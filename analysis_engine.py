"""
RE-ZERO - Analysis Engine
Orchestrateur central : exécute la séquence complète décrite en
section 19 (ANALYSE AUTOMATIQUE) et produit le rapport final
(section 20 - RAPPORT FINAL).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from app.core import (
    confluence_engine,
    divergence_engine,
    fibonacci_engine,
    indicator_engine,
    market_structure,
    pattern_engine,
    regime_engine,
    risk_engine,
    scoring_engine,
    smc_engine,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnalysisReport:
    symbol: str
    timestamp: str
    current_price: float
    regime: str
    regime_explanation: str
    htf_bias: str
    mtf_bias: str
    ltf_bias: str
    structure_bias: str
    structure_event: str | None
    supports: list[float]
    resistances: list[float]
    indicators_snapshot: dict
    confluences_bullish: list[str]
    confluences_bearish: list[str]
    scores: dict
    verdict: str  # BULLISH / BEARISH / NEUTRAL / NO TRADE
    grade: str
    confidence: str
    reasoning: str
    data_warnings: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# RE-ZERO MARKET REPORT",
            "",
            f"**Actif :** {self.symbol}",
            f"**Horodatage (UTC) :** {self.timestamp}",
            f"**Prix actuel :** {self.current_price}",
            "",
            f"**Régime :** {self.regime}  \n_{self.regime_explanation}_",
            "",
            "## STRUCTURE",
            f"- Tendance HTF : {self.htf_bias}",
            f"- Tendance MTF : {self.mtf_bias}",
            f"- Tendance LTF : {self.ltf_bias}",
            f"- Biais structurel : {self.structure_bias}",
            f"- Dernier événement : {self.structure_event or 'aucun'}",
            "",
            "## SUPPORTS / RÉSISTANCES",
            f"- Supports : {', '.join(f'{s:.5f}' for s in self.supports) or 'N/A'}",
            f"- Résistances : {', '.join(f'{r:.5f}' for r in self.resistances) or 'N/A'}",
            "",
            "## CONFLUENCES HAUSSIÈRES",
        ]
        lines += [f"- {c}" for c in self.confluences_bullish] or ["- (aucune)"]
        lines += ["", "## CONFLUENCES BAISSIÈRES"]
        lines += [f"- {c}" for c in self.confluences_bearish] or ["- (aucune)"]
        lines += [
            "",
            "## SCORE",
            f"- Bullish : {self.scores.get('bullish')}/100",
            f"- Bearish : {self.scores.get('bearish')}/100",
            f"- Neutral : {self.scores.get('neutral')}/100",
            "",
            f"## VERDICT ANALYTIQUE : {self.verdict}",
            f"**Grade :** {self.grade} — **Confiance :** {self.confidence}",
            "",
            f"_{self.reasoning}_",
        ]
        if self.data_warnings:
            lines += ["", "## AVERTISSEMENTS DONNÉES"]
            lines += [f"- {w}" for w in self.data_warnings]
        return "\n".join(lines)


def _ema_trend_direction(df: pd.DataFrame, indicators: dict) -> str | None:
    close = df["close"].iloc[-1]
    ema200 = indicators["ema_200"].iloc[-1]
    ema50 = indicators["ema_50"].iloc[-1]
    if pd.isna(ema200) or pd.isna(ema50):
        return None
    if close > ema200 and ema50 > ema200:
        return "bullish"
    if close < ema200 and ema50 < ema200:
        return "bearish"
    return "neutral"


def _momentum_direction(indicators: dict) -> str | None:
    rsi_val = indicators["rsi_14"].iloc[-1]
    macd_hist = indicators["macd"]["hist"].iloc[-1]
    if pd.isna(rsi_val) or pd.isna(macd_hist):
        return None
    bullish_votes = int(rsi_val > 55) + int(macd_hist > 0)
    bearish_votes = int(rsi_val < 45) + int(macd_hist < 0)
    if bullish_votes >= 2:
        return "bullish"
    if bearish_votes >= 2:
        return "bearish"
    return "neutral"


def _volatility_state(indicators: dict) -> str:
    atr_pct = indicators["atr_percent"]
    current = atr_pct.iloc[-1]
    avg = atr_pct.rolling(50).mean().iloc[-1] if len(atr_pct) >= 50 else atr_pct.mean()
    if pd.isna(current) or pd.isna(avg) or avg == 0:
        return "normal"
    if current > avg * 1.8:
        return "extreme"
    return "normal"


def _tf_bias_from_structure(df_tf: pd.DataFrame) -> str:
    struct = market_structure.analyze_structure(df_tf)
    return struct.bias


def run_full_analysis(symbol: str, mtf_data: dict[str, pd.DataFrame],
                       base_tf: str, htf: str, ltf: str,
                       capital: float = 1000.0, risk_percent: float = 1.0,
                       data_warnings: list[str] | None = None) -> AnalysisReport:
    """
    mtf_data: dict {timeframe: DataFrame} déjà construit par le DataEngine
    (build_multi_timeframe). Doit contenir au minimum base_tf, htf, ltf.
    """
    data_warnings = data_warnings or []

    df = mtf_data[base_tf]
    current_price = float(df["close"].iloc[-1])

    # 1) Multi-timeframe bias
    htf_bias = _tf_bias_from_structure(mtf_data[htf]) if htf in mtf_data else "neutral"
    mtf_bias = _tf_bias_from_structure(df)
    ltf_bias = _tf_bias_from_structure(mtf_data[ltf]) if ltf in mtf_data else "neutral"
    mtf_conflict = len({htf_bias, ltf_bias} - {"neutral", "range"}) > 1

    # 2) Régime
    indicators = indicator_engine.compute_all(df)
    adx_df = indicators["adx"]
    atr_pct_series = indicators["atr_percent"]
    choppiness_series = indicators["choppiness"]

    regime_result = regime_engine.classify_regime(
        adx_value=float(adx_df["adx"].iloc[-1]) if not pd.isna(adx_df["adx"].iloc[-1]) else 0,
        plus_di=float(adx_df["plus_di"].iloc[-1]) if not pd.isna(adx_df["plus_di"].iloc[-1]) else 0,
        minus_di=float(adx_df["minus_di"].iloc[-1]) if not pd.isna(adx_df["minus_di"].iloc[-1]) else 0,
        atr_percent_value=float(atr_pct_series.iloc[-1]) if not pd.isna(atr_pct_series.iloc[-1]) else 0,
        choppiness_value=float(choppiness_series.iloc[-1]) if not pd.isna(choppiness_series.iloc[-1]) else 50,
        atr_percent_avg=float(atr_pct_series.mean()) if not atr_pct_series.isna().all() else 1,
    )

    # 3) Structure de prix + S/R
    structure = market_structure.analyze_structure(df)

    # 4) Patterns chandeliers
    trend_ctx = "bullish" if mtf_bias == "bullish" else "bearish" if mtf_bias == "bearish" else "range"
    patterns = pattern_engine.detect_candle_patterns(df, trend_context=trend_ctx)

    # 5) Divergences (RSI en référence)
    divergences = divergence_engine.detect_divergences(structure.swings, indicators["rsi_14"], "RSI")

    # 6) SMC
    fvgs = smc_engine.detect_fair_value_gaps(df)
    order_blocks = smc_engine.detect_order_blocks(df)
    liquidity_levels = smc_engine.detect_liquidity_levels(df, structure.swings)

    # 7) Fibonacci
    fib_info = fibonacci_engine.compute_from_last_swings(structure.swings, current_price)
    if fib_info.get("available"):
        fib_info["direction"] = mtf_bias if mtf_bias in ("bullish", "bearish") else "neutral"

    # 8) Indicateurs agrégés (facteurs "trend"/"momentum"/"volatility")
    indicator_summary = {
        "ema_trend_direction": _ema_trend_direction(df, indicators),
        "momentum_direction": _momentum_direction(indicators),
        "volatility_state": _volatility_state(indicators),
    }

    # 9) Confluence
    confluence = confluence_engine.build_confluence(
        mtf_bias={"htf": htf_bias, "mtf": mtf_bias, "ltf": ltf_bias},
        structure_bias=structure.bias,
        structure_event=structure.last_event,
        indicators=indicator_summary,
        regime=regime_result.regime,
        patterns=patterns,
        divergences=divergences,
        liquidity_levels=liquidity_levels,
        order_blocks=order_blocks,
        fvgs=fvgs,
        fib_info=fib_info,
    )
    scores = confluence.normalize()

    # 10) Risk/Reward (utilise le support/résistance le plus proche comme TP/SL indicatifs)
    rr_ok = False
    if structure.supports and structure.resistances:
        try:
            if scores["bullish"] >= scores["bearish"]:
                entry = current_price
                stop = min(structure.supports)
                tps = sorted([r for r in structure.resistances if r > entry]) or structure.resistances
            else:
                entry = current_price
                stop = max(structure.resistances)
                tps = sorted([s for s in structure.supports if s < entry], reverse=True) or structure.supports
            sizing = risk_engine.compute_position_size(capital, risk_percent, entry, stop, tps)
            rr_ok = risk_engine.is_risk_reward_acceptable(sizing.risk_reward_ratios)
        except (ValueError, ZeroDivisionError) as exc:
            logger.warning(f"Calcul R:R impossible : {exc}")
            rr_ok = False

    # 11) Grade final
    grade_result = scoring_engine.grade_signal(
        scores=scores, risk_reward_ok=rr_ok, mtf_conflict=mtf_conflict,
        data_sufficient=len(df) >= 50,
    )

    if grade_result.grade == "NO TRADE":
        verdict = "NO TRADE"
    elif scores["bullish"] > scores["bearish"] and scores["bullish"] >= 50:
        verdict = "BULLISH"
    elif scores["bearish"] > scores["bullish"] and scores["bearish"] >= 50:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    bullish_reasons = confluence.bullish_reasons()
    bearish_reasons = confluence.bearish_reasons()

    if verdict in ("BULLISH", "BEARISH"):
        reasoning = (
            f"Le biais est {verdict.lower()} car : " + "; ".join(
                bullish_reasons if verdict == "BULLISH" else bearish_reasons
            ) or "confluence limitée."
        )
        opposite = bearish_reasons if verdict == "BULLISH" else bullish_reasons
        if opposite:
            reasoning += " Éléments contradictoires à surveiller : " + "; ".join(opposite) + "."
    else:
        reasoning = grade_result.reason

    return AnalysisReport(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
        current_price=current_price,
        regime=regime_result.regime,
        regime_explanation=regime_result.explanation,
        htf_bias=htf_bias,
        mtf_bias=mtf_bias,
        ltf_bias=ltf_bias,
        structure_bias=structure.bias,
        structure_event=structure.last_event,
        supports=structure.supports,
        resistances=structure.resistances,
        indicators_snapshot={
            "RSI_14": round(float(indicators["rsi_14"].iloc[-1]), 2) if not pd.isna(indicators["rsi_14"].iloc[-1]) else None,
            "MACD_hist": round(float(indicators["macd"]["hist"].iloc[-1]), 6) if not pd.isna(indicators["macd"]["hist"].iloc[-1]) else None,
            "ADX": round(float(adx_df["adx"].iloc[-1]), 2) if not pd.isna(adx_df["adx"].iloc[-1]) else None,
            "ATR": round(float(indicators["atr_14"].iloc[-1]), 6) if not pd.isna(indicators["atr_14"].iloc[-1]) else None,
        },
        confluences_bullish=bullish_reasons,
        confluences_bearish=bearish_reasons,
        scores=scores,
        verdict=verdict,
        grade=grade_result.grade,
        confidence=grade_result.confidence_label,
        reasoning=reasoning,
        data_warnings=data_warnings,
    )
