"""
RE-ZERO - Page Backtest
Teste une stratégie simple dérivée du Confluence Engine sur des
données historiques, sans look-ahead bias : chaque décision n'utilise
que les données disponibles jusqu'à la bougie évaluée (section 17/18).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app.core import market_structure, regime_engine
from app.core.data_engine import data_engine
from app.core.indicator_engine import atr, compute_all
from app.utils.validators import DataValidationError


def _walk_forward_signals(df: pd.DataFrame, warmup: int = 210) -> pd.DataFrame:
    """
    Génère un signal simple (long/short/flat) recalculé bougie par
    bougie en n'utilisant QUE les données jusqu'à l'instant `i` inclus
    (aucune donnée future) — condition indispensable pour éviter le
    look-ahead bias et le repainting.
    """
    signals = []
    for i in range(warmup, len(df)):
        window = df.iloc[: i + 1]
        indicators = compute_all(window)
        close = window["close"].iloc[-1]
        ema200 = indicators["ema_200"].iloc[-1]
        rsi_val = indicators["rsi_14"].iloc[-1]

        if pd.isna(ema200) or pd.isna(rsi_val):
            signals.append(0)
            continue

        if close > ema200 and rsi_val > 50:
            signals.append(1)
        elif close < ema200 and rsi_val < 50:
            signals.append(-1)
        else:
            signals.append(0)

    padded = [0] * warmup + signals
    return pd.Series(padded, index=df.index, name="signal")


def _run_backtest(df: pd.DataFrame, initial_capital: float = 1000.0) -> dict:
    signals = _walk_forward_signals(df)
    returns = df["close"].pct_change().fillna(0)
    # Position prise à la clôture du signal, appliquée à la barre suivante (pas de look-ahead)
    strategy_returns = signals.shift(1).fillna(0) * returns

    equity_curve = initial_capital * (1 + strategy_returns).cumprod()

    trades = signals.diff().fillna(0) != 0
    n_trades = int(trades.sum())

    wins = strategy_returns[strategy_returns > 0]
    losses = strategy_returns[strategy_returns < 0]

    win_rate = len(wins) / (len(wins) + len(losses)) * 100 if (len(wins) + len(losses)) > 0 else 0
    profit_factor = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")

    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    max_dd = float(drawdown.min() * 100)

    sharpe = 0.0
    if strategy_returns.std() != 0:
        sharpe = float(strategy_returns.mean() / strategy_returns.std() * np.sqrt(252))

    return {
        "equity_curve": equity_curve,
        "n_trades": n_trades,
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else None,
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "final_equity": round(float(equity_curve.iloc[-1]), 2),
    }


def render():
    st.header("🧪 RE-ZERO — Backtest Engine")

    st.caption(
        "Stratégie de démonstration (EMA200 + RSI). Remplace la logique de "
        "`_walk_forward_signals` par ta propre règle dérivée du Confluence Engine."
    )

    uploaded = st.file_uploader("Données OHLCV historiques (CSV)", type=["csv"], key="bt_upload")
    if uploaded is None:
        return

    tmp_path = f"/tmp/bt_{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getbuffer())

    try:
        df, warnings = data_engine.get_data("BACKTEST", "1H", source_path=tmp_path, use_cache=False)
    except DataValidationError as e:
        st.error(str(e))
        return

    for w in warnings:
        st.warning(w)

    if len(df) < 250:
        st.error("Historique trop court pour un backtest fiable (minimum ~250 bougies recommandé).")
        return

    initial_capital = st.number_input("Capital initial", value=1000.0, min_value=1.0)

    if st.button("Lancer le backtest", type="primary"):
        with st.spinner("Backtest en cours (walk-forward, sans look-ahead)..."):
            results = _run_backtest(df, initial_capital)

        st.line_chart(results["equity_curve"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Trades", results["n_trades"])
        c2.metric("Win rate", f"{results['win_rate']}%")
        c3.metric("Profit factor", results["profit_factor"] or "∞")
        c4.metric("Max drawdown", f"{results['max_drawdown_pct']}%")

        c5, c6 = st.columns(2)
        c5.metric("Sharpe ratio", results["sharpe_ratio"])
        c6.metric("Capital final", results["final_equity"])

        st.info(
            "Ces résultats sont calculés sur données historiques connues. "
            "Aucune performance passée ne garantit un résultat futur."
        )
