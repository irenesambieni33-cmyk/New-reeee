"""
RE-ZERO - Notifications Email
Envoi via SMTP standard. Nécessite des identifiants configurés par
l'utilisateur (aucun identifiant en dur dans le code).
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmailNotifier:
    def __init__(self, smtp_host: str | None = None, smtp_port: int = 587,
                 username: str | None = None, password: str | None = None,
                 sender: str | None = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender or username

    @property
    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.username and self.password)

    def send(self, to_address: str, subject: str, body: str) -> bool:
        if not self.is_configured:
            logger.warning("Email non configuré : message non envoyé.")
            return False

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = to_address

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, [to_address], msg.as_string())
            return True
        except (smtplib.SMTPException, OSError) as exc:
            logger.error(f"Échec d'envoi email : {exc}")
            return False
