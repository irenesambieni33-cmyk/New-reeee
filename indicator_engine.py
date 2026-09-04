"""
RE-ZERO - Indicator Engine
Calcule les indicateurs techniques en pandas/numpy pur (aucune
dépendance à une lib externe type ta-lib, pour rester portable).

RE-ZERO évite la redondance : les indicateurs sont regroupés par
famille (trend / momentum / volatilité / volume) pour permettre au
Confluence Engine de ne pas compter 3 fois la même information
(ex : RSI + Stoch + StochRSI mesurent tous le momentum).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# TREND
# ----------------------------------------------------------------------

def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def wma(series: pd.Series, length: int) -> pd.Series:
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def hma(series: pd.Series, length: int) -> pd.Series:
    half = wma(series, length // 2)
    full = wma(series, length)
    raw = 2 * half - full
    return wma(raw, max(int(np.sqrt(length)), 1))


def dema(series: pd.Series, length: int) -> pd.Series:
    e1 = ema(series, length)
    e2 = ema(e1, length)
    return 2 * e1 - e2


def tema(series: pd.Series, length: int) -> pd.Series:
    e1 = ema(series, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return 3 * e1 - 3 * e2 + e3


def vwma(df: pd.DataFrame, length: int) -> pd.Series:
    if "volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    pv = df["close"] * df["volume"]
    return pv.rolling(length).sum() / df["volume"].rolling(length).sum()


def parabolic_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    high, low = df["high"].values, df["low"].values
    sar = np.zeros(len(df))
    trend_up = True
    af = af_step
    ep = high[0]
    sar[0] = low[0]

    for i in range(1, len(df)):
        prev_sar = sar[i - 1]
        if trend_up:
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = min(sar[i], low[i - 1], low[max(i - 2, 0)])
            if high[i] > ep:
                ep = high[i]
                af = min(af + af_step, af_max)
            if low[i] < sar[i]:
                trend_up = False
                sar[i] = ep
                ep = low[i]
                af = af_step
        else:
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = max(sar[i], high[i - 1], high[max(i - 2, 0)])
            if low[i] < ep:
                ep = low[i]
                af = min(af + af_step, af_max)
            if high[i] > sar[i]:
                trend_up = True
                sar[i] = ep
                ep = high[i]
                af = af_step

    return pd.Series(sar, index=df.index)


def adx(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    high, low, close = df["high"], df["low"], df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat([
        (high - low),
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)

    atr_ = tr.ewm(alpha=1 / length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_ = dx.ewm(alpha=1 / length, adjust=False).mean()

    return pd.DataFrame({"plus_di": plus_di, "minus_di": minus_di, "adx": adx_})


def aroon(df: pd.DataFrame, length: int = 25) -> pd.DataFrame:
    high, low = df["high"], df["low"]
    up = 100 * high.rolling(length + 1).apply(lambda x: x.argmax(), raw=True) / length
    down = 100 * low.rolling(length + 1).apply(lambda x: x.argmin(), raw=True) / length
    return pd.DataFrame({"aroon_up": up, "aroon_down": down})


def ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    high, low, close = df["high"], df["low"], df["close"]

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    chikou = close.shift(-26)

    return pd.DataFrame({
        "tenkan_sen": tenkan,
        "kijun_sen": kijun,
        "senkou_span_a": senkou_a,
        "senkou_span_b": senkou_b,
        "chikou_span": chikou,
    })


# ----------------------------------------------------------------------
# MOMENTUM
# ----------------------------------------------------------------------

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def stochastic(df: pd.DataFrame, k_length: int = 14, d_length: int = 3) -> pd.DataFrame:
    low_min = df["low"].rolling(k_length).min()
    high_max = df["high"].rolling(k_length).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    d = k.rolling(d_length).mean()
    return pd.DataFrame({"k": k, "d": d})


def stochastic_rsi(series: pd.Series, rsi_length: int = 14, stoch_length: int = 14) -> pd.Series:
    rsi_series = rsi(series, rsi_length)
    low_min = rsi_series.rolling(stoch_length).min()
    high_max = rsi_series.rolling(stoch_length).max()
    return 100 * (rsi_series - low_min) / (high_max - low_min).replace(0, np.nan)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def roc(series: pd.Series, length: int = 12) -> pd.Series:
    return 100 * (series - series.shift(length)) / series.shift(length)


def cci(df: pd.DataFrame, length: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(length).mean()
    mad = tp.rolling(length).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))


def williams_r(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high_max = df["high"].rolling(length).max()
    low_min = df["low"].rolling(length).min()
    return -100 * (high_max - df["close"]) / (high_max - low_min).replace(0, np.nan)


def awesome_oscillator(df: pd.DataFrame) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2
    return sma(median_price, 5) - sma(median_price, 34)


def trix(series: pd.Series, length: int = 15) -> pd.Series:
    e1 = ema(series, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return 100 * e3.pct_change()


# ----------------------------------------------------------------------
# VOLATILITÉ
# ----------------------------------------------------------------------

def true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    return pd.concat([
        (high - low),
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / length, adjust=False).mean()


def atr_percent(df: pd.DataFrame, length: int = 14) -> pd.Series:
    return 100 * atr(df, length) / df["close"]


def bollinger_bands(series: pd.Series, length: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(series, length)
    std = series.rolling(length).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width})


def keltner_channels(df: pd.DataFrame, length: int = 20, mult: float = 2.0) -> pd.DataFrame:
    mid = ema(df["close"], length)
    band = mult * atr(df, length)
    return pd.DataFrame({"kc_mid": mid, "kc_upper": mid + band, "kc_lower": mid - band})


def donchian_channels(df: pd.DataFrame, length: int = 20) -> pd.DataFrame:
    upper = df["high"].rolling(length).max()
    lower = df["low"].rolling(length).min()
    return pd.DataFrame({"dc_upper": upper, "dc_lower": lower, "dc_mid": (upper + lower) / 2})


def choppiness_index(df: pd.DataFrame, length: int = 14) -> pd.Series:
    tr_sum = true_range(df).rolling(length).sum()
    high_max = df["high"].rolling(length).max()
    low_min = df["low"].rolling(length).min()
    return 100 * np.log10(tr_sum / (high_max - low_min).replace(0, np.nan)) / np.log10(length)


# ----------------------------------------------------------------------
# VOLUME (uniquement si la colonne 'volume' est réellement présente)
# ----------------------------------------------------------------------

def obv(df: pd.DataFrame) -> pd.Series:
    if "volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    direction = np.sign(df["close"].diff()).fillna(0)
    return (direction * df["volume"]).cumsum()


def vwap(df: pd.DataFrame) -> pd.Series:
    if "volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).cumsum() / df["volume"].cumsum()


def mfi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    if "volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    raw_mf = tp * df["volume"]
    positive = raw_mf.where(tp > tp.shift(), 0.0)
    negative = raw_mf.where(tp < tp.shift(), 0.0)
    mfr = positive.rolling(length).sum() / negative.rolling(length).sum().replace(0, np.nan)
    return 100 - (100 / (1 + mfr))


def chaikin_money_flow(df: pd.DataFrame, length: int = 20) -> pd.Series:
    if "volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"]).replace(0, np.nan)
    mfv = mfm * df["volume"]
    return mfv.rolling(length).sum() / df["volume"].rolling(length).sum()


# ----------------------------------------------------------------------
# CALCUL GROUPÉ
# ----------------------------------------------------------------------

def compute_all(df: pd.DataFrame) -> dict:
    """
    Calcule un jeu d'indicateurs représentatif par famille, en évitant
    la redondance (voir docstring du module). Retourne un dict de
    Series/DataFrames prêt à consommer par les autres engines.
    """
    close = df["close"]

    result = {
        "ema_20": ema(close, 20),
        "ema_50": ema(close, 50),
        "ema_200": ema(close, 200),
        "sma_50": sma(close, 50),
        "sma_200": sma(close, 200),
        "adx": adx(df),
        "ichimoku": ichimoku(df),
        "rsi_14": rsi(close, 14),
        "stochastic": stochastic(df),
        "macd": macd(close),
        "cci": cci(df),
        "awesome_oscillator": awesome_oscillator(df),
        "atr_14": atr(df, 14),
        "atr_percent": atr_percent(df, 14),
        "bollinger": bollinger_bands(close, 20),
        "keltner": keltner_channels(df, 20),
        "donchian": donchian_channels(df, 20),
        "choppiness": choppiness_index(df, 14),
    }

    if "volume" in df.columns:
        result["obv"] = obv(df)
        result["vwap"] = vwap(df)
        result["mfi"] = mfi(df)
        result["cmf"] = chaikin_money_flow(df)

    return result
