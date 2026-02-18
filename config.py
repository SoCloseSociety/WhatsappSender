"""
SoClose Community Bot — Configuration
Loads settings from environment variables (.env file).
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Telegram Bot ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_IDS = [
    int(uid.strip())
    for uid in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    if uid.strip().lstrip("-").isdigit()
]

# ── WhatsApp Provider ─────────────────────────────────────────
WA_PROVIDER = os.getenv("WA_PROVIDER", "twilio").lower()  # twilio | meta

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")  # whatsapp:+14155238886

# Meta Cloud API
WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
WA_ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN", "")
WA_API_VERSION = os.getenv("WA_API_VERSION", "v21.0")
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "")

# ── Webhook Server ────────────────────────────────────────────
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
try:
    WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
except ValueError:
    WEBHOOK_PORT = 8000

# ── Database ──────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "community_bot.db")

# ── Rate Limiting ─────────────────────────────────────────────
try:
    WA_MESSAGES_PER_SECOND = int(os.getenv("WA_MESSAGES_PER_SECOND", "50"))
except ValueError:
    WA_MESSAGES_PER_SECOND = 50

# ── GitHub ────────────────────────────────────────────────────
GITHUB_ORG = os.getenv("GITHUB_ORG", "SoCloseSociety")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # optional, for higher rate limits

# ── Bot Identity ──────────────────────────────────────────────
BOT_NAME = "SoClose Community Bot"
BOT_VERSION = "2.0.0"
COMMUNITY_URL = "https://github.com/SoCloseSociety"
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://soclose.co")
BOT_EMAIL = "contact@soclose.co"

# ── Dashboard ─────────────────────────────────────────────────
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")


def validate() -> list[str]:
    """Return a list of configuration warnings."""
    warnings = []

    if not TELEGRAM_BOT_TOKEN:
        warnings.append("TELEGRAM_BOT_TOKEN not set — Telegram mode disabled")
    if not TELEGRAM_ADMIN_IDS:
        warnings.append("TELEGRAM_ADMIN_IDS not set — no admin access")
    if not WA_VERIFY_TOKEN:
        warnings.append("WA_VERIFY_TOKEN not set — webhook verification disabled")
    if not DASHBOARD_PASSWORD:
        warnings.append("DASHBOARD_PASSWORD not set — dashboard has no auth")

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

    return warnings
