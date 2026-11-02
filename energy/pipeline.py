"""Download the raw OWID energy dataset and build the tidy table the dashboard reads.

Usage:  python -m energy.pipeline            # download (if needed) and rebuild
        python -m energy.pipeline --refresh  # always download the latest data
"""

import argparse
import urllib.request
from pathlib import Path

import pandas as pd

SOURCE_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "owid-energy-data.csv"
PROCESSED = ROOT / "data" / "processed" / "electricity_mix.csv"
FIRST_YEAR = 2000

COLUMNS = {
    "electricity_generation": "generation_twh",
    "low_carbon_share_elec": "low_carbon_pct",
    "renewables_share_elec": "renewables_pct",
    "nuclear_share_elec": "nuclear_pct",
    "fossil_share_elec": "fossil_pct",
    "solar_share_elec": "solar_pct",
    "wind_share_elec": "wind_pct",
    "hydro_share_elec": "hydro_pct",
    "coal_share_elec": "coal_pct",
    "gas_share_elec": "gas_pct",
    "carbon_intensity_elec": "carbon_intensity_g_per_kwh",
}


def download(destination: Path = RAW) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(SOURCE_URL, destination)
    return destination


def build(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep real countries plus the World total, from 2000 on, with readable column names.

    OWID mixes regions and income groups in with countries; those have no ISO code or an
    'OWID_' code. World is kept separately as the benchmark.
    """
    is_country = raw["iso_code"].str.fullmatch(r"[A-Z]{3}", na=False)
    is_world = raw["country"].eq("World")
    keep = ["country", "iso_code", "year", *COLUMNS]
    # reindex tolerates an optional column missing from a future OWID release; required ones are checked below
    df = raw.loc[(is_country | is_world) & (raw["year"] >= FIRST_YEAR)].reindex(columns=keep)
    df = df.rename(columns=COLUMNS).dropna(subset=["generation_twh", "low_carbon_pct"])
    df.loc[df["country"].eq("World"), "iso_code"] = "WORLD"
    pct = [c for c in df.columns if c.endswith("_pct")]
    df[pct] = df[pct].clip(0, 100)
    return df.sort_values(["country", "year"]).reset_index(drop=True).round(3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="download the latest data even if a copy exists")
    args = parser.parse_args()
    if args.refresh or not RAW.exists():
        print(f"Downloading {SOURCE_URL}")
        download()
    table = build(pd.read_csv(RAW))
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(PROCESSED, index=False)
    print(f"Wrote {len(table):,} rows for {table['country'].nunique()} countries to {PROCESSED.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
