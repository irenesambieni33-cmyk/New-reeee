"""
RE-ZERO - Notifications Telegram
Nécessite un bot Telegram (BotFather) + un chat_id. Non actif par
défaut : aucune clé n'est demandée tant que l'utilisateur ne configure
pas ces deux valeurs dans Settings.
"""
from __future__ import annotations

import requests

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, message: str) -> bool:
        if not self.is_configured:
            logger.warning("Telegram non configuré : message non envoyé.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            response = requests.post(
                url, data={"chat_id": self.chat_id, "text": message}, timeout=10
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            logger.error(f"Échec d'envoi Telegram : {exc}")
            return False
