"""
RE-ZERO TRADING ANALYST
Point d'entrée de l'application Streamlit.

Lancement :
    streamlit run app/main.py

Identité (section 33) :
"Je ne prédis pas le marché. J'analyse les scénarios, les probabilités,
les risques et les confluences."
"""
from __future__ import annotations

import streamlit as st

from app.core.data_engine import data_engine
from app.pages import analyst, backtest, dashboard, paper_trading, scanner, settings

# Connecteur de données live gratuit (Yahoo Finance via yfinance).
# Ne fonctionne que si l'app tourne dans un environnement avec accès
# internet (ex: Streamlit Community Cloud) - sans ça, l'app reste
# utilisable en uploadant des CSV.
try:
    from app.core.live_fetcher_yfinance import fetch_live
    data_engine.register_live_fetcher(fetch_live)
except ImportError:
    pass

st.set_page_config(
    page_title="RE-ZERO TRADING ANALYST",
    page_icon="📈",
    layout="wide",
)

PAGES = {
    "Dashboard": dashboard,
    "Analyst": analyst,
    "Scanner": scanner,
    "Backtest": backtest,
    "Paper Trading": paper_trading,
    "Settings": settings,
}


def main():
    st.sidebar.title("RE-ZERO TRADING ANALYST")
    st.sidebar.caption("IA d'analyse quantitative, technique et structurelle des marchés.")
    st.sidebar.caption("_Je ne prédis pas le marché. J'analyse les scénarios, les probabilités, "
                        "les risques et les confluences._")

    choice = st.sidebar.radio("Navigation", list(PAGES.keys()))

    st.sidebar.divider()
    st.sidebar.warning(
        "⚠️ Pas d'accès réseau par défaut : brancher une source de données live "
        "nécessite ta propre clé API (voir page Settings)."
    )

    PAGES[choice].render()


if __name__ == "__main__":
    main()
