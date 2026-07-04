# 🌍 CO₂ Explorer

Interaktywna aplikacja analityczna do eksploracji **światowych emisji dwutlenku węgla**,
zbudowana w **Streamlit + Plotly**. Projekt zaliczeniowy z przedmiotu
*Zarządzanie Big Data* (WSB Merito).

**🔗 Aplikacja na żywo:** https://wsb-big-data-co2-project-rdzienio.streamlit.app/

---

## O aplikacji

CO₂ Explorer pozwala interaktywnie analizować emisje CO₂ na przestrzeni lat i krajów:
- porównać emisje globalne i krajowe,
- zobaczyć, kto emituje najwięcej (ogółem i w przeliczeniu na mieszkańca),
- prześledzić zmiany struktury paliwowej emisji,
- zbadać zależność między zamożnością (PKB per capita) a śladem węglowym.

## Źródło danych

Dane pochodzą z **[Our World in Data — CO₂ and Greenhouse Gas Emissions](https://github.com/owid/co2-data)**
(licencja CC BY 4.0). Zbiór obejmuje **218 krajów**, lata **1750–2024**, z podziałem emisji
na źródła (węgiel, ropa, gaz, cement) oraz danymi o PKB, populacji i wpływie na temperaturę.

Plik `owid-co2-data.csv` jest dołączony do repozytorium. Jeśli go brakuje,
moduł `data.py` pobiera go automatycznie z oficjalnego źródła.

## Funkcje

- **5 filtrów interaktywnych**: zakres lat, rok (widok migawkowy), metryka,
  liczba krajów w rankingu (Top N), wybór krajów do porównań.
- **7 typów wizualizacji**:
  1. 🗺️ Mapa choropleth świata
  2. 📈 Wykres liniowy (trendy emisji w czasie)
  3. 📊 Wykres warstwowy (globalny miks paliw)
  4. 📊 Wykres słupkowy (ranking Top N)
  5. 🌳 Treemap (struktura emisji wg paliw)
  6. 🔵 Wykres punktowy / bąbelkowy (PKB vs CO₂ per capita)
  7. 🔥 Heatmapa (emisje per capita: kraj × dekada)
- **KPI**: emisje globalne (r/r), największy emitent, najwyższe emisje per capita,
  liczba krajów z danymi.
- Cache danych (`@st.cache_data`) i podział kodu na moduły.

## Struktura projektu

```
├── app.py               # aplikacja Streamlit (UI, layout, wykresy)
├── data.py              # ładowanie i czyszczenie danych (+ demo: python data.py)
├── owid-co2-data.csv    # dane źródłowe (Our World in Data)
├── requirements.txt     # zależności runtime
└── README.md
```

## Uruchomienie lokalne

Wymagany Python 3.13.

```bash
# 1. Instalacja zależności
pip install -r requirements.txt

# 2. Uruchomienie aplikacji
streamlit run app.py
```

Aplikacja otworzy się w przeglądarce pod adresem `http://localhost:8501`.

Aby sprawdzić samo czyszczenie danych (bez UI):

```bash
python data.py
```

## Wdrożenie

Aplikacja jest przygotowana pod **[Streamlit Community Cloud](https://share.streamlit.io)**:
publiczne repozytorium GitHub, plik główny `app.py`, zależności w `requirements.txt`.

---

*Dane: Our World in Data (CC BY 4.0). Projekt edukacyjny.*
