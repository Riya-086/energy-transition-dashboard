import pandas as pd
import pytest

from energy.analysis import latest_complete_year, share_with_majority_low_carbon, top_movers
from energy.pipeline import build


@pytest.fixture
def raw():
    rows = []
    for country, iso, ren15, ren24, nuc15, nuc24, gen in [
        ("Alpha", "AAA", 10, 50, 5, 5, 100),  # +40 pts, all renewables
        ("Beta", "BBB", 20, 25, 10, 20, 50),  # +15 pts, mostly nuclear, still below 50%
        ("Tiny", "TTT", 0, 90, 0, 0, 1),  # huge swing but a tiny grid
        ("Europe", None, 30, 40, 20, 20, 4000),  # region, must be dropped
        ("World", "OWID_WRL", 20, 30, 10, 9, 30000),
    ]:
        for year, ren, nuc in [(1999, ren15, nuc15), (2015, ren15, nuc15), (2024, ren24, nuc24)]:
            rows.append(
                {
                    "country": country,
                    "iso_code": iso,
                    "year": year,
                    "electricity_generation": gen,
                    "renewables_share_elec": ren,
                    "nuclear_share_elec": nuc,
                    "low_carbon_share_elec": ren + nuc,
                    "fossil_share_elec": 100 - ren - nuc,
                }
            )
    return pd.DataFrame(rows)


def test_build_keeps_countries_and_world_from_2000(raw):
    df = build(raw)
    assert set(df["country"]) == {"Alpha", "Beta", "Tiny", "World"}
    assert df["year"].min() == 2015
    assert df.loc[df["country"] == "World", "iso_code"].unique().tolist() == ["WORLD"]
    assert {"generation_twh", "low_carbon_pct", "renewables_pct", "nuclear_pct"} <= set(df.columns)


def test_top_movers_ranks_by_change_and_excludes_small_grids(raw):
    movers = top_movers(build(raw), 2015, 2024, min_twh=10)
    assert movers["country"].tolist() == ["Alpha", "Beta"]
    alpha, beta = movers.iloc[0], movers.iloc[1]
    assert (alpha["change_pts"], alpha["renewables_pts"], alpha["nuclear_pts"]) == (40, 40, 0)
    assert (beta["change_pts"], beta["nuclear_pts"]) == (15, 10)


def test_latest_complete_year_and_majority_count(raw):
    df = build(raw)
    assert latest_complete_year(df, min_countries=3) == 2024
    assert share_with_majority_low_carbon(df, 2024, min_twh=10) == (1, 2)  # Alpha 55%, Beta 45%


def test_processed_data_file_is_consistent():
    from energy.analysis import load

    df = load()
    assert df["low_carbon_pct"].between(0, 100).all()
    assert df.duplicated(["country", "year"]).sum() == 0
    assert "World" in set(df["country"]) and df["year"].max() >= 2023
