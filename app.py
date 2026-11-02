"""Streamlit dashboard: run with `streamlit run app.py`."""

import plotly.express as px
import streamlit as st

from energy.analysis import latest_complete_year, load, share_with_majority_low_carbon, top_movers, world_trend

st.set_page_config(page_title="Electricity Transition Dashboard", page_icon="⚡", layout="wide")


@st.cache_data
def data():
    return load()


df = data()
latest = latest_complete_year(df)
countries = sorted(c for c in df["country"].unique() if c != "World")

st.title("Who is decarbonising their electricity fastest?")
st.caption(
    "Share of electricity from low-carbon sources (renewables + nuclear), by country. "
    "Data: Our World in Data energy dataset (CC BY 4.0), based on Ember and Energy Institute statistics."
)

with st.sidebar:
    st.header("Filters")
    start = st.slider("Compare from", min_value=2000, max_value=latest - 1, value=2015)
    min_twh = st.number_input("Minimum grid size (TWh per year)", min_value=0.0, value=10.0, step=5.0)
    picked = st.multiselect(
        "Countries to chart",
        countries,
        default=[c for c in ("United States", "China", "India", "Germany", "United Kingdom") if c in countries],
    )

world = world_trend(df).set_index("year")
majority, total = share_with_majority_low_carbon(df, latest, min_twh)
c1, c2, c3 = st.columns(3)
c1.metric(
    f"World low-carbon share, {latest}",
    f"{world.loc[latest, 'low_carbon_pct']:.1f}%",
    f"{world.loc[latest, 'low_carbon_pct'] - world.loc[start, 'low_carbon_pct']:+.1f} pts since {start}",
)
c2.metric(
    f"World fossil share, {latest}",
    f"{world.loc[latest, 'fossil_pct']:.1f}%",
    f"{world.loc[latest, 'fossil_pct'] - world.loc[start, 'fossil_pct']:+.1f} pts since {start}",
    delta_color="inverse",
)
c3.metric("Countries with a majority low-carbon grid", f"{majority} of {total}", help=f"Grids of {min_twh:g}+ TWh")

st.subheader(f"Biggest increases in low-carbon share, {start}–{latest}")
movers = top_movers(df, start, latest, min_twh=min_twh)
if movers.empty:
    st.info("No countries match these filters.")
else:
    chart = movers.melt(
        id_vars="country", value_vars=["renewables_pts", "nuclear_pts"], var_name="source", value_name="points"
    )
    chart["source"] = chart["source"].map({"renewables_pts": "Renewables", "nuclear_pts": "Nuclear"})
    fig = px.bar(
        chart,
        x="points",
        y="country",
        color="source",
        orientation="h",
        labels={"points": "Change in share of electricity (percentage points)", "country": ""},
        color_discrete_map={"Renewables": "#2a9d8f", "Nuclear": "#7b6fd6"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, legend_title_text="", height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(movers, hide_index=True, use_container_width=True)

st.subheader("Low-carbon share over time")
if picked:
    trend = df[df["country"].isin([*picked, "World"])]
    fig = px.line(
        trend,
        x="year",
        y="low_carbon_pct",
        color="country",
        markers=False,
        labels={"low_carbon_pct": "Low-carbon share of electricity (%)", "year": ""},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pick at least one country in the sidebar.")

st.subheader("What one country's grid is made of")
country = st.selectbox("Country", countries, index=countries.index("India") if "India" in countries else 0)
mix = df[df["country"] == country].melt(
    id_vars="year",
    value_vars=["coal_pct", "gas_pct", "nuclear_pct", "hydro_pct", "wind_pct", "solar_pct"],
    var_name="source",
    value_name="share",
)
mix["source"] = mix["source"].str.removesuffix("_pct").str.capitalize()
st.plotly_chart(
    px.area(mix, x="year", y="share", color="source", labels={"share": "Share of electricity (%)", "year": ""}),
    use_container_width=True,
)

with st.expander("Method and limitations"):
    st.markdown(
        "- Low-carbon = renewables (hydro, wind, solar, bioenergy, other) + nuclear, as defined by OWID.\n"
        "- Shares are of electricity generation, not total energy use: transport and heating are not included.\n"
        "- Small grids are filtered out of rankings because one new plant can swing their shares.\n"
        f"- {latest} is the most recent year with data for at least 100 countries; later years may be partial."
    )
