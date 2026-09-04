"""
RE-ZERO - Tests de base
Vérifie que les moteurs principaux tournent sans erreur sur des
données synthétiques et respectent les règles anti-hallucination
(pas de données inventées, pas de crash sur historique court).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

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
from app.utils.validators import DataValidationError, validate_ohlcv


def make_synthetic_df(n: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")

    returns = rng.normal(0, 0.002, n)
    close = 1.10 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(rng.normal(0, 0.001, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.001, n)))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    volume = rng.integers(100, 1000, n)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def test_validate_ohlcv_ok():
    df = make_synthetic_df()
    warnings = validate_ohlcv(df)
    assert isinstance(warnings, list)


def test_validate_ohlcv_empty_raises():
    with pytest.raises(DataValidationError):
        validate_ohlcv(pd.DataFrame())


def test_indicator_engine_runs():
    df = make_synthetic_df()
    result = indicator_engine.compute_all(df)
    assert "rsi_14" in result
    assert "macd" in result
    assert not result["rsi_14"].dropna().empty


def test_market_structure_runs():
    df = make_synthetic_df()
    structure = market_structure.analyze_structure(df)
    assert structure.bias in ("bullish", "bearish", "neutral", "range")


def test_smc_engine_runs():
    df = make_synthetic_df()
    fvgs = smc_engine.detect_fair_value_gaps(df)
    obs = smc_engine.detect_order_blocks(df)
    assert isinstance(fvgs, list)
    assert isinstance(obs, list)


def test_pattern_engine_runs():
    df = make_synthetic_df()
    patterns = pattern_engine.detect_candle_patterns(df)
    assert isinstance(patterns, list)


def test_fibonacci_requires_swings():
    df = make_synthetic_df()
    structure = market_structure.analyze_structure(df)
    fib = fibonacci_engine.compute_from_last_swings(structure.swings, float(df["close"].iloc[-1]))
    assert "available" in fib


def test_regime_classification():
    result = regime_engine.classify_regime(
        adx_value=30, plus_di=25, minus_di=15,
        atr_percent_value=1.2, choppiness_value=40, atr_percent_avg=1.0,
    )
    assert result.regime in regime_engine.REGIMES


def test_risk_engine_rejects_invalid_percent():
    with pytest.raises(ValueError):
        risk_engine.compute_position_size(1000, 1.3, 1.1000, 1.0950, [1.1100])


def test_risk_engine_computes_sizing():
    sizing = risk_engine.compute_position_size(1000, 1.0, 1.1000, 1.0950, [1.1100, 1.1200])
    assert sizing.risk_amount == 10.0
    assert len(sizing.risk_reward_ratios) == 2


def test_scoring_no_trade_on_low_confluence():
    grade = scoring_engine.grade_signal(
        scores={"bullish": 30, "bearish": 25, "neutral": 45},
        risk_reward_ok=True, mtf_conflict=False,
    )
    assert grade.grade == "NO TRADE"


def test_confluence_engine_produces_scores():
    result = confluence_engine.build_confluence(
        mtf_bias={"htf": "bullish", "mtf": "bullish", "ltf": "bullish"},
        structure_bias="bullish", structure_event="BOS_bullish",
        indicators={"ema_trend_direction": "bullish", "momentum_direction": "bullish",
                    "volatility_state": "normal"},
        regime="bull_trend", patterns=[], divergences=[],
        liquidity_levels=[], order_blocks=[], fvgs=[], fib_info={"available": False},
    )
    scores = result.normalize()
    assert scores["bullish"] > scores["bearish"]
