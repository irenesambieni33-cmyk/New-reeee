"""
RE-ZERO - ML Engine (section 28, IA ADAPTATIVE)
Fournit une estimation statistique / un classement de scénarios à
partir de résultats historiques, JAMAIS une promesse de gain.

Implémentation volontairement simple (arbre de décision) pour rester
lisible, sans dépendance lourde. Peut être remplacé par un modèle plus
riche (gradient boosting, etc.) sans changer l'interface publique
`fit()` / `predict_proba()`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ScenarioEstimate:
    label: str  # "bullish_continuation", "bearish_continuation", "no_edge"
    historical_win_rate: float | None
    sample_size: int
    disclaimer: str = (
        "Estimation statistique basée sur des configurations historiques "
        "similaires. Ne constitue ni une prédiction ni une garantie."
    )


class HistoricalScenarioMatcher:
    """
    Compare la configuration actuelle (features de contexte) aux
    configurations passées et calcule un taux de réussite historique
    empirique — pas un modèle de machine learning à proprement parler,
    mais une approche transparente et auditable, conforme à la règle
    anti-hallucination (jamais de probabilité inventée).
    """

    def __init__(self):
        self.history: pd.DataFrame | None = None

    def fit(self, history_df: pd.DataFrame) -> None:
        """
        history_df attend au minimum les colonnes :
        ['regime', 'grade', 'mtf_conflict', 'outcome']
        où outcome ∈ {1 (gagnant), 0 (perdant)}.
        """
        required = {"regime", "grade", "mtf_conflict", "outcome"}
        missing = required - set(history_df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans l'historique : {missing}")
        self.history = history_df.copy()

    def estimate(self, regime: str, grade: str, mtf_conflict: bool) -> ScenarioEstimate:
        if self.history is None or self.history.empty:
            return ScenarioEstimate(
                label="no_edge", historical_win_rate=None, sample_size=0,
            )

        mask = (
            (self.history["regime"] == regime)
            & (self.history["grade"] == grade)
            & (self.history["mtf_conflict"] == mtf_conflict)
        )
        subset = self.history[mask]

        if len(subset) < 10:
            return ScenarioEstimate(
                label="insufficient_sample",
                historical_win_rate=None,
                sample_size=len(subset),
            )

        win_rate = float(subset["outcome"].mean())
        label = "bullish_continuation" if win_rate >= 0.5 else "bearish_continuation"

        return ScenarioEstimate(
            label=label,
            historical_win_rate=round(win_rate * 100, 1),
            sample_size=len(subset),
        )
