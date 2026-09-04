# RE-ZERO TRADING ANALYST

> « Je ne prédis pas le marché. J'analyse les scénarios, les probabilités,
> les risques et les confluences. »

IA d'analyse quantitative, technique et structurelle des marchés (Forex,
Crypto, Indices, Matières premières). Application Streamlit modulaire :
Dashboard, Analyst, Scanner, Backtest, Paper Trading, Settings.

## ⚠️ Limitation assumée — lis ceci avant tout

Ce code a été généré dans un environnement **sans accès réseau**. Il n'y a
donc :
- **aucune connexion API live** (pas de yfinance, pas de broker, pas de flux
  temps réel) branchée par défaut ;
- **aucune clé API** en dur nulle part (et il ne doit jamais y en avoir dans
  le code source — voir section Sécurité) ;
- **aucun envoi Telegram/email** tant que tu n'as pas renseigné tes propres
  identifiants dans la page Settings.

L'application fonctionne dès maintenant avec des **fichiers CSV OHLCV** que
tu uploades (colonnes attendues : `datetime, open, high, low, close,
volume` — volume optionnel). Pour la faire fonctionner en temps réel,
il te suffit d'implémenter une fonction de récupération de données et de
l'enregistrer :

```python
from app.core.data_engine import data_engine
import yfinance as yf

def fetch_live(symbol: str, timeframe: str):
    # à adapter selon ta source (yfinance, ccxt, broker...)
    return yf.download(symbol, interval="1h", period="60d")

data_engine.register_live_fetcher(fetch_live)
```

Ajoute cet appel au début de `app/main.py`, dans un environnement qui a
accès à internet.

## Installation

```bash
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app/main.py
```

## Tests

```bash
pytest app/tests -v
```

## Architecture

```
app/
  main.py                  # Point d'entrée Streamlit
  pages/                   # Une page = un mode d'utilisation
    dashboard.py           # Vue d'ensemble + analyse complète
    analyst.py             # Analyse approfondie d'un actif
    scanner.py              # Scan multi-actifs
    backtest.py             # Backtest walk-forward (anti look-ahead)
    paper_trading.py        # Simulation sans argent réel
    settings.py             # Capital, risque, notifications
  core/                    # Moteurs d'analyse (logique métier pure)
    data_engine.py          # Chargement / validation / multi-timeframe
    indicator_engine.py      # Trend, momentum, volatilité, volume
    market_structure.py      # Price action : swings, BOS/CHOCH, S/R
    smc_engine.py             # Liquidity, order blocks, FVG
    fibonacci_engine.py       # Retracement / extension
    pattern_engine.py         # Chandeliers + patterns graphiques
    divergence_engine.py      # Divergences régulières / cachées
    regime_engine.py          # Classification du régime de marché
    confluence_engine.py       # Moteur central de score
    risk_engine.py             # Position sizing, R:R
    scoring_engine.py          # Grade A+/A/B/C/NO TRADE
    analysis_engine.py         # Orchestrateur + rapport final
  models/
    ml_engine.py             # Estimation statistique (jamais une promesse)
  notifications/
    telegram.py / email.py / browser.py
  utils/
    cache.py / logger.py / validators.py
  tests/
    test_engines.py
```

## Règles de conception (non négociables, voir le prompt d'origine)

1. **Anti-hallucination** : aucune donnée, prix, volume ou actualité n'est
   inventé. Si une donnée manque, le système le dit explicitement
   (`DataValidationError` / message "Donnée indisponible").
2. **Signal détecté ≠ signal confirmé** : les order blocks et FVG portent
   un statut `detected` ou `confirmed` (après retest).
3. **Le score de confluence n'est pas une probabilité de gain** : c'est une
   mesure de densité/cohérence des facteurs, jamais présentée comme telle
   à l'utilisateur.
4. **NO TRADE est un résultat valide et volontairement fréquent** quand la
   confluence est insuffisante ou le Risk/Reward mauvais.
5. **Pas d'exécution réelle** : Paper Trading uniquement, aucune clé de
   courtier n'est demandée.
6. **Anti-repaint / anti look-ahead** : le backtest recalcule les
   indicateurs bougie par bougie sans utiliser de données futures.

## Ce qu'il te reste à faire (hors scope de cet environnement)

- Brancher une vraie source de données (API broker, yfinance, ccxt) via
  `data_engine.register_live_fetcher`.
- Configurer Telegram/Email dans Settings si tu veux des notifications.
- Déployer (Streamlit Community Cloud, VPS, Docker...) dans un environnement
  avec accès réseau.
- Étoffer `ml_engine.py` si tu veux un vrai modèle statistique une fois que
  tu as un historique de trades réel à lui donner.
