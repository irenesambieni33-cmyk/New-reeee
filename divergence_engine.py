"""
RE-ZERO - Divergence Engine
Compare la structure du prix (swings) à celle d'un oscillateur pour
détecter les divergences classiques et cachées.

Rappel (section 9) : une divergence n'est JAMAIS une garantie de
retournement, seulement un élément de confluence.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Divergence:
    kind: str  # "bullish", "bearish", "hidden_bullish", "hidden_bearish"
    indicator: str
    first_index: pd.Timestamp
    second_index: pd.Timestamp


def _swings_by_kind(swings, kind):
    return sorted([s for s in swings if s.kind == kind], key=lambda s: s.index)


def detect_divergences(price_swings, oscillator: pd.Series, indicator_name: str = "RSI") -> list[Divergence]:
    divergences: list[Divergence] = []

    for kind, opp_labels in [("low", ("bullish", "hidden_bullish")), ("high", ("bearish", "hidden_bearish"))]:
        pts = _swings_by_kind(price_swings, kind)
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            if p1.index not in oscillator.index or p2.index not in oscillator.index:
                continue
            osc1, osc2 = oscillator.loc[p1.index], oscillator.loc[p2.index]
            if pd.isna(osc1) or pd.isna(osc2):
                continue

            if kind == "low":
                # Régulière bullish : prix LL, oscillateur HL
                if p2.price < p1.price and osc2 > osc1:
                    divergences.append(Divergence(opp_labels[0], indicator_name, p1.index, p2.index))
                # Cachée bullish : prix HL, oscillateur LL (continuation haussière)
                elif p2.price > p1.price and osc2 < osc1:
                    divergences.append(Divergence(opp_labels[1], indicator_name, p1.index, p2.index))
            else:
                # Régulière bearish : prix HH, oscillateur LH
                if p2.price > p1.price and osc2 < osc1:
                    divergences.append(Divergence(opp_labels[0], indicator_name, p1.index, p2.index))
                # Cachée bearish : prix LH, oscillateur HH (continuation baissière)
                elif p2.price < p1.price and osc2 > osc1:
                    divergences.append(Divergence(opp_labels[1], indicator_name, p1.index, p2.index))

    return divergences
