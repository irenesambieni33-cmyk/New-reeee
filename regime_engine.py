"""
RE-ZERO - Market Regime Engine
Détermine le régime de marché AVANT toute stratégie (section 10).
Les autres moteurs adaptent leur lecture en fonction de ce régime
(ex : ne pas appliquer une logique de range à un marché tendanciel).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REGIMES = [
    "strong_bull_trend", "bull_trend", "weak_bull",
    "range", "compression", "breakout",
    "strong_bear_trend", "bear_trend", "weak_bear",
    "high_volatility", "low_volatility", "transition",
]


@dataclass
class RegimeResult:
    regime: str
    adx_value: float
    atr_percent_value: float
    choppiness_value: float
    explanation: str


def classify_regime(adx_value: float, plus_di: float, minus_di: float,
                     atr_percent_value: float, choppiness_value: float,
                     atr_percent_avg: float) -> RegimeResult:
    """
    Classification simple mais explicite basée sur ADX (force de tendance),
    +DI/-DI (direction), Choppiness Index (range vs trend) et ATR% relatif
    (volatilité actuelle vs moyenne historique).
    """
    reasons = []

    high_vol = atr_percent_value > atr_percent_avg * 1.5
    low_vol = atr_percent_value < atr_percent_avg * 0.6
    is_choppy = choppiness_value > 61.8
    is_trending_chop = choppiness_value < 38.2

    if high_vol:
        reasons.append(f"ATR% ({atr_percent_value:.2f}) largement au-dessus de sa moyenne")
    if is_choppy:
        reasons.append(f"Choppiness Index élevé ({choppiness_value:.1f}) : marché sans direction claire")

    if adx_value >= 40:
        regime = "strong_bull_trend" if plus_di > minus_di else "strong_bear_trend"
        reasons.append(f"ADX très élevé ({adx_value:.1f}) : tendance forte")
    elif adx_value >= 25:
        regime = "bull_trend" if plus_di > minus_di else "bear_trend"
        reasons.append(f"ADX ({adx_value:.1f}) confirme une tendance établie")
    elif adx_value >= 18:
        regime = "weak_bull" if plus_di > minus_di else "weak_bear"
        reasons.append(f"ADX modéré ({adx_value:.1f}) : tendance naissante ou faiblissante")
    else:
        if is_choppy:
            regime = "range"
            reasons.append("Absence de tendance (ADX faible) + choppiness élevé -> range")
        else:
            regime = "compression"
            reasons.append("ADX faible sans choppiness marqué -> possible compression avant breakout")

    if high_vol and regime not in ("strong_bull_trend", "strong_bear_trend"):
        regime = "high_volatility"
    elif low_vol:
        regime = "low_volatility"
        reasons.append(f"ATR% ({atr_percent_value:.2f}) nettement sous sa moyenne : faible volatilité")

    return RegimeResult(
        regime=regime,
        adx_value=adx_value,
        atr_percent_value=atr_percent_value,
        choppiness_value=choppiness_value,
        explanation=" ; ".join(reasons),
    )


def regime_strategy_priority(regime: str) -> list[str]:
    """Retourne les priorités stratégiques adaptées au régime (section 10)."""
    trending = {"strong_bull_trend", "bull_trend", "weak_bull",
                "strong_bear_trend", "bear_trend", "weak_bear", "breakout"}
    ranging = {"range", "compression", "low_volatility"}

    if regime in trending:
        return ["pullback", "continuation", "breakout confirmé", "momentum"]
    if regime in ranging:
        return ["support", "résistance", "extrêmes", "rejet", "mean reversion"]
    if regime == "high_volatility":
        return ["prudence", "réduction de taille", "attendre stabilisation"]
    return ["observation", "attendre confirmation de régime"]
