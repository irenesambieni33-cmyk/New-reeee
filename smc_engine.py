"""
RE-ZERO - Smart Money / Structure Engine (SMC)
Détecte liquidity pools, order blocks, breaker blocks et Fair Value Gaps.

RÈGLE IMPORTANTE (section 6 du prompt) :
On distingue toujours "signal détecté" (structurellement présent)
de "signal confirmé" (validé par un retest ou une réaction de prix).
Chaque objet retourné porte un champ `status` = "detected" | "confirmed".
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class FairValueGap:
    start_index: pd.Timestamp
    end_index: pd.Timestamp
    top: float
    bottom: float
    direction: str  # "bullish" ou "bearish"
    status: str = "detected"


@dataclass
class OrderBlock:
    index: pd.Timestamp
    top: float
    bottom: float
    direction: str  # "bullish" ou "bearish"
    status: str = "detected"


@dataclass
class LiquidityLevel:
    price: float
    kind: str  # "buy_side" ou "sell_side"
    swept: bool = False


def detect_fair_value_gaps(df: pd.DataFrame) -> list[FairValueGap]:
    """
    Un FVG (3-candle pattern) bullish existe quand low[i] > high[i-2]
    (gap entre la bougie i-2 et i, non comblé par i-1).
    Symétrique pour le bearish.
    """
    fvgs: list[FairValueGap] = []
    highs, lows = df["high"].values, df["low"].values

    for i in range(2, len(df)):
        if lows[i] > highs[i - 2]:
            fvgs.append(FairValueGap(
                start_index=df.index[i - 2], end_index=df.index[i],
                top=float(lows[i]), bottom=float(highs[i - 2]), direction="bullish",
            ))
        if highs[i] < lows[i - 2]:
            fvgs.append(FairValueGap(
                start_index=df.index[i - 2], end_index=df.index[i],
                top=float(lows[i - 2]), bottom=float(highs[i]), direction="bearish",
            ))

    # Confirmation : le prix a-t-il retesté (retracé dans) le FVG depuis ?
    closes = df["close"]
    for fvg in fvgs:
        after = closes.loc[fvg.end_index:]
        if len(after) > 1:
            retest = after.iloc[1:]
            touched = ((retest >= fvg.bottom) & (retest <= fvg.top)).any()
            if touched:
                fvg.status = "confirmed"

    return fvgs


def detect_order_blocks(df: pd.DataFrame, displacement_atr_mult: float = 1.5) -> list[OrderBlock]:
    """
    Un order block bullish = dernière bougie baissière avant un
    déplacement haussier fort (displacement). Approche simplifiée basée
    sur l'ATR pour juger ce qu'est un "déplacement fort".
    """
    from app.core.indicator_engine import atr

    atr_series = atr(df, 14)
    blocks: list[OrderBlock] = []

    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values

    for i in range(1, len(df) - 1):
        body = abs(c[i] - o[i])
        a = atr_series.iloc[i] if not pd.isna(atr_series.iloc[i]) else 0
        if a == 0:
            continue

        is_displacement_up = (c[i] - o[i]) > displacement_atr_mult * a
        is_displacement_down = (o[i] - c[i]) > displacement_atr_mult * a

        if is_displacement_up and c[i - 1] < o[i - 1]:
            blocks.append(OrderBlock(df.index[i - 1], float(h[i - 1]), float(l[i - 1]), "bullish"))
        if is_displacement_down and c[i - 1] > o[i - 1]:
            blocks.append(OrderBlock(df.index[i - 1], float(h[i - 1]), float(l[i - 1]), "bearish"))

    # Confirmation par retest
    closes = df["close"]
    for ob in blocks:
        after = closes.loc[ob.index:]
        if len(after) > 1:
            retest = after.iloc[1:]
            touched = ((retest >= ob.bottom) & (retest <= ob.top)).any()
            if touched:
                ob.status = "confirmed"

    return blocks


def detect_liquidity_levels(df: pd.DataFrame, swings) -> list[LiquidityLevel]:
    """
    Identifie les zones de liquidité (equal highs/lows, extrêmes récents)
    et vérifie si elles ont été "sweep" (mèche au-delà, clôture en retrait).
    """
    levels: list[LiquidityLevel] = []
    tolerance = 0.0008  # ~0.08%, à ajuster selon l'actif

    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    def group_equals(swings_list, kind):
        used = set()
        for i, s1 in enumerate(swings_list):
            if i in used:
                continue
            group = [s1]
            for j, s2 in enumerate(swings_list[i + 1:], start=i + 1):
                if j in used:
                    continue
                if abs(s1.price - s2.price) / s1.price < tolerance:
                    group.append(s2)
                    used.add(j)
            if len(group) >= 2:
                avg_price = sum(s.price for s in group) / len(group)
                levels.append(LiquidityLevel(price=avg_price, kind=kind))

    group_equals(highs, "buy_side")
    group_equals(lows, "sell_side")

    # Sweep : le prix a-t-il dépassé le niveau puis clôturé de l'autre côté ?
    for lvl in levels:
        if lvl.kind == "buy_side":
            swept_mask = (df["high"] > lvl.price) & (df["close"] < lvl.price)
        else:
            swept_mask = (df["low"] < lvl.price) & (df["close"] > lvl.price)
        lvl.swept = bool(swept_mask.any())

    return levels
