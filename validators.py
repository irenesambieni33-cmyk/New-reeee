"""
RE-ZERO - Validators
Règle anti-hallucination : on ne travaille jamais sur des données
incomplètes, corrompues ou inventées. Si une donnée manque, on le dit.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close"]


class DataValidationError(Exception):
    pass


def validate_ohlcv(df: pd.DataFrame, require_volume: bool = False) -> list[str]:
    """
    Vérifie qu'un DataFrame OHLCV est exploitable.
    Retourne une liste de messages d'avertissement (vide si tout est OK).
    Lève DataValidationError si les données sont inutilisables.
    """
    warnings: list[str] = []

    if df is None or df.empty:
        raise DataValidationError("Donnée indisponible : DataFrame vide ou absent.")

    cols_lower = {c.lower(): c for c in df.columns}
    missing = [c for c in REQUIRED_COLUMNS if c not in cols_lower]
    if missing:
        raise DataValidationError(
            f"Donnée indisponible : colonnes manquantes {missing}."
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        warnings.append("Index non temporel : les analyses multi-timeframe seront limitées.")

    n_missing = df[[cols_lower[c] for c in REQUIRED_COLUMNS]].isna().sum().sum()
    if n_missing > 0:
        warnings.append(f"{n_missing} valeurs manquantes détectées dans OHLC.")

    if "volume" not in cols_lower:
        if require_volume:
            raise DataValidationError("Donnée indisponible : volume requis mais absent.")
        warnings.append(
            "Volume réel non disponible (Forex : uniquement du tick volume le cas échéant)."
        )

    if len(df) < 50:
        warnings.append(
            f"Historique court ({len(df)} bougies) : fiabilité des indicateurs réduite."
        )

    return warnings


def normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Met les colonnes en minuscules et standardise les noms courants."""
    rename_map = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc in ("o", "open"):
            rename_map[c] = "open"
        elif lc in ("h", "high"):
            rename_map[c] = "high"
        elif lc in ("l", "low"):
            rename_map[c] = "low"
        elif lc in ("c", "close", "adj close", "adj_close"):
            rename_map[c] = "close"
        elif lc in ("v", "vol", "volume", "tick_volume"):
            rename_map[c] = "volume"
        elif lc in ("date", "datetime", "time", "timestamp"):
            rename_map[c] = "datetime"
    return df.rename(columns=rename_map)
