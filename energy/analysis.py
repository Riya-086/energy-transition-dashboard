"""Questions answered with SQL (DuckDB) over the processed table."""

from pathlib import Path

import duckdb
import pandas as pd

from .pipeline import PROCESSED


def load(path: Path = PROCESSED) -> pd.DataFrame:
    return pd.read_csv(path)


def _query(df: pd.DataFrame, sql: str, params: list) -> pd.DataFrame:
    con = duckdb.connect()
    con.register("mix", df)
    try:
        return con.execute(sql, params).df()
    finally:
        con.close()


def latest_complete_year(df: pd.DataFrame, min_countries: int = 100) -> int:
    """Most recent year with data for enough countries, so partial years don't skew rankings."""
    counts = df[df["iso_code"] != "WORLD"].groupby("year")["country"].nunique()
    return int(counts[counts >= min_countries].index.max())


def top_movers(df: pd.DataFrame, start: int, end: int, min_twh: float = 10.0, limit: int = 10) -> pd.DataFrame:
    """Countries whose low-carbon share of electricity rose most between two years.

    The change is split into renewables and nuclear, which together make up low-carbon power.
    Small grids (under `min_twh` generation in the end year) are excluded because a single new
    plant can swing their shares wildly.
    """
    return _query(
        df,
        """
        SELECT e.country,
               s.low_carbon_pct                    AS start_pct,
               e.low_carbon_pct                    AS end_pct,
               e.low_carbon_pct - s.low_carbon_pct AS change_pts,
               e.renewables_pct - s.renewables_pct AS renewables_pts,
               e.nuclear_pct - s.nuclear_pct       AS nuclear_pts,
               e.generation_twh
        FROM mix e
        JOIN mix s ON s.country = e.country AND s.year = ?
        WHERE e.year = ? AND e.iso_code <> 'WORLD' AND e.generation_twh >= ?
        ORDER BY change_pts DESC
        LIMIT ?
        """,
        [start, end, min_twh, limit],
    ).round(1)


def world_trend(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["iso_code"] == "WORLD"][["year", "low_carbon_pct", "renewables_pct", "nuclear_pct", "fossil_pct"]]


def share_with_majority_low_carbon(df: pd.DataFrame, year: int, min_twh: float = 10.0) -> tuple[int, int]:
    row = _query(
        df,
        """SELECT COUNT(*) FILTER (WHERE low_carbon_pct > 50) AS majority, COUNT(*) AS total
           FROM mix WHERE year = ? AND iso_code <> 'WORLD' AND generation_twh >= ?""",
        [year, min_twh],
    ).iloc[0]
    return int(row["majority"]), int(row["total"])
