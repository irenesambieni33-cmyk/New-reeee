"""
RE-ZERO CONFLUENCE ENGINE (section 11)
Combine tous les facteurs d'analyse en un score Bullish/Bearish/Neutral,
en évitant explicitement de compter deux fois la même information
(ex: RSI + Stoch + StochRSI = 1 seul facteur "momentum").

Le score produit N'EST PAS une probabilité mathématique de gagner :
c'est une mesure de la densité et de la cohérence des confluences.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Poids max par facteur (doit rester cohérent, total ~100 pour lisibilité)
FACTOR_WEIGHTS = {
    "structure": 15,
    "trend": 12,
    "momentum": 8,
    "volume": 6,
    "volatility": 5,
    "support_resistance": 12,
    "liquidity": 8,
    "fibonacci": 5,
    "multi_timeframe": 15,
    "pattern": 4,
    "smc": 10,
}


@dataclass
class ConfluenceFactor:
    name: str
    direction: str  # "bullish" / "bearish" / "neutral"
    weight: float
    reason: str


@dataclass
class ConfluenceResult:
    factors: list[ConfluenceFactor] = field(default_factory=list)
    bullish_score: float = 0.0
    bearish_score: float = 0.0
    neutral_score: float = 0.0

    def add(self, name: str, direction: str, reason: str):
        weight = FACTOR_WEIGHTS.get(name, 5)
        self.factors.append(ConfluenceFactor(name, direction, weight, reason))
        if direction == "bullish":
            self.bullish_score += weight
        elif direction == "bearish":
            self.bearish_score += weight
        else:
            self.neutral_score += weight

    def normalize(self) -> dict:
        total = self.bullish_score + self.bearish_score + self.neutral_score
        if total == 0:
            return {"bullish": 0, "bearish": 0, "neutral": 100}
        return {
            "bullish": round(100 * self.bullish_score / total, 1),
            "bearish": round(100 * self.bearish_score / total, 1),
            "neutral": round(100 * self.neutral_score / total, 1),
        }

    def bullish_reasons(self) -> list[str]:
        return [f.reason for f in self.factors if f.direction == "bullish"]

    def bearish_reasons(self) -> list[str]:
        return [f.reason for f in self.factors if f.direction == "bearish"]


def build_confluence(mtf_bias: dict, structure_bias: str, structure_event: str | None,
                      indicators: dict, regime: str, patterns: list, divergences: list,
                      liquidity_levels: list, order_blocks: list, fvgs: list,
                      fib_info: dict) -> ConfluenceResult:
    result = ConfluenceResult()

    # --- Multi-timeframe ---
    htf = mtf_bias.get("htf")
    ltf = mtf_bias.get("ltf")
    if htf and htf != "neutral":
        result.add("multi_timeframe", htf, f"Tendance HTF {htf}")
    if ltf and ltf != htf and ltf not in ("neutral", None):
        result.add("multi_timeframe", "neutral",
                    f"LTF ({ltf}) en désaccord avec HTF ({htf}) -> probable correction, pas un retournement confirmé")

    # --- Structure ---
    if structure_bias in ("bullish", "bearish"):
        result.add("structure", structure_bias, f"Structure de prix {structure_bias}")
    if structure_event:
        direction = "bullish" if "bullish" in structure_event else "bearish"
        result.add("structure", direction, f"Événement structurel : {structure_event}")

    # --- Trend (EMA/ADX regroupés en un seul facteur "trend") ---
    ema_trend = indicators.get("ema_trend_direction")
    if ema_trend:
        result.add("trend", ema_trend, "Prix positionné par rapport aux EMA de référence")

    # --- Momentum (RSI/MACD/Stoch fusionnés en 1 facteur si redondants) ---
    momentum_dir = indicators.get("momentum_direction")
    if momentum_dir:
        result.add("momentum", momentum_dir, "Momentum agrégé (RSI/MACD) orienté " + momentum_dir)

    # --- Volatilité (facteur neutre informatif, sauf extrêmes) ---
    vol_state = indicators.get("volatility_state")
    if vol_state == "extreme":
        result.add("volatility", "neutral", "Volatilité extrême : prudence, pas un signal directionnel")

    # --- Régime ---
    if regime in ("strong_bull_trend", "bull_trend", "weak_bull"):
        result.add("trend", "bullish", f"Régime de marché : {regime}")
    elif regime in ("strong_bear_trend", "bear_trend", "weak_bear"):
        result.add("trend", "bearish", f"Régime de marché : {regime}")

    # --- Patterns chandeliers (le plus fiable seulement, pour éviter la redondance) ---
    if patterns:
        best = max(patterns, key=lambda p: p.reliability_score)
        if best.reliability_score >= 55 and best.direction in ("bullish", "bearish"):
            result.add("pattern", best.direction, f"Pattern {best.name} (score {best.reliability_score})")

    # --- Divergences ---
    for div in divergences:
        if div.kind in ("bullish", "hidden_bullish"):
            result.add("momentum", "bullish", f"Divergence {div.kind} ({div.indicator})")
        elif div.kind in ("bearish", "hidden_bearish"):
            result.add("momentum", "bearish", f"Divergence {div.kind} ({div.indicator})")

    # --- Liquidité ---
    for lvl in liquidity_levels:
        if lvl.swept:
            direction = "bullish" if lvl.kind == "sell_side" else "bearish"
            result.add("liquidity", direction, f"Liquidity sweep {lvl.kind} @ {lvl.price:.5f}")

    # --- SMC : order blocks confirmés uniquement ---
    for ob in order_blocks:
        if ob.status == "confirmed":
            result.add("smc", ob.direction, f"Order block {ob.direction} confirmé (retest validé)")
    for fvg in fvgs:
        if fvg.status == "confirmed":
            result.add("smc", fvg.direction, f"Fair Value Gap {fvg.direction} confirmé")

    # --- Fibonacci (jamais seul, uniquement comme confluence de zone) ---
    if fib_info.get("available") and fib_info.get("price_near_level"):
        ratio, level_price = fib_info["price_near_level"]
        direction = fib_info.get("direction", "neutral")
        result.add("fibonacci", direction,
                    f"Prix proche du niveau Fibonacci {ratio} ({level_price:.5f})")

    return result
