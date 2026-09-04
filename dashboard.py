"""
RE-ZERO - Page Dashboard
Vue d'ensemble : sélection actif/timeframe, graphique, panneaux de
synthèse, score global.
"""
from __future__ import annotations

import streamlit as st

from app.core.analysis_engine import run_full_analysis
from app.core.data_engine import data_engine
from app.core.live_fetcher_yfinance import SYMBOL_MAP
from app.utils.validators import DataValidationError

TIMEFRAMES = ["1min", "3min", "5min", "15min", "30min", "1H", "2H", "4H", "1D", "1W", "1M"]


def render():
    st.header("📊 RE-ZERO — Dashboard")

    source_mode = st.radio(
        "Source des données", ["Live gratuit (Yahoo Finance)", "CSV uploadé"], horizontal=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if source_mode == "Live gratuit (Yahoo Finance)":
            symbol = st.selectbox("Actif", list(SYMBOL_MAP.keys()))
        else:
            symbol = st.text_input("Actif", value=st.session_state.get("symbol", "EUR/USD"))
    with col2:
        base_tf = st.selectbox("Timeframe de base", TIMEFRAMES, index=TIMEFRAMES.index("1H"))
    with col3:
        uploaded = None
        if source_mode == "CSV uploadé":
            uploaded = st.file_uploader("Données OHLCV (CSV)", type=["csv"])

    if source_mode == "Live gratuit (Yahoo Finance)":
        try:
            df, warnings = data_engine.get_data(symbol, base_tf, source_path=None, use_cache=True)
        except DataValidationError as e:
            st.error(str(e))
            st.caption(
                "Le fetcher live ne fonctionne que si l'app tourne avec un accès internet "
                "(ex: Streamlit Community Cloud) et que `yfinance` est installé."
            )
            return
    else:
        if uploaded is None:
            st.info(
                "Upload un CSV OHLCV (colonnes : datetime, open, high, low, close, "
                "volume optionnel)."
            )
            return

        tmp_path = f"/tmp/{uploaded.name}"
        with open(tmp_path, "wb") as f:
            f.write(uploaded.getbuffer())

        try:
            df, warnings = data_engine.get_data(symbol, base_tf, source_path=tmp_path, use_cache=False)
        except DataValidationError as e:
            st.error(str(e))
            return

    for w in warnings:
        st.warning(w)

    htf_map = {"5min": "1H", "15min": "4H", "30min": "4H", "1H": "1D", "4H": "1D", "1D": "1W"}
    ltf_map = {"1H": "15min", "4H": "1H", "1D": "4H", "1W": "1D"}
    htf = htf_map.get(base_tf, "1D")
    ltf = ltf_map.get(base_tf, base_tf)

    mtf_data = data_engine.build_multi_timeframe(df, base_tf, [htf, ltf])

    capital = st.session_state.get("capital", 1000.0)
    risk_percent = st.session_state.get("risk_percent", 1.0)

    if st.button("🔍 ANALYSE COMPLÈTE", type="primary"):
        report = run_full_analysis(
            symbol=symbol, mtf_data=mtf_data, base_tf=base_tf, htf=htf, ltf=ltf,
            capital=capital, risk_percent=risk_percent, data_warnings=warnings,
        )
        st.session_state["last_report"] = report

    report = st.session_state.get("last_report")
    if report is None:
        return

    st.subheader(f"{report.symbol} — {report.timestamp}")

    badge = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡", "NO TRADE": "⚪"}[report.verdict]
    st.markdown(f"## {badge} Verdict : **{report.verdict}** — Grade **{report.grade}** ({report.confidence})")

    st.line_chart(mtf_data[base_tf]["close"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prix actuel", f"{report.current_price:.5f}")
    c2.metric("Régime", report.regime)
    c3.metric("Bullish", f"{report.scores['bullish']}/100")
    c4.metric("Bearish", f"{report.scores['bearish']}/100")

    st.markdown("### Structure")
    st.write(f"HTF: **{report.htf_bias}** · MTF: **{report.mtf_bias}** · LTF: **{report.ltf_bias}**")
    st.write(f"Dernier événement structurel : {report.structure_event or 'aucun'}")

    col_s, col_r = st.columns(2)
    with col_s:
        st.markdown("**Supports**")
        for s in report.supports:
            st.write(f"- {s:.5f}")
    with col_r:
        st.markdown("**Résistances**")
        for r in report.resistances:
            st.write(f"- {r:.5f}")

    st.markdown("### Confluences")
    col_b, col_be = st.columns(2)
    with col_b:
        st.markdown("**Haussières**")
        for c in report.confluences_bullish:
            st.write(f"- {c}")
    with col_be:
        st.markdown("**Baissières**")
        for c in report.confluences_bearish:
            st.write(f"- {c}")

    st.markdown("### Raisonnement")
    st.info(report.reasoning)

    with st.expander("Rapport complet (Markdown)"):
        st.code(report.to_markdown(), language="markdown")
        st.download_button(
            "Télécharger le rapport",
            report.to_markdown(),
            file_name=f"rezero_report_{symbol.replace('/', '')}.md",
        )
