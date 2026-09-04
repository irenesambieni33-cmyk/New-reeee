"""
RE-ZERO - Signal Quality Engine (section 12)
Classe une configuration : A+, A, B, C, ou NO TRADE.
Une IA sérieuse doit savoir ne rien faire.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalGrade:
    grade: str  # "A+", "A", "B", "C", "NO TRADE"
    dominant_score: float
    confidence_label: str  # Faible / Modéré / Élevé / Très élevé
    reason: str


def grade_signal(scores: dict, risk_reward_ok: bool, mtf_conflict: bool,
                  data_sufficient: bool = True) -> SignalGrade:
    """
    scores: {"bullish": x, "bearish": y, "neutral": z} (déjà normalisés /100)
    """
    if not data_sufficient:
        return SignalGrade("NO TRADE", 0, "Faible", "Données insuffisantes pour statuer.")

    dominant = max(scores, key=scores.get)
    dominant_score = scores[dominant]

    if dominant == "neutral" or dominant_score < 40:
        return SignalGrade("NO TRADE", dominant_score, "Faible",
                            "Aucune confluence dominante suffisamment nette.")

    if not risk_reward_ok:
        return SignalGrade("NO TRADE", dominant_score, "Faible",
                            "Confluence présente mais Risk/Reward insuffisant.")

    if mtf_conflict and dominant_score < 65:
        return SignalGrade("C", dominant_score, "Modéré",
                            "Conflit multi-timeframe non résolu : configuration faible.")

    if dominant_score >= 80 and not mtf_conflict:
        grade, conf = "A+", "Très élevé"
    elif dominant_score >= 65:
        grade, conf = "A", "Élevé"
    elif dominant_score >= 50:
        grade, conf = "B", "Modéré"
    else:
        grade, conf = "C", "Faible"

    reason = f"Score {dominant} dominant à {dominant_score}/100."
    if mtf_conflict:
        reason += " Conflit multi-timeframe présent : à surveiller."

    return SignalGrade(grade, dominant_score, conf, reason)
