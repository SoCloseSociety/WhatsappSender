# CLAUDE.md -- WhatsappSender

## 1. Project Identity

**Name:** WhatsappSender -- WhatsApp Bulk Message Platform
**Role:** Multi-interface WhatsApp bulk messaging platform with Twilio/Meta Cloud API support, campaign management, delivery tracking, and 3 control interfaces (CLI, Streamlit dashboard, Telegram bot).
**Author:** SoClose Society (https://soclose.co)
**License:** MIT

### Stack

- **Language:** Python 3.10+
- **WhatsApp API:** Twilio or Meta Cloud API (configurable)
- **Bot:** python-telegram-bot 22.6 (remote control)
- **Web UI:** Streamlit (dashboard)
- **Webhooks:** FastAPI + Uvicorn (delivery callbacks)
- **Database:** aiosqlite (async SQLite with WAL)
- **Data:** pandas, phonenumbers
- **Architecture:** Multi-module (9 files, ~2,607 LOC)

### Project Structure

```
main.py (205 LOC)          Entry point with mode switching
cli.py (470 LOC)           Interactive CLI menu
config.py (85 LOC)         Config management + validation
whatsapp.py (181 LOC)      WhatsApp client (Twilio/Meta)
database.py (445 LOC)      SQLite async database layer
csv_handler.py (162 LOC)   CSV parsing + phone normalization
webhook.py (136 LOC)       FastAPI delivery webhook
dashboard.py (404 LOC)     Streamlit web dashboard
telegram_bot.py (519 LOC)  Telegram bot for remote control
```

### External Services

| Service      | Notes                                     |
| ------------ | ----------------------------------------- |
| Twilio       | WhatsApp Business API (paid)              |
| Meta Cloud   | WhatsApp Cloud API (free tier available)  |
| Telegram Bot | Remote control interface                  |
| FastAPI      | Webhook for delivery status callbacks     |

### Critical Files -- Do Not Touch Without a Plan

- `whatsapp.py` -- API provider abstraction (Twilio/Meta)
- `database.py` -- 445 LOC, all DB operations
- `config.py` -- Provider switching logic

## 2-5. Standard Workflow

- Enter plan mode for non-trivial tasks
- Test with dry-run mode first
- Verify phone number normalization works (E.164 format)
- Test webhook delivery tracking
- Track tasks in `tasks/todo.md`, lessons in `tasks/lessons.md`

## 6. Project-Specific Rules

### Dev Commands
```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in provider credentials

python main.py                  # CLI mode (default)
python main.py --mode dashboard # Streamlit dashboard
python main.py --mode bot       # Telegram bot control
python main.py --mode webhook   # Delivery webhook server
```

### Environment Variables
- WA_PROVIDER=twilio (or meta)
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
- WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN (Meta)
- TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS
- WEBHOOK_HOST=0.0.0.0, WEBHOOK_PORT=8000
- DB_PATH=whatsapp_sender.db
- WA_MESSAGES_PER_SECOND=50
- DASHBOARD_PASSWORD, DASHBOARD_PORT=8501

### Known Fragile Areas
- Provider abstraction -- Twilio and Meta have different error formats
- Phone normalization -- international formats can be tricky
- Webhook server -- must be publicly accessible for delivery callbacks
- Rate limiting -- WA_MESSAGES_PER_SECOND default of 50 may be too aggressive

## Neo Connector (auto)
Ce projet expose `NEO_CONNECTOR.md` : le manifeste machine-lisible de TOUS ses
endpoints/auth/env, consommé par NeoBot pour se câbler automatiquement.
- RÈGLE : à chaque ajout/suppression/modif d'un endpoint, d'une auth ou d'une env var,
  régénère le manifeste via `/neo-connector` (ou le prompt dans .claude/skills/neo-connector).
- Ne jamais éditer NEO_CONNECTOR.md à la main : il est généré.
- Le hook pre-commit (.git/hooks/pre-commit) avertit si des routes ont changé sans MAJ du manifeste.
- NOTE projet : la surface HTTP (webhook.py) est faite de callbacks ENTRANTS (Meta/Twilio) +
  /health ; il n'y a PAS d'API d'action sortante. Ne pas câbler ce repo comme des outils HTTP Neo.

## 7. Core Principles

- Simplicity First, No Laziness, Minimal Impact
- Never use em dashes (use -- instead)
- Ollama-first for any local LLM calls (RTX 4070 available)
- Always use dry-run mode for testing before live sends
