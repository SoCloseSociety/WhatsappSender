"""
WhatsApp Bulk Sender — Configuration
Loads settings from environment variables (.env file).
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


# -- Telegram Bot (admin) ------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_IDS = [
    int(uid.strip())
    for uid in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    if uid.strip().lstrip("-").isdigit()
]

# -- WhatsApp Provider ----------------------------------------
WA_PROVIDER = os.getenv("WA_PROVIDER", "twilio").lower()  # twilio | meta

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

# Meta Cloud API
WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
WA_ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN", "")
WA_API_VERSION = os.getenv("WA_API_VERSION", "v21.0")
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "")
WA_BASE_URL = f"https://graph.facebook.com/{WA_API_VERSION}/{WA_PHONE_NUMBER_ID}/messages"

# -- Webhook Server -------------------------------------------
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
try:
    WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
except ValueError:
    WEBHOOK_PORT = 8000

# -- Database -------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "whatsapp_sender.db")

# -- Rate Limiting --------------------------------------------
try:
    WA_MESSAGES_PER_SECOND = int(os.getenv("WA_MESSAGES_PER_SECOND", "50"))
except ValueError:
    WA_MESSAGES_PER_SECOND = 50

# -- Bot Identity ---------------------------------------------
BOT_NAME = "WhatsApp Bulk Sender"
BOT_VERSION = "1.0.0"
COMMUNITY_URL = "https://github.com/SoCloseSociety"
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://soclose.co")

# -- Dashboard ------------------------------------------------
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")


def validate() -> list[str]:
    """Return a list of configuration warnings."""
    warnings = []

    if WA_PROVIDER == "twilio":
        if not TWILIO_ACCOUNT_SID:
            warnings.append("TWILIO_ACCOUNT_SID not set")
        if not TWILIO_AUTH_TOKEN:
            warnings.append("TWILIO_AUTH_TOKEN not set")
        if not TWILIO_WHATSAPP_FROM:
            warnings.append("TWILIO_WHATSAPP_FROM not set")
    elif WA_PROVIDER == "meta":
        if not WA_PHONE_NUMBER_ID:
            warnings.append("WA_PHONE_NUMBER_ID not set")
        if not WA_ACCESS_TOKEN:
            warnings.append("WA_ACCESS_TOKEN not set")
    else:
        warnings.append(f"Unknown WA_PROVIDER: {WA_PROVIDER} (use 'twilio' or 'meta')")

    if WA_MESSAGES_PER_SECOND <= 0:
        warnings.append(f"WA_MESSAGES_PER_SECOND is {WA_MESSAGES_PER_SECOND}, should be > 0 (defaulting to 1)")

    return warnings
