"""
RE-ZERO - Page Analyst
Analyse approfondie d'un actif sélectionné : détail indicateur par
indicateur, patterns détectés, SMC, divergences.
"""
from __future__ import annotations

import streamlit as st

from app.core import (
    divergence_engine,
    fibonacci_engine,
    indicator_engine,
    market_structure,
    pattern_engine,
    smc_engine,
)
from app.core.data_engine import data_engine
from app.utils.validators import DataValidationError


def render():
    st.header("🔬 RE-ZERO — Analyst (mode approfondi)")

    uploaded = st.file_uploader("Données OHLCV (CSV)", type=["csv"], key="analyst_upload")
    if uploaded is None:
        st.info("Upload un CSV OHLCV pour lancer une analyse approfondie.")
        return

    tmp_path = f"/tmp/analyst_{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getbuffer())

    try:
        df, warnings = data_engine.get_data("CUSTOM", "1H", source_path=tmp_path, use_cache=False)
    except DataValidationError as e:
        st.error(str(e))
        return

    for w in warnings:
        st.warning(w)

    tabs = st.tabs(["Indicateurs", "Structure & S/R", "Patterns", "SMC", "Divergences", "Fibonacci"])

    indicators = indicator_engine.compute_all(df)

    with tabs[0]:
        st.subheader("Trend")
        st.line_chart(df[["close"]].join([
            indicators["ema_20"].rename("EMA 20"),
            indicators["ema_50"].rename("EMA 50"),
            indicators["ema_200"].rename("EMA 200"),
        ]))
        st.subheader("Momentum")
        st.line_chart(indicators["rsi_14"].rename("RSI 14"))
        st.line_chart(indicators["macd"][["macd", "signal"]])
        st.subheader("Volatilité")
        st.line_chart(indicators["atr_percent"].rename("ATR %"))
        st.line_chart(indicators["bollinger"][["bb_upper", "bb_mid", "bb_lower"]])

    structure = market_structure.analyze_structure(df)
    with tabs[1]:
        st.write(f"Biais structurel : **{structure.bias}**")
        st.write(f"Dernier événement : {structure.last_event or 'aucun'}")
        st.write("Supports :", [round(s, 5) for s in structure.supports])
        st.write("Résistances :", [round(r, 5) for r in structure.resistances])
        st.write(f"Nombre de swings détectés : {len(structure.swings)}")

    with tabs[2]:
        trend_ctx = structure.bias if structure.bias in ("bullish", "bearish") else "range"
        patterns = pattern_engine.detect_candle_patterns(df, trend_context=trend_ctx)
        doubles = pattern_engine.detect_double_top_bottom(df, structure.swings)
        if patterns:
            st.dataframe([
                {"Date": p.index, "Pattern": p.name, "Direction": p.direction, "Fiabilité": p.reliability_score}
                for p in patterns[-20:]
            ])
        else:
            st.write("Aucun pattern chandelier détecté récemment.")
        if doubles:
            st.write("Patterns graphiques :", doubles)

    with tabs[3]:
        fvgs = smc_engine.detect_fair_value_gaps(df)
        obs = smc_engine.detect_order_blocks(df)
        liq = smc_engine.detect_liquidity_levels(df, structure.swings)
        st.markdown(f"**Fair Value Gaps** ({len(fvgs)} détectés)")
        st.dataframe([
            {"Direction": f.direction, "Top": f.top, "Bottom": f.bottom, "Statut": f.status}
            for f in fvgs[-15:]
        ])
        st.markdown(f"**Order Blocks** ({len(obs)} détectés)")
        st.dataframe([
            {"Direction": o.direction, "Top": o.top, "Bottom": o.bottom, "Statut": o.status}
            for o in obs[-15:]
        ])
        st.markdown(f"**Liquidité** ({len(liq)} niveaux)")
        st.dataframe([
            {"Prix": l.price, "Type": l.kind, "Sweep": l.swept}
            for l in liq
        ])

    with tabs[4]:
        divs = divergence_engine.detect_divergences(structure.swings, indicators["rsi_14"], "RSI")
        if divs:
            st.dataframe([
                {"Type": d.kind, "Indicateur": d.indicator, "De": d.first_index, "À": d.second_index}
                for d in divs
            ])
        else:
            st.write("Aucune divergence RSI détectée.")

    with tabs[5]:
        fib = fibonacci_engine.compute_from_last_swings(structure.swings, float(df["close"].iloc[-1]))
        if fib.get("available"):
            st.write("Retracements :", {k: round(v, 5) for k, v in fib["retracement_levels"].items()})
            st.write("Extensions :", {k: round(v, 5) for k, v in fib["extension_levels"].items()})
            if fib.get("price_near_level"):
                st.success(f"Prix proche du niveau {fib['price_near_level'][0]}")
        else:
            st.write(fib.get("reason"))
