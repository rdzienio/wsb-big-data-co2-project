"""
Interaktywna analiza światowych emisji dwutlenku węgla.

Projekt zaliczeniowy „Zarządzanie Big Data" (WSB Merito).
Dane: Our World in Data - https://github.com/owid/co2-data

Autor: Robert Dzienio

Uruchomienie lokalne:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from data import wczytaj_kraje, wczytaj_agregaty, PALIWA, PALIWA_PL

# --------------------------------------------------------------------------- #
# Konfiguracja strony
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="CO₂ Explorer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dostępne metryki: etykieta widoczna dla użytkownika -> nazwa kolumny.
METRYKI = {
    "Emisje CO₂ (mln ton)": "co2",
    "CO₂ per capita (tony/os.)": "co2_per_capita",
    "Udział w globalnych emisjach (%)": "share_global_co2",
    "Emisje skumulowane (mln ton)": "cumulative_co2",
}


# --------------------------------------------------------------------------- #
# Dane (cache w module data.py)
# --------------------------------------------------------------------------- #
kraje = wczytaj_kraje()
agregaty = wczytaj_agregaty()
swiat = agregaty[agregaty["country"] == "World"]

ROK_MIN, ROK_MAX = int(kraje["year"].min()), int(kraje["year"].max())


# --------------------------------------------------------------------------- #
# Pasek boczny - filtry
# --------------------------------------------------------------------------- #
st.sidebar.title("🌍 CO₂ Explorer")
st.sidebar.caption("Filtry sterują wszystkimi wykresami poniżej.")

# Filtr 1 - zakres lat (dla wykresów czasowych).
zakres_lat = st.sidebar.slider(
    "Zakres lat (trendy czasowe)",
    min_value=ROK_MIN, max_value=ROK_MAX,
    value=(1950, ROK_MAX), step=1,
)

# Filtr 2 - pojedynczy rok (dla widoków „migawkowych": mapa, ranking, treemap).
rok = st.sidebar.slider(
    "Rok (mapa i rankingi)",
    min_value=ROK_MIN, max_value=ROK_MAX, value=ROK_MAX, step=1,
)

# Filtr 3 - metryka pokazywana na mapie i w rankingu.
metryka_label = st.sidebar.selectbox("Metryka", list(METRYKI.keys()))
metryka = METRYKI[metryka_label]

# Filtr 4 - liczba krajów w rankingach.
top_n = st.sidebar.slider("Liczba krajów w rankingu (Top N)", 5, 30, 15, step=1)

# Filtr 5 - kraje do porównań czasowych. Domyślnie najwięksi emitenci ostatniego roku.
domyslne_kraje = (
    kraje[kraje["year"] == ROK_MAX]
    .nlargest(6, "co2")["country"].astype(str).tolist()
)
wszystkie_kraje = sorted(kraje["country"].astype(str).unique())
wybrane_kraje = st.sidebar.multiselect(
    "Kraje do porównania (trendy)",
    options=wszystkie_kraje,
    default=domyslne_kraje,
)

st.sidebar.divider()
st.sidebar.caption("Źródło: Our World in Data (owid/co2-data). "
                   "Dane obejmują emisje ze spalania paliw kopalnych i przemysłu.")


# --------------------------------------------------------------------------- #
# Nagłówek + KPI
# --------------------------------------------------------------------------- #
st.title("🌍 CO₂ Explorer")
st.markdown(
    "Interaktywna analiza światowych emisji **dwutlenku węgla** na podstawie "
    "danych *Our World in Data*. Użyj filtrów po lewej, aby zmienić rok, metrykę "
    "i porównywane kraje."
)

kraje_rok = kraje[kraje["year"] == rok]


def kpi_swiat(rok: int) -> float | None:
    """Globalne emisje CO₂ (mln ton) w danym roku wg encji 'World'."""
    wiersz = swiat[swiat["year"] == rok]
    return float(wiersz["co2"].iloc[0]) if not wiersz.empty else None


c1, c2, c3, c4 = st.columns(4)

glob = kpi_swiat(rok)
glob_prev = kpi_swiat(rok - 1)
delta = f"{(glob - glob_prev) / glob_prev * 100:+.1f}% r/r" if glob and glob_prev else None
c1.metric(f"Emisje świata ({rok})", f"{glob:,.0f} mln t" if glob else "—", delta)

if not kraje_rok.empty:
    lider = kraje_rok.nlargest(1, "co2").iloc[0]
    c2.metric("Największy emitent", str(lider["country"]),
              f"{lider['co2']:,.0f} mln t")

    # Per capita liczymy tylko dla krajów > 1 mln mieszkańców (pomijamy „mikro-outliery").
    duze = kraje_rok[kraje_rok["population"] > 1_000_000]
    if not duze.empty and duze["co2_per_capita"].notna().any():
        pc = duze.nlargest(1, "co2_per_capita").iloc[0]
        c3.metric("Najwięcej CO₂ / osobę", str(pc["country"]),
                  f"{pc['co2_per_capita']:.1f} t/os.")

    c4.metric("Krajów z danymi", f"{kraje_rok['co2'].notna().sum()}")

st.divider()


# --------------------------------------------------------------------------- #
# Zakładki z wizualizacjami
# --------------------------------------------------------------------------- #
tab_mapa, tab_trendy, tab_rankingi, tab_zaleznosci, tab_polska = st.tabs(
    ["Mapa świata", "Trendy w czasie", "Rankingi", "Zależności",
     "Polska"]
)


# ---- Zakładka 1: MAPA (choropleth) ---------------------------------------- #
with tab_mapa:
    st.subheader(f"{metryka_label} — {rok}")
    dane_mapy = kraje_rok.dropna(subset=[metryka])
    fig = px.choropleth(
        dane_mapy,
        locations="iso_code",
        color=metryka,
        hover_name="country",
        color_continuous_scale="YlOrRd",
        labels={metryka: metryka_label},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=520)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Mapa pokazuje **{metryka_label.lower()}** w roku {rok}. "
        "Ciemniejszy kolor = wyższa wartość. Kraje bez danych pozostają szare."
    )


# ---- Zakładka 2: TRENDY (wykres liniowy + skumulowany obszarowy) ----------- #
with tab_trendy:
    lata_od, lata_do = zakres_lat
    if not wybrane_kraje:
        st.info("Wybierz co najmniej jeden kraj w panelu bocznym.")
    else:
        maska = (
            kraje["country"].astype(str).isin(wybrane_kraje)
            & kraje["year"].between(lata_od, lata_do)
        )
        dane_t = kraje[maska]

        st.subheader("Emisje CO₂ w czasie")
        fig_line = px.line(
            dane_t, x="year", y="co2", color="country",
            labels={"year": "Rok", "co2": "Emisje CO₂ (mln ton)",
                    "country": "Kraj"},
        )
        fig_line.update_layout(height=430, hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)
        st.caption("Wykres liniowy ujawnia różne ścieżki rozwoju — np. gwałtowny "
                   "wzrost Chin po 2000 r. vs. stabilizacja/spadki w krajach Zachodu.")

        st.subheader("Globalny miks paliw w czasie")
        # Stacked area - z jakich źródeł pochodzą światowe emisje.
        swiat_zakres = swiat[swiat["year"].between(lata_od, lata_do)]
        dane_paliwa = swiat_zakres.melt(
            id_vars="year", value_vars=PALIWA,
            var_name="zrodlo", value_name="emisje",
        )
        dane_paliwa["zrodlo"] = dane_paliwa["zrodlo"].map(PALIWA_PL)
        fig_area = px.area(
            dane_paliwa, x="year", y="emisje", color="zrodlo",
            labels={"year": "Rok", "emisje": "Emisje CO₂ (mln ton)",
                    "zrodlo": "Źródło"},
        )
        fig_area.update_layout(height=400)
        st.plotly_chart(fig_area, use_container_width=True)
        st.caption("Wykres warstwowy pokazuje strukturę źródeł emisji na świecie. "
                   "Węgiel i ropa historycznie dominują; udział gazu rośnie.")


# ---- Zakładka 3: RANKINGI (słupkowy + treemap) ---------------------------- #
with tab_rankingi:
    st.subheader(f"Top {top_n} krajów — {metryka_label} ({rok})")
    top = kraje_rok.dropna(subset=[metryka]).nlargest(top_n, metryka)
    fig_bar = px.bar(
        top.sort_values(metryka), x=metryka, y="country", orientation="h",
        color=metryka, color_continuous_scale="YlOrRd",
        labels={metryka: metryka_label, "country": ""},
    )
    fig_bar.update_layout(height=max(400, top_n * 24), coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader(f"Struktura emisji wg paliw — Top {top_n} ({rok})")
    # Treemap: kraj -> paliwo. Pokazuje kto emituje i z czego.
    top_co2 = kraje_rok.dropna(subset=["co2"]).nlargest(top_n, "co2")
    tm = top_co2.melt(id_vars="country", value_vars=PALIWA,
                      var_name="zrodlo", value_name="emisje")
    tm["zrodlo"] = tm["zrodlo"].map(PALIWA_PL)
    tm = tm.dropna(subset=["emisje"])
    tm = tm[tm["emisje"] > 0]
    fig_tree = px.treemap(
        tm, path=[px.Constant("Świat"), "country", "zrodlo"], values="emisje",
        color="emisje", color_continuous_scale="YlOrRd",
    )
    fig_tree.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_tree, use_container_width=True)
    st.caption("Treemap: pole prostokąta = wielkość emisji. Klikaj, aby wejść "
               "w głąb i zobaczyć rozbicie na paliwa dla danego kraju.")


# ---- Zakładka 4: ZALEŻNOŚCI (scatter + heatmapa) -------------------------- #
with tab_zaleznosci:
    st.subheader(f"Zamożność a emisje per capita ({rok})")
    # Scatter: PKB per capita vs CO2 per capita, wielkość = populacja.
    sc = kraje_rok.dropna(subset=["gdp_per_capita", "co2_per_capita", "population"])
    sc = sc[sc["population"] > 1_000_000]
    if sc.empty:
        st.info(f"Brak danych o PKB dla roku {rok}. Wybierz wcześniejszy rok "
                "(PKB dostępne zwykle do ~2022).")
    else:
        fig_sc = px.scatter(
            sc, x="gdp_per_capita", y="co2_per_capita",
            size="population", color="co2", hover_name="country",
            size_max=55, log_x=True, color_continuous_scale="YlOrRd",
            labels={"gdp_per_capita": "PKB na mieszkańca (USD, skala log)",
                    "co2_per_capita": "CO₂ na mieszkańca (tony)",
                    "co2": "CO₂ ogółem", "population": "Populacja"},
        )
        fig_sc.update_layout(height=470)
        st.plotly_chart(fig_sc, use_container_width=True)
        st.caption("💡 Wyraźna korelacja: bogatsze kraje emitują więcej CO₂ na osobę. "
                   "Ale są wyjątki — kraje o podobnym PKB potrafią mieć bardzo różny ślad.")

    st.subheader("Heatmapa emisji per capita (kraj × dekada)")
    if wybrane_kraje:
        hm = kraje[kraje["country"].astype(str).isin(wybrane_kraje)]
        pivot = hm.pivot_table(index="country", columns="dekada",
                               values="co2_per_capita", aggfunc="mean")
        pivot = pivot.dropna(axis=1, how="all")
        fig_hm = px.imshow(
            pivot, color_continuous_scale="YlOrRd", aspect="auto",
            labels=dict(x="Dekada", y="Kraj", color="CO₂/os."),
        )
        fig_hm.update_layout(height=400)
        st.plotly_chart(fig_hm, use_container_width=True)
        st.caption("Heatmapa: średnie emisje per capita w dekadach. Dobrze widać, "
                   "które kraje redukują ślad, a które go zwiększają.")
    else:
        st.info("Wybierz kraje w panelu bocznym, aby zobaczyć heatmapę.")


# ---- Zakładka 5: POLSKA (analiza dedykowana) ------------------------------ #
POLSKA = "Poland"
SASIEDZI = ["Poland", "Germany", "Czechia", "Slovakia", "Ukraine", "France", "Sweden"]

with tab_polska:
    st.subheader("Polska — analiza szczegółowa")
    pl = kraje[kraje["country"].astype(str) == POLSKA]
    pl_rok = pl[pl["year"] == rok]

    if pl_rok.empty:
        st.info(f"Brak danych dla Polski w roku {rok}. Wybierz inny rok w panelu bocznym.")
    else:
        w = pl_rok.iloc[0]

        # --- KPI dla Polski w wybranym roku ---
        p1, p2, p3, p4 = st.columns(4)

        pl_prev = pl[pl["year"] == rok - 1]
        delta_pl = None
        if not pl_prev.empty and pd.notna(pl_prev["co2"].iloc[0]):
            poprz = pl_prev["co2"].iloc[0]
            delta_pl = f"{(w['co2'] - poprz) / poprz * 100:+.1f}% r/r"
        p1.metric(f"Emisje CO₂ ({rok})", f"{w['co2']:,.0f} mln t", delta_pl,
                  delta_color="inverse")  # spadek emisji to dobra wiadomość
        p2.metric("CO₂ na mieszkańca", f"{w['co2_per_capita']:.1f} t/os.")
        p3.metric("Udział węgla", f"{w['udzial_wegla_prct']:.0f}%")

        # Miejsce Polski w światowym rankingu emisji CO₂ w danym roku.
        ranking = (kraje_rok.dropna(subset=["co2"])
                   .sort_values("co2", ascending=False)
                   .reset_index(drop=True))
        poz = ranking.index[ranking["country"].astype(str) == POLSKA]
        p4.metric("Miejsce w świecie", f"{int(poz[0]) + 1}." if len(poz) else "—",
                  help="Pozycja w rankingu emisji CO₂ ogółem")

        lata_od, lata_do = zakres_lat
        pl_zakres = pl[pl["year"].between(lata_od, lata_do)]

        # --- Miks paliw Polski w czasie (stacked area) ---
        st.subheader("Z czego pochodzą emisje Polski? (miks paliw)")
        dp = pl_zakres.melt(id_vars="year", value_vars=PALIWA,
                            var_name="zrodlo", value_name="emisje")
        dp["zrodlo"] = dp["zrodlo"].map(PALIWA_PL)
        fig_pl_area = px.area(
            dp, x="year", y="emisje", color="zrodlo",
            labels={"year": "Rok", "emisje": "Emisje CO₂ (mln ton)", "zrodlo": "Źródło"},
        )
        fig_pl_area.update_layout(height=380)
        st.plotly_chart(fig_pl_area, use_container_width=True)
        st.caption("Emisje Polski historycznie zdominowane przez **węgiel** — "
                   "spuścizna energetyki opartej na węglu kamiennym i brunatnym.")

        col_a, col_b = st.columns(2)

        # --- Udział węgla w czasie (linia) — historia dekarbonizacji ---
        with col_a:
            st.subheader("Udział węgla w emisjach")
            fig_coal = px.line(
                pl_zakres, x="year", y="udzial_wegla_prct",
                labels={"year": "Rok", "udzial_wegla_prct": "Udział węgla (%)"},
            )
            fig_coal.update_traces(line_color="#5c4033", line_width=3)
            fig_coal.update_layout(height=360, yaxis_range=[0, 100])
            st.plotly_chart(fig_coal, use_container_width=True)
            st.caption("💡 Wyraźny trend spadkowy — postępująca dekarbonizacja "
                       "polskiej gospodarki.")

        # --- Polska na tle sąsiadów (słupkowy) ---
        with col_b:
            st.subheader(f"Na tle sąsiadów ({rok})")
            por = (kraje_rok[kraje_rok["country"].astype(str).isin(SASIEDZI)]
                   .dropna(subset=["co2_per_capita"])
                   .sort_values("co2_per_capita"))
            por["grupa"] = por["country"].astype(str).eq(POLSKA).map(
                {True: "Polska", False: "Sąsiedzi"})
            fig_por = px.bar(
                por, x="co2_per_capita", y="country", orientation="h",
                color="grupa",
                color_discrete_map={"Polska": "#d62728", "Sąsiedzi": "#9aa0a6"},
                labels={"co2_per_capita": "CO₂ per capita (t/os.)",
                        "country": "", "grupa": ""},
            )
            fig_por.update_layout(height=360, legend_title_text="")
            st.plotly_chart(fig_por, use_container_width=True)
            st.caption("Polska wypada wysoko per capita — efekt węgla. "
                       "Francja (atom) i Szwecja (hydro/atom) emitują dużo mniej.")


# --------------------------------------------------------------------------- #
# Stopka
# --------------------------------------------------------------------------- #
st.divider()
st.caption("Dane: Our World in Data (CC BY 4.0) · Projekt zaliczeniowy Big Data · "
           "Zbudowano w Streamlit + Plotly")
