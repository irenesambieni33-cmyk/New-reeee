"""
RE-ZERO - Risk Management Engine (section 14)
Calcule automatiquement la taille de position, le R:R, l'exposition.
Ne recommande JAMAIS d'augmenter le risque simplement parce qu'un
score de confluence est élevé.
"""
from __future__ import annotations

from dataclasses import dataclass

ALLOWED_RISK_PERCENTS = [0.25, 0.5, 1.0, 2.0]


@dataclass
class PositionSizing:
    capital: float
    risk_percent: float
    risk_amount: float
    entry: float
    stop_loss: float
    stop_distance: float
    position_size_units: float
    take_profits: list[float]
    risk_reward_ratios: list[float]


def compute_position_size(capital: float, risk_percent: float, entry: float,
                           stop_loss: float, take_profits: list[float],
                           pip_value_per_unit: float = 1.0) -> PositionSizing:
    if risk_percent not in ALLOWED_RISK_PERCENTS:
        raise ValueError(
            f"risk_percent doit être l'un de {ALLOWED_RISK_PERCENTS} (reçu {risk_percent})."
        )
    if capital <= 0:
        raise ValueError("Le capital doit être positif.")

    stop_distance = abs(entry - stop_loss)
    if stop_distance == 0:
        raise ValueError("Le stop loss ne peut pas être égal au prix d'entrée.")

    risk_amount = capital * (risk_percent / 100)
    position_size_units = risk_amount / (stop_distance * pip_value_per_unit)

    rr_ratios = [round(abs(tp - entry) / stop_distance, 2) for tp in take_profits]

    return PositionSizing(
        capital=capital,
        risk_percent=risk_percent,
        risk_amount=round(risk_amount, 2),
        entry=entry,
        stop_loss=stop_loss,
        stop_distance=round(stop_distance, 6),
        position_size_units=round(position_size_units, 4),
        take_profits=take_profits,
        risk_reward_ratios=rr_ratios,
    )


def is_risk_reward_acceptable(rr_ratios: list[float], minimum: float = 1.5) -> bool:
    """Le meilleur R:R proposé doit au moins atteindre le seuil minimum (défaut 1.5)."""
    return bool(rr_ratios) and max(rr_ratios) >= minimum


def max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 0
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
    return round(max_dd * 100, 2)
