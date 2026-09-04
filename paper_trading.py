"""
RE-ZERO - Page Paper Trading
Simule des opérations sans argent réel, à partir des rapports générés
par l'Analysis Engine. Aucune connexion broker, aucune exécution réelle
(section 31 - SÉCURITÉ).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core.risk_engine import compute_position_size


def _init_state():
    if "paper_positions" not in st.session_state:
        st.session_state["paper_positions"] = []
    if "paper_capital" not in st.session_state:
        st.session_state["paper_capital"] = 1000.0


def render():
    st.header("📝 RE-ZERO — Paper Trading")
    st.caption("Simulation uniquement. Aucun ordre réel n'est envoyé à un broker.")

    _init_state()

    report = st.session_state.get("last_report")

    with st.form("new_paper_trade"):
        st.subheader("Nouvelle position simulée")
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("Actif", value=report.symbol if report else "EUR/USD")
            direction = st.selectbox("Sens", ["long", "short"])
            entry = st.number_input("Prix d'entrée", value=float(report.current_price) if report else 1.0)
        with col2:
            stop_loss = st.number_input("Stop loss", value=0.0)
            take_profit = st.number_input("Take profit", value=0.0)
            risk_percent = st.selectbox("Risque (%)", [0.25, 0.5, 1.0, 2.0], index=2)

        submitted = st.form_submit_button("Ouvrir la position simulée")

        if submitted:
            try:
                sizing = compute_position_size(
                    capital=st.session_state["paper_capital"],
                    risk_percent=risk_percent,
                    entry=entry,
                    stop_loss=stop_loss,
                    take_profits=[take_profit],
                )
                st.session_state["paper_positions"].append({
                    "symbol": symbol, "direction": direction, "entry": entry,
                    "stop_loss": stop_loss, "take_profit": take_profit,
                    "size": sizing.position_size_units, "status": "open",
                })
                st.success("Position simulée ouverte.")
            except ValueError as e:
                st.error(str(e))

    st.subheader("Positions simulées")
    positions = st.session_state["paper_positions"]
    if not positions:
        st.write("Aucune position ouverte.")
        return

    df_positions = pd.DataFrame(positions)
    st.dataframe(df_positions, use_container_width=True)

    idx_to_close = st.number_input(
        "Index de la position à clôturer", min_value=0,
        max_value=max(len(positions) - 1, 0), step=1,
    )
    exit_price = st.number_input("Prix de clôture", value=0.0)

    if st.button("Clôturer cette position") and positions:
        pos = positions[idx_to_close]
        pnl = (exit_price - pos["entry"]) * pos["size"]
        if pos["direction"] == "short":
            pnl = -pnl
        pos["status"] = "closed"
        pos["exit_price"] = exit_price
        pos["pnl"] = round(pnl, 2)
        st.session_state["paper_capital"] += pnl
        st.success(f"Position clôturée. PnL simulé : {pnl:.2f}")

    st.metric("Capital simulé courant", round(st.session_state["paper_capital"], 2))
