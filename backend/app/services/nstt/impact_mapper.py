"""
INCIDENT_IMPACT Mapper Service
==============================
Converts raw INCIDENT_IMPACT values:
- 0 / "0" / 0.0 / "SA" -> "SA"
- 1 / "1" / 1.0 / "NSA" -> "NSA"
- All other values / null / NaN -> None (unclassified)
"""

from typing import Any
import pandas as pd


def map_single_impact(val: Any) -> str | None:
    """Maps a single raw INCIDENT_IMPACT cell value to 'SA', 'NSA', or None."""
    if val is None or pd.isna(val):
        return None

    # Strip whitespace and convert to string
    val_str = str(val).strip().upper()

    if val_str in ("0", "0.0", "SA"):
        return "SA"
    if val_str in ("1", "1.0", "NSA"):
        return "NSA"

    return None


def map_incident_impact(df_or_series: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """
    Applies INCIDENT_IMPACT mapping across a DataFrame (updating 'INCIDENT_IMPACT' column)
    or directly on a Series.
    """
    if isinstance(df_or_series, pd.Series):
        return df_or_series.apply(map_single_impact)

    if isinstance(df_or_series, pd.DataFrame):
        df_copy = df_or_series.copy()
        if "INCIDENT_IMPACT" in df_copy.columns:
            df_copy["INCIDENT_IMPACT"] = df_copy["INCIDENT_IMPACT"].apply(map_single_impact)
        return df_copy

    return df_or_series
