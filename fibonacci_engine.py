"""
RE-ZERO - Fibonacci Engine
Calcule retracements et extensions. Rappel (section 7 du prompt) :
les niveaux Fibonacci ne constituent JAMAIS seuls une entrée -
ils sont exposés comme zones de confluence potentielles uniquement.
"""
from __future__ import annotations

RETRACEMENT_RATIOS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 0.886, 1.0]
EXTENSION_RATIOS = [1.272, 1.618, 2.0, 2.618]


def retracement_levels(swing_high: float, swing_low: float) -> dict[float, float]:
    diff = swing_high - swing_low
    return {r: swing_high - diff * r for r in RETRACEMENT_RATIOS}


def extension_levels(swing_high: float, swing_low: float, direction: str = "bullish") -> dict[float, float]:
    diff = swing_high - swing_low
    if direction == "bullish":
        return {r: swing_low + diff * r for r in EXTENSION_RATIOS}
    return {r: swing_high - diff * r for r in EXTENSION_RATIOS}


def nearest_level(price: float, levels: dict[float, float], tolerance_pct: float = 0.15) -> tuple[float, float] | None:
    """Retourne (ratio, prix) du niveau Fibonacci le plus proche du prix, si dans la tolérance."""
    best = None
    best_dist = None
    for ratio, level_price in levels.items():
        dist_pct = abs(price - level_price) / price * 100
        if dist_pct <= tolerance_pct and (best_dist is None or dist_pct < best_dist):
            best = (ratio, level_price)
            best_dist = dist_pct
    return best


def compute_from_last_swings(swings, current_price: float) -> dict:
    """
    Construit retracement + extension à partir des deux derniers swings
    opposés (le dernier high et le dernier low disponibles).
    """
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if not highs or not lows:
        return {"available": False, "reason": "Swings insuffisants pour calculer le Fibonacci."}

    last_high = highs[-1]
    last_low = lows[-1]

    direction = "bullish" if last_low.index > last_high.index else "bearish"

    retr = retracement_levels(last_high.price, last_low.price)
    ext = extension_levels(last_high.price, last_low.price, direction=direction)

    confluence = nearest_level(current_price, {**retr})

    return {
        "available": True,
        "swing_high": last_high.price,
        "swing_low": last_low.price,
        "direction": direction,
        "retracement_levels": retr,
        "extension_levels": ext,
        "price_near_level": confluence,
    }
