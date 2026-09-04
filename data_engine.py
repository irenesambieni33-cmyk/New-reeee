"""
RE-ZERO - Data Engine
Gère le chargement des données OHLCV (CSV local, ou toute fonction
d'API que l'utilisateur branche), le rééchantillonnage multi-timeframe,
et le cache.

IMPORTANT (limitation assumée) :
Cet environnement n'a pas d'accès réseau. Ce module ne contacte donc
AUCUNE API en ligne par défaut. Il fournit :
  1) un loader CSV/parquet local (fonctionne partout) ;
  2) un point d'extension `fetch_live()` que TU dois implémenter avec
     ta propre clé API / connexion (yfinance, broker, ccxt, etc.)
     une fois déployé dans un environnement avec accès réseau.

RE-ZERO ne doit jamais inventer une donnée manquante : si aucune
source n'est disponible, une DataValidationError est levée.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from app.utils.cache import cache_dataframe, load_cached_dataframe, memory_cache
from app.utils.logger import get_logger
from app.utils.validators import DataValidationError, normalize_ohlcv_columns, validate_ohlcv

logger = get_logger(__name__)

# Mapping timeframe -> règle de resample pandas
TIMEFRAME_RULES = {
    "1min": "1min",
    "3min": "3min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "1H": "1h",
    "2H": "2h",
    "4H": "4h",
    "1D": "1D",
    "1W": "1W",
    "1M": "1ME",
}

TIMEFRAME_ORDER = list(TIMEFRAME_RULES.keys())


class DataEngine:
    def __init__(self):
        self._live_fetcher: Optional[Callable[[str, str], pd.DataFrame]] = None

    def register_live_fetcher(self, fn: Callable[[str, str], pd.DataFrame]) -> None:
        """
        Permet de brancher une vraie source de données live une fois
        déployé avec accès réseau, sans toucher au reste du code.

        fn(symbol, timeframe) -> DataFrame avec colonnes
        [open, high, low, close, volume] et un DatetimeIndex.
        """
        self._live_fetcher = fn
        logger.info("Live fetcher enregistré.")

    def load_csv(self, path: str | Path, datetime_col: Optional[str] = None) -> pd.DataFrame:
        path = Path(path)
        if not path.exists():
            raise DataValidationError(f"Donnée indisponible : fichier introuvable ({path}).")

        df = pd.read_csv(path)
        df = normalize_ohlcv_columns(df)

        dt_col = datetime_col or ("datetime" if "datetime" in df.columns else None)
        if dt_col is None:
            raise DataValidationError(
                "Donnée indisponible : aucune colonne de date/heure identifiable dans le CSV."
            )

        df[dt_col] = pd.to_datetime(df[dt_col], utc=True, errors="coerce")
        df = df.dropna(subset=[dt_col]).set_index(dt_col).sort_index()

        warnings = validate_ohlcv(df)
        for w in warnings:
            logger.warning(w)

        return df

    def get_data(self, symbol: str, timeframe: str, source_path: Optional[str] = None,
                 use_cache: bool = True) -> tuple[pd.DataFrame, list[str]]:
        """
        Point d'entrée principal. Retourne (df, warnings).
        Priorité : cache mémoire -> fichier local fourni -> live fetcher enregistré.
        """
        cache_key = f"{symbol}_{timeframe}"

        if use_cache:
            cached = memory_cache.get(cache_key, ttl_seconds=30)
            if cached is not None:
                return cached, ["Données servies depuis le cache mémoire."]

        if source_path:
            df = self.load_csv(source_path)
        elif self._live_fetcher:
            df = self._live_fetcher(symbol, timeframe)
            df = normalize_ohlcv_columns(df)
        else:
            raise DataValidationError(
                "Donnée indisponible : aucune source (CSV ou live fetcher) n'a été fournie "
                "pour ce symbole. Cet environnement n'a pas d'accès réseau par défaut."
            )

        warnings = validate_ohlcv(df)
        memory_cache.set(cache_key, df)
        return df, warnings

    @staticmethod
    def resample(df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """Rééchantillonne un DataFrame OHLCV vers un timeframe supérieur."""
        if target_timeframe not in TIMEFRAME_RULES:
            raise ValueError(f"Timeframe inconnu : {target_timeframe}")

        rule = TIMEFRAME_RULES[target_timeframe]
        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
        if "volume" in df.columns:
            agg["volume"] = "sum"

        out = df.resample(rule).agg(agg).dropna(subset=["open", "high", "low", "close"])
        return out

    def build_multi_timeframe(self, df_base: pd.DataFrame, base_tf: str,
                               target_tfs: list[str]) -> dict[str, pd.DataFrame]:
        """
        Construit un dict {timeframe: DataFrame} à partir d'un DataFrame
        de base, en resamplant uniquement vers des timeframes supérieurs
        ou égaux (on ne peut jamais "inventer" une granularité plus fine).
        """
        base_idx = TIMEFRAME_ORDER.index(base_tf) if base_tf in TIMEFRAME_ORDER else 0
        result = {base_tf: df_base}

        for tf in target_tfs:
            if tf == base_tf:
                continue
            tf_idx = TIMEFRAME_ORDER.index(tf) if tf in TIMEFRAME_ORDER else -1
            if tf_idx < base_idx:
                logger.warning(
                    f"Impossible de dériver {tf} depuis {base_tf} (granularité plus fine)."
                )
                continue
            result[tf] = self.resample(df_base, tf)

        return result

    def is_candle_closed(self, df: pd.DataFrame, timeframe: str) -> pd.Series:
        """
        Marque chaque bougie comme LIVE ou CLOSED en comparant sa fin
        théorique à l'heure actuelle. Nécessaire pour le No-Repaint Engine.
        """
        rule = TIMEFRAME_RULES.get(timeframe, "1D")
        now = pd.Timestamp.utcnow()
        period_end = df.index.to_series().dt.tz_convert("UTC") + pd.tseries.frequencies.to_offset(rule)
        return period_end <= now


data_engine = DataEngine()
