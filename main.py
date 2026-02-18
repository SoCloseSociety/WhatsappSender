#!/usr/bin/env python3
"""
SoClose Community Bot — Entry Point
WhatsApp bot for the SoCloseSociety open-source community.

Usage:
    python main.py              # CLI mode (default)
    python main.py --telegram   # Telegram bot + webhook server
    python main.py --dashboard  # Streamlit web dashboard
    python main.py --webhook    # Webhook server only (no Telegram)
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import os
import threading

import config

# ── Logging ───────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── Dependency Check ──────────────────────────────────────────

def check_dependencies():
    """Verify all required packages are installed."""
    required = [
        ("dotenv", "python-dotenv"),
        ("aiosqlite", "aiosqlite"),
        ("requests", "requests"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
    ]
    missing = []
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"\n❌ Packages manquants: {', '.join(missing)}")
        print(f"   Installe-les avec: pip install -r requirements.txt\n")
        sys.exit(1)


# ── Modes ─────────────────────────────────────────────────────

async def run_cli_mode():
    """Interactive CLI for local testing."""
    from cli import run_cli
    await run_cli()


async def run_telegram_mode():
    """Telegram bot + FastAPI webhook server."""
    import database
    import github_api

    await database.init()
    await github_api.sync_projects()

    # Mark as initialized so webhook lifespan doesn't double-init
    import webhook
    webhook._initialized = True

    # Start webhook server in background thread
    import uvicorn

    server_config = uvicorn.Config(
        webhook.app,
        host=config.WEBHOOK_HOST,
        port=config.WEBHOOK_PORT,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    webhook_thread = threading.Thread(target=server.run, daemon=True)
    webhook_thread.start()

    logger.info(f"Webhook server started on {config.WEBHOOK_HOST}:{config.WEBHOOK_PORT}")

    # Start Telegram bot
    from telegram_bot import build_telegram_app

    telegram_app = build_telegram_app()
    logger.info("Telegram bot starting...")

    async with telegram_app:
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        logger.info(f"{config.BOT_NAME} is running! (Telegram + Webhook)")
        logger.info(f"Health check: http://localhost:{config.WEBHOOK_PORT}/health")

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await telegram_app.updater.stop()
            await telegram_app.stop()


async def run_webhook_mode():
    """FastAPI webhook server only (no Telegram)."""
    import uvicorn
    from webhook import app as fastapi_app

    logger.info(f"Starting webhook server on {config.WEBHOOK_HOST}:{config.WEBHOOK_PORT}")
    logger.info(f"API docs: http://localhost:{config.WEBHOOK_PORT}/docs")

    server_config = uvicorn.Config(
        fastapi_app,
        host=config.WEBHOOK_HOST,
        port=config.WEBHOOK_PORT,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()


def run_dashboard_mode():
    """Streamlit web dashboard."""
    try:
        port = int(os.getenv("DASHBOARD_PORT", "8501"))
    except ValueError:
        port = 8501
    logger.info(f"Starting Streamlit dashboard on port {port}")
    subprocess.run(
        ["streamlit", "run", "dashboard.py", "--server.port", str(port), "--server.headless", "true"],
        check=True,
    )


# ── Main ──────────────────────────────────────────────────────

def main():
    check_dependencies()

    parser = argparse.ArgumentParser(
        description=f"{config.BOT_NAME} v{config.BOT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  (default)     CLI interactif pour tests locaux
  --telegram    Bot Telegram + serveur webhook
  --webhook     Serveur webhook seul (auto-reply WhatsApp)
  --dashboard   Dashboard web Streamlit

Exemples:
  python main.py                    # CLI
  python main.py --telegram         # Production
  python main.py --dashboard        # Web UI
  python main.py --webhook          # API seule
        """,
    )
    parser.add_argument("--telegram", action="store_true", help="Lancer le bot Telegram + webhook")
    parser.add_argument("--webhook", action="store_true", help="Lancer le serveur webhook seul")
    parser.add_argument("--dashboard", action="store_true", help="Lancer le dashboard Streamlit")
    args = parser.parse_args()

    # Show config warnings
    warnings = config.validate()
    if warnings:
        for w in warnings:
            logger.warning(w)

    print(f"\n🤖 {config.BOT_NAME} v{config.BOT_VERSION}")
    print(f"   Provider: {config.WA_PROVIDER.upper()}")
    print(f"   GitHub: {config.COMMUNITY_URL}\n")

    if args.dashboard:
        run_dashboard_mode()
    elif args.telegram:
        if not config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN requis pour le mode Telegram")
            sys.exit(1)
        asyncio.run(run_telegram_mode())
    elif args.webhook:
        asyncio.run(run_webhook_mode())
    else:
        asyncio.run(run_cli_mode())


if __name__ == "__main__":
    main()
