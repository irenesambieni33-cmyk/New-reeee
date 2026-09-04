"""
RE-ZERO - Page Settings
Configuration du capital, du risque par trade, et des notifications
(Telegram/email). Aucune clé n'est stockée en dur dans le code
(section 31 - SÉCURITÉ).
"""
from __future__ import annotations

import streamlit as st


def render():
    st.header("⚙️ RE-ZERO — Settings")

    st.subheader("Capital & Risque")
    st.session_state["capital"] = st.number_input(
        "Capital (référence pour le sizing)",
        value=st.session_state.get("capital", 1000.0), min_value=1.0,
    )
    st.session_state["risk_percent"] = st.selectbox(
        "Risque par trade (%)", [0.25, 0.5, 1.0, 2.0],
        index=[0.25, 0.5, 1.0, 2.0].index(st.session_state.get("risk_percent", 1.0)),
    )

    st.divider()
    st.subheader("Notifications Telegram")
    st.caption("Crée un bot via @BotFather sur Telegram pour obtenir un token.")
    st.session_state["telegram_bot_token"] = st.text_input(
        "Bot Token", value=st.session_state.get("telegram_bot_token", ""), type="password",
    )
    st.session_state["telegram_chat_id"] = st.text_input(
        "Chat ID", value=st.session_state.get("telegram_chat_id", ""),
    )

    st.divider()
    st.subheader("Notifications Email (SMTP)")
    st.session_state["smtp_host"] = st.text_input("Hôte SMTP", value=st.session_state.get("smtp_host", ""))
    st.session_state["smtp_user"] = st.text_input("Utilisateur", value=st.session_state.get("smtp_user", ""))
    st.session_state["smtp_password"] = st.text_input(
        "Mot de passe", value=st.session_state.get("smtp_password", ""), type="password",
    )

    st.divider()
    st.subheader("Source de données live")
    st.info(
        "Cet environnement de génération n'a pas d'accès réseau. Pour brancher une "
        "source live (yfinance, broker, ccxt...), implémente une fonction "
        "`fetch(symbol, timeframe) -> DataFrame` et enregistre-la via "
        "`data_engine.register_live_fetcher(fetch)` dans `main.py`, une fois déployé "
        "dans un environnement avec accès internet."
    )

    if st.button("Sauvegarder"):
        st.success("Paramètres sauvegardés pour cette session.")
