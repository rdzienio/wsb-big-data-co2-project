"""
Moduł ładowania i czyszczenia danych o emisjach CO2 (Our World in Data).

Autor: Robert Dzienio

Źródło: https://github.com/owid/co2-data
Plik:   owid-co2-data.csv  (~14 MB, 50k wierszy, 79 kolumn, lata 1750-2024)

Moduł jest używany przez aplikację Streamlit (app.py). Funkcje ładujące są
opakowane w @st.cache_data, żeby dane wczytywały się raz na sesję (wymóg
wydajności na share.streamlit.io - 1 GB RAM).
"""
from __future__ import annotations

import os
import pandas as pd

# Streamlit jest opcjonalny przy uruchomieniu modułu jako skryptu (demo),
# dlatego cache podpinamy warunkowo - poza Streamlitem to zwykłe funkcje.
try:
    import streamlit as st
    cache = st.cache_data
except ModuleNotFoundError:  # uruchomienie standalone: python data.py
    def cache(func=None, **_kwargs):
        return func if func else (lambda f: f)


# Lokalny plik obok modułu - działa tak samo lokalnie i po deployu.
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "owid-co2-data.csv")
CSV_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"

# Podzbiór kolumn, których faktycznie używamy. Redukcja 79 -> 25 kolumn
# znacząco zmniejsza zużycie pamięci (istotne przy limicie 1 GB na hostingu).
KOLUMNY = [
    # identyfikacja
    "country", "year", "iso_code", "population", "gdp",
    # emisje - główne
    "co2", "co2_per_capita", "co2_growth_prct",
    "cumulative_co2", "share_global_co2", "consumption_co2", "trade_co2",
    # emisje wg źródła (paliwa / przemysł)
    "coal_co2", "oil_co2", "gas_co2", "cement_co2", "flaring_co2",
    # inne gazy cieplarniane
    "methane", "nitrous_oxide", "total_ghg",
    # wpływ na temperaturę i energia
    "temperature_change_from_co2",
    "primary_energy_consumption", "energy_per_capita",
]

PALIWA = ["coal_co2", "oil_co2", "gas_co2", "cement_co2", "flaring_co2"]
PALIWA_PL = {
    "coal_co2": "Węgiel",
    "oil_co2": "Ropa",
    "gas_co2": "Gaz",
    "cement_co2": "Cement",
    "flaring_co2": "Spalanie gazu (flaring)",
}


@cache
def wczytaj_surowe() -> pd.DataFrame:
    """Wczytuje surowy CSV z dysku (lub pobiera z sieci, jeśli brak lokalnie)."""
    sciezka = CSV_PATH if os.path.exists(CSV_PATH) else CSV_URL
    df = pd.read_csv(sciezka, usecols=lambda c: c in KOLUMNY)
    return df


def _dodaj_kolumny_pochodne(df: pd.DataFrame) -> pd.DataFrame:
    """Kolumny wyliczane: PKB per capita, dekada, udział paliw w miksie CO2."""
    df = df.copy()

    # PKB na mieszkańca (USD). Chronimy przed dzieleniem przez zero/braki.
    df["gdp_per_capita"] = (df["gdp"] / df["population"]).where(df["population"] > 0)

    # Dekada – przydatna do agregacji i heatmap.
    df["dekada"] = (df["year"] // 10 * 10).astype("int16")

    # Udział procentowy węgla w emisjach CO2 danego kraju/roku.
    df["udzial_wegla_prct"] = (100 * df["coal_co2"] / df["co2"]).where(df["co2"] > 0)

    return df


@cache
def wczytaj_kraje() -> pd.DataFrame:
    """
    Zwraca oczyszczony DataFrame TYLKO z prawdziwymi krajami.

    Czyszczenie:
      * odrzucenie agregatów (World, kontynenty, grupy dochodowe) — nie mają iso_code
      * poprawne typy (year -> int, kody -> category)
      * dodanie kolumn pochodnych
    """
    df = wczytaj_surowe()

    # Prawdziwe kraje mają 3-literowy kod ISO; agregaty mają puste iso_code.
    df = df[df["iso_code"].notna()].copy()

    df["year"] = df["year"].astype("int16")
    df = _dodaj_kolumny_pochodne(df)

    df["country"] = df["country"].astype("category")
    df["iso_code"] = df["iso_code"].astype("category")

    return df.reset_index(drop=True)


@cache
def wczytaj_agregaty() -> pd.DataFrame:
    """Zwraca encje zbiorcze (World, kontynenty, grupy dochodowe) — do kontekstu KPI."""
    df = wczytaj_surowe()
    df = df[df["iso_code"].isna()].copy()
    df["year"] = df["year"].astype("int16")
    return _dodaj_kolumny_pochodne(df).reset_index(drop=True)


if __name__ == "__main__":
    # Demo / sanity-check czyszczenia – uruchom: python data.py
    kraje = wczytaj_kraje()
    agg = wczytaj_agregaty()

    print("=== KRAJE (oczyszczone) ===")
    print("Shape:", kraje.shape)
    print("Liczba krajów:", kraje["country"].nunique())
    print("Zakres lat:", kraje["year"].min(), "-", kraje["year"].max())
    print("Pamięć: {:.1f} MB".format(kraje.memory_usage(deep=True).sum() / 1e6))
    print()
    print("=== AGREGATY ===")
    print("Encje:", sorted(agg["country"].unique())[:8], "...")
    print()
    print("=== Przykład: Polska, ostatnie 5 lat ===")
    pl = kraje[kraje["country"] == "Poland"].tail(5)
    print(pl[["year", "co2", "co2_per_capita", "gdp_per_capita", "udzial_wegla_prct"]]
          .to_string(index=False))
