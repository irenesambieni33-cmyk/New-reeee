"""
RE-ZERO - Page Scanner
Examine plusieurs actifs (plusieurs CSV uploadés) et produit un
tableau filtrable par verdict/grade (section 27).
"""
from __future__ import annotations

import streamlit as st

from app.core.analysis_engine import run_full_analysis
from app.core.data_engine import data_engine
from app.utils.validators import DataValidationError


def render():
    st.header("🛰️ RE-ZERO — Scanner")

    st.write(
        "Upload plusieurs fichiers CSV OHLCV (un par actif) pour scanner "
        "l'ensemble et filtrer les meilleures configurations."
    )

    uploaded_files = st.file_uploader(
        "Fichiers OHLCV (CSV, un par actif)", type=["csv"], accept_multiple_files=True
    )

    if not uploaded_files:
        return

    base_tf = st.selectbox("Timeframe de base", ["15min", "30min", "1H", "4H", "1D"], index=2)

    results = []
    for f in uploaded_files:
        symbol = f.name.rsplit(".", 1)[0]
        tmp_path = f"/tmp/scan_{f.name}"
        with open(tmp_path, "wb") as out:
            out.write(f.getbuffer())

        try:
            df, warnings = data_engine.get_data(symbol, base_tf, source_path=tmp_path, use_cache=False)
        except DataValidationError as e:
            st.warning(f"{symbol} : {e}")
            continue

        htf_map = {"15min": "4H", "30min": "4H", "1H": "1D", "4H": "1D", "1D": "1W"}
        ltf_map = {"4H": "1H", "1D": "4H", "1W": "1D"}
        htf = htf_map.get(base_tf, "1D")
        ltf = ltf_map.get(base_tf, base_tf)

        mtf_data = data_engine.build_multi_timeframe(df, base_tf, [htf, ltf])

        try:
            report = run_full_analysis(
                symbol=symbol, mtf_data=mtf_data, base_tf=base_tf, htf=htf, ltf=ltf,
                data_warnings=warnings,
            )
        except Exception as exc:  # noqa: BLE001 - on veut continuer le scan même si un actif échoue
            st.warning(f"{symbol} : analyse impossible ({exc})")
            continue

        results.append({
            "Actif": report.symbol,
            "Verdict": report.verdict,
            "Grade": report.grade,
            "Régime": report.regime,
            "Bullish": report.scores["bullish"],
            "Bearish": report.scores["bearish"],
            "Confiance": report.confidence,
        })

    if not results:
        st.info("Aucun résultat exploitable.")
        return

    verdict_filter = st.multiselect(
        "Filtrer par verdict", ["BULLISH", "BEARISH", "NEUTRAL", "NO TRADE"],
        default=["BULLISH", "BEARISH"],
    )
    grade_filter = st.multiselect(
        "Filtrer par grade", ["A+", "A", "B", "C", "NO TRADE"],
        default=["A+", "A", "B"],
    )

    filtered = [
        r for r in results
        if r["Verdict"] in verdict_filter and r["Grade"] in grade_filter
    ]

    st.dataframe(filtered or results, use_container_width=True)
