"""
RE-ZERO - Pattern Engine
Détecte les patterns chandeliers (règles géométriques simples) et
attribue un score de fiabilité contextuel (ex : un marteau après un
downtrend a plus de valeur qu'au milieu d'un range).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CandlePattern:
    index: pd.Timestamp
    name: str
    direction: str  # "bullish" / "bearish" / "neutral"
    reliability_score: int  # 0-100, dépend du contexte


def _body(o, c):
    return abs(c - o)


def _range(h, l):
    return max(h - l, 1e-12)


def detect_candle_patterns(df: pd.DataFrame, trend_context: str = "neutral") -> list[CandlePattern]:
    """
    trend_context: "bullish" | "bearish" | "range" - utilisé pour pondérer
    la fiabilité (ex : un Hammer en fin de downtrend est plus fiable).
    """
    patterns: list[CandlePattern] = []
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    for i in range(1, len(df)):
        body = _body(o.iloc[i], c.iloc[i])
        rng = _range(h.iloc[i], l.iloc[i])
        upper_wick = h.iloc[i] - max(o.iloc[i], c.iloc[i])
        lower_wick = min(o.iloc[i], c.iloc[i]) - l.iloc[i]
        idx = df.index[i]

        # Doji
        if body / rng < 0.1:
            patterns.append(CandlePattern(idx, "Doji", "neutral", 40))

        # Hammer (petit corps, longue mèche basse, peu de mèche haute)
        if lower_wick > 2 * body and upper_wick < body and body / rng > 0.05:
            score = 70 if trend_context == "bearish" else 40
            patterns.append(CandlePattern(idx, "Hammer", "bullish", score))

        # Shooting Star
        if upper_wick > 2 * body and lower_wick < body and body / rng > 0.05:
            score = 70 if trend_context == "bullish" else 40
            patterns.append(CandlePattern(idx, "Shooting Star", "bearish", score))

        # Engulfing (par rapport à la bougie précédente)
        prev_o, prev_c = o.iloc[i - 1], c.iloc[i - 1]
        prev_body = _body(prev_o, prev_c)
        if c.iloc[i] > o.iloc[i] and prev_c < prev_o and c.iloc[i] > prev_o and o.iloc[i] < prev_c:
            score = 75 if trend_context == "bearish" else 50
            patterns.append(CandlePattern(idx, "Bullish Engulfing", "bullish", score))
        if c.iloc[i] < o.iloc[i] and prev_c > prev_o and o.iloc[i] > prev_c and c.iloc[i] < prev_o:
            score = 75 if trend_context == "bullish" else 50
            patterns.append(CandlePattern(idx, "Bearish Engulfing", "bearish", score))

        # Marubozu (quasi pas de mèches)
        if body / rng > 0.9:
            direction = "bullish" if c.iloc[i] > o.iloc[i] else "bearish"
            patterns.append(CandlePattern(idx, "Marubozu", direction, 55))

        # Pin Bar générique (mèche dominante d'un côté)
        if lower_wick > 2.5 * body and lower_wick > upper_wick * 2:
            patterns.append(CandlePattern(idx, "Pin Bar (bullish)", "bullish", 60))
        if upper_wick > 2.5 * body and upper_wick > lower_wick * 2:
            patterns.append(CandlePattern(idx, "Pin Bar (bearish)", "bearish", 60))

    return patterns


def detect_double_top_bottom(df: pd.DataFrame, swings, tolerance_pct: float = 0.3) -> list[dict]:
    """Détecte des doubles sommets/creux à partir des swings déjà identifiés."""
    results = []
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    for group, kind, name in [(highs, "bearish", "Double Top"), (lows, "bullish", "Double Bottom")]:
        for i in range(len(group) - 1):
            p1, p2 = group[i], group[i + 1]
            if abs(p1.price - p2.price) / p1.price * 100 < tolerance_pct:
                results.append({
                    "name": name,
                    "direction": kind,
                    "level": (p1.price + p2.price) / 2,
                    "first_index": p1.index,
                    "second_index": p2.index,
                })
    return results
