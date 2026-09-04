"""
RE-ZERO - Market Structure Engine
Analyse le prix indépendamment des indicateurs : swings, HH/HL/LH/LL,
Break of Structure, Change of Character, supports/résistances.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Swing:
    index: pd.Timestamp
    price: float
    kind: str  # "high" ou "low"


@dataclass
class StructureResult:
    swings: list[Swing] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)  # HH/HL/LH/LL alignés sur swings
    bias: str = "neutral"  # bullish / bearish / neutral / range
    last_event: str | None = None  # "BOS_bullish", "CHOCH_bearish", ...
    supports: list[float] = field(default_factory=list)
    resistances: list[float] = field(default_factory=list)


def find_swings(df: pd.DataFrame, lookback: int = 3) -> list[Swing]:
    """
    Détecte les swing highs/lows par comparaison locale (fractal simple) :
    un swing high est un plus haut que `lookback` bougies avant/après.
    """
    highs, lows = df["high"].values, df["low"].values
    swings: list[Swing] = []

    n = len(df)
    for i in range(lookback, n - lookback):
        window_h = highs[i - lookback: i + lookback + 1]
        window_l = lows[i - lookback: i + lookback + 1]

        if highs[i] == window_h.max() and np.argmax(window_h) == lookback:
            swings.append(Swing(df.index[i], float(highs[i]), "high"))
        if lows[i] == window_l.min() and np.argmin(window_l) == lookback:
            swings.append(Swing(df.index[i], float(lows[i]), "low"))

    swings.sort(key=lambda s: s.index)
    return swings


def label_structure(swings: list[Swing]) -> tuple[list[str], str]:
    """
    Étiquette chaque swing en HH/HL/LH/LL en comparant au swing
    précédent du même type, puis détermine un biais global.
    """
    labels: list[str] = []
    last_high: float | None = None
    last_low: float | None = None

    bull_count = 0
    bear_count = 0

    for s in swings:
        if s.kind == "high":
            if last_high is None:
                labels.append("H")
            elif s.price > last_high:
                labels.append("HH")
                bull_count += 1
            else:
                labels.append("LH")
                bear_count += 1
            last_high = s.price
        else:
            if last_low is None:
                labels.append("L")
            elif s.price > last_low:
                labels.append("HL")
                bull_count += 1
            else:
                labels.append("LL")
                bear_count += 1
            last_low = s.price

    if bull_count > bear_count * 1.3:
        bias = "bullish"
    elif bear_count > bull_count * 1.3:
        bias = "bearish"
    elif bull_count == 0 and bear_count == 0:
        bias = "neutral"
    else:
        bias = "range"

    return labels, bias


def detect_bos_choch(swings: list[Swing], labels: list[str]) -> str | None:
    """
    Détecte le dernier événement structurel notable :
    - BOS (Break of Structure) : continuation dans le sens de la tendance
    - CHOCH (Change of Character) : premier signe de retournement
    """
    if len(labels) < 3:
        return None

    last_three = labels[-3:]

    # Séquence bullish qui casse (LH ou LL apparaît après des HH/HL) -> CHOCH bearish
    if last_three[0] in ("HH", "HL") and last_three[1] in ("HH", "HL") and last_three[2] in ("LH", "LL"):
        return "CHOCH_bearish"
    if last_three[0] in ("LH", "LL") and last_three[1] in ("LH", "LL") and last_three[2] in ("HH", "HL"):
        return "CHOCH_bullish"

    if labels[-1] == "HH":
        return "BOS_bullish"
    if labels[-1] == "LL":
        return "BOS_bearish"

    return None


def find_support_resistance(df: pd.DataFrame, swings: list[Swing], tolerance_pct: float = 0.05,
                             max_levels: int = 3) -> tuple[list[float], list[float]]:
    """
    Regroupe les swing lows/highs proches (cluster simple) pour obtenir
    des niveaux de support/résistance robustes plutôt qu'un swing isolé.
    """
    current_price = float(df["close"].iloc[-1])

    highs = sorted([s.price for s in swings if s.kind == "high"], reverse=True)
    lows = sorted([s.price for s in swings if s.kind == "low"])

    def cluster(levels: list[float]) -> list[float]:
        clustered: list[float] = []
        for lvl in levels:
            if not any(abs(lvl - c) / c < tolerance_pct / 100 * 100 for c in clustered):
                clustered.append(lvl)
            if len(clustered) >= max_levels:
                break
        return clustered

    resistances = cluster([h for h in highs if h > current_price]) or cluster(highs)
    supports = cluster([l for l in lows if l < current_price]) or cluster(lows)

    return supports[:max_levels], resistances[:max_levels]


def analyze_structure(df: pd.DataFrame, lookback: int = 3) -> StructureResult:
    swings = find_swings(df, lookback=lookback)
    labels, bias = label_structure(swings)
    last_event = detect_bos_choch(swings, labels)
    supports, resistances = find_support_resistance(df, swings)

    return StructureResult(
        swings=swings,
        labels=labels,
        bias=bias,
        last_event=last_event,
        supports=supports,
        resistances=resistances,
    )
