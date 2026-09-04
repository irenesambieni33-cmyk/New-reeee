"""
RE-ZERO - Live Fetcher (yfinance, 100% gratuit, sans clé API)
Branche une vraie source de données live sur le Data Engine, en
utilisant Yahoo Finance via la librairie `yfinance` (gratuite,
pas de compte ni de clé API nécessaire).

Couverture :
  - Forex   : EURUSD=X, GBPUSD=X, USDJPY=X, XAUUSD=X, XAGUSD=X, ...
  - Crypto  : BTC-USD, ETH-USD, ...
  - Indices : ^GSPC (S&P500), ^NDX (Nasdaq100), ^DJI (Dow Jones),
              ^GDAXI (DAX), ^FCHI (CAC40)
  - Matières premières : GC=F (Gold), SI=F (Silver), CL=F (Oil)

LIMITES à connaître (gratuit = compromis) :
  - Pas de vrai flux temps réel tick-par-tick, données différées de
    quelques minutes selon l'actif.
  - Granularité 1min/5min limitée aux ~60 derniers jours par Yahoo.
  - Yahoo peut rate-limiter en cas d'usage intensif : le cache du
    Data Engine (cache.py) est donc important à conserver.
  - Ne fonctionne que dans un environnement AVEC accès internet
    (pas dans le sandbox qui a généré ce code).

Usage (à mettre en tout début de app/main.py) :

    from app.core.live_fetcher_yfinance import fetch_live, SYMBOL_MAP
    from app.core.data_engine import data_engine
    data_engine.register_live_fetcher(fetch_live)
"""
from __future__ import annotations

import pandas as pd

from app.utils.logger import get_logger
from app.utils.validators import DataValidationError, normalize_ohlcv_columns

logger = get_logger(__name__)

# Mapping "nom lisible" -> ticker Yahoo Finance
SYMBOL_MAP = {
    # Forex
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X", "NZD/USD": "NZDUSD=X",
    "USD/CAD": "USDCAD=X", "XAU/USD": "XAUUSD=X", "XAG/USD": "XAGUSD=X",
    # Crypto
    "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
    # Indices
    "NASDAQ": "^NDX", "S&P 500": "^GSPC", "DOW JONES": "^DJI",
    "DAX": "^GDAXI", "CAC 40": "^FCHI",
    # Matières premières
    "GOLD": "GC=F", "SILVER": "SI=F", "OIL": "CL=F",
}

# Mapping timeframe RE-ZERO -> (interval yfinance, période max conseillée)
INTERVAL_MAP = {
    "1min": ("1m", "7d"),
    "5min": ("5m", "60d"),
    "15min": ("15m", "60d"),
    "30min": ("30m", "60d"),
    "1H": ("1h", "730d"),
    "4H": ("1h", "730d"),  # yfinance ne fait pas de 4H natif -> resample ensuite
    "1D": ("1d", "10y"),
    "1W": ("1wk", "20y"),
    "1M": ("1mo", "max"),
}


def fetch_live(symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Fonction à enregistrer via data_engine.register_live_fetcher().
    Lève DataValidationError si aucune donnée n'est disponible - ne
    retourne JAMAIS de données inventées.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise DataValidationError(
            "yfinance n'est pas installé. Ajoute `yfinance` à requirements.txt "
            "et fais `pip install yfinance`."
        ) from exc

    ticker = SYMBOL_MAP.get(symbol, symbol)  # autorise aussi un ticker Yahoo direct
    interval, period = INTERVAL_MAP.get(timeframe, ("1d", "10y"))

    logger.info(f"Fetch live yfinance : {ticker} ({interval}, {period})")

    try:
        raw = yf.download(ticker, interval=interval, period=period,
                           progress=False, auto_adjust=False)
    except Exception as exc:  # noqa: BLE001 - toute erreur réseau/Yahoo doit remonter clairement
        raise DataValidationError(f"Donnée indisponible : échec de récupération Yahoo Finance ({exc}).") from exc

    if raw is None or raw.empty:
        raise DataValidationError(
            f"Donnée indisponible : aucune donnée retournée par Yahoo Finance pour {ticker}."
        )

    # yfinance peut retourner des colonnes multi-index (Ticker, OHLCV) selon version
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]

    raw = raw.rename(columns={"Open": "open", "High": "high", "Low": "low",
                               "Close": "close", "Volume": "volume"})
    raw.index.name = "datetime"
    df = normalize_ohlcv_columns(raw.reset_index()).set_index("datetime")

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    # 4H n'existe pas nativement chez Yahoo -> on resample depuis le 1H
    if timeframe == "4H":
        from app.core.data_engine import DataEngine
        df = DataEngine.resample(df, "4H")

    return df[["open", "high", "low", "close"] + (["volume"] if "volume" in df.columns else [])]
