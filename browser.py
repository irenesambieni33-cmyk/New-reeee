"""
RE-ZERO - Notifications navigateur
Utilise les notifications natives via Streamlit (st.toast / st.balloons
ne sont pas des notifications système ; pour de vraies notifications
navigateur, un petit composant JS est injecté).

Règle (section 24) : aucune notification n'est envoyée pour un simple
signal isolé, uniquement pour des événements de confluence validés.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def notify_browser(title: str, message: str) -> None:
    """Affiche une notification navigateur native (permission requise)."""
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    components.html(
        f"""
        <script>
        if (Notification.permission === "granted") {{
            new Notification("{safe_title}", {{ body: "{safe_message}" }});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(function (permission) {{
                if (permission === "granted") {{
                    new Notification("{safe_title}", {{ body: "{safe_message}" }});
                }}
            }});
        }}
        </script>
        """,
        height=0,
    )


def notify_in_app(message: str, level: str = "info") -> None:
    """Notification simple dans l'interface Streamlit elle-même."""
    if level == "success":
        st.toast(message, icon="✅")
    elif level == "warning":
        st.toast(message, icon="⚠️")
    elif level == "error":
        st.toast(message, icon="🛑")
    else:
        st.toast(message, icon="ℹ️")
