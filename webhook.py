"""
SoClose Community Bot — Webhook Server
FastAPI endpoints for WhatsApp message reception and delivery status updates.
Handles both Meta Cloud API and Twilio webhooks + auto-reply logic.
"""

import hmac
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

import config
import database
import github_api
from whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)

# ── Rate Limiting ─────────────────────────────────────────────
_inbound_rate: dict[str, list[float]] = defaultdict(list)
_MAX_MESSAGES_PER_MINUTE = 10


# ── Lifespan ──────────────────────────────────────────────────

_initialized = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _initialized
    if not _initialized:
        await database.init()
        await github_api.sync_projects()
        _initialized = True
        logger.info(f"{config.BOT_NAME} v{config.BOT_VERSION} webhook server started")
    yield


app = FastAPI(title=config.BOT_NAME, version=config.BOT_VERSION, lifespan=lifespan)
wa_client = WhatsAppClient()


# ── Auto-Reply Router ─────────────────────────────────────────

async def handle_incoming_message(phone: str, text: str, name: str = ""):
    """Process an incoming WhatsApp message and auto-reply."""
    # Per-user rate limiting
    now = time.time()
    _inbound_rate[phone] = [t for t in _inbound_rate[phone] if now - t < 60]
    if len(_inbound_rate[phone]) >= _MAX_MESSAGES_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for {phone}")
        return
    _inbound_rate[phone].append(now)

    text_lower = text.strip().lower()

    # Register / update user
    await database.upsert_user(phone, name or "")
    await database.log_message(phone=phone, content=text[:500], direction="inbound")

    # ── Command Routing ───────────────────────────────────────
    if text_lower in ("menu", "start", "bonjour", "salut", "hi", "hello"):
        await wa_client.send_interactive_menu(phone)
        return

    if text_lower in ("aide", "help", "?"):
        tpl = await database.get_template("help")
        if tpl:
            await wa_client.send_message(phone, tpl["body"])
        return

    if text_lower == "stop":
        await database.set_user_subscribed(phone, False)
        await wa_client.send_message(
            phone, "Tu as ete desabonne. Tape *start* pour te reabonner."
        )
        return

    if text_lower in ("projets", "projects", "repos", "liste", "list"):
        projects = await database.get_all_projects()
        if not projects:
            await github_api.sync_projects()
            projects = await database.get_all_projects()
        project_list = github_api.format_project_list(projects)
        tpl = await database.get_template("project_list")
        if tpl:
            msg = tpl["body"].replace("{project_list}", project_list)
        else:
            msg = project_list
        await wa_client.send_message(phone, msg)
        return

    if text_lower in ("bots", "bot", "automatisation"):
        projects = await database.get_all_projects()
        bots = [p for p in projects if p.get("category") in ("bot", "automation")]
        msg = github_api.format_project_list(bots) if bots else "Aucun bot trouve."
        await wa_client.send_message(phone, msg)
        return

    if text_lower in ("scrapers", "scraper", "scraping"):
        projects = await database.get_all_projects()
        scrapers = [p for p in projects if p.get("category") == "scraper"]
        msg = github_api.format_project_list(scrapers) if scrapers else "Aucun scraper trouve."
        await wa_client.send_message(phone, msg)
        return

    if text_lower in ("site", "website", "web"):
        await wa_client.send_message(
            phone,
            f"🌐 *SoClose Society*\n\n"
            f"Site: {config.WEBSITE_URL}\n"
            f"GitHub: {config.COMMUNITY_URL}\n"
            f"Contact: {config.BOT_EMAIL}\n\n"
            f"Tape *menu* pour revenir au menu.",
        )
        return

    # ── Number Selection (project by index) ───────────────────
    if text_lower.isdigit():
        idx = int(text_lower) - 1
        projects = await database.get_all_projects()
        if 0 <= idx < len(projects):
            detail = github_api.format_project_detail(projects[idx])
            await wa_client.send_message(phone, detail)
        else:
            await wa_client.send_message(phone, "Numero invalide. Tape *projets* pour la liste.")
        return

    # ── Search ────────────────────────────────────────────────
    results = await database.search_projects(text_lower)
    if results:
        if len(results) == 1:
            detail = github_api.format_project_detail(results[0])
            await wa_client.send_message(phone, detail)
        else:
            msg = f"🔍 Resultats pour *{text}*:\n\n{github_api.format_project_list(results)}"
            await wa_client.send_message(phone, msg)
        return

    # ── Fallback ──────────────────────────────────────────────
    await wa_client.send_message(
        phone,
        "Je n'ai pas compris. Tape *menu* pour voir les options ou *aide* pour l'aide.",
    )


# ── Meta Cloud API Webhook ────────────────────────────────────

@app.get("/webhook")
async def meta_verify(request: Request):
    """Meta webhook verification (challenge-response)."""
    params = request.query_params
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and config.WA_VERIFY_TOKEN and hmac.compare_digest(token, config.WA_VERIFY_TOKEN):
        logger.info("Meta webhook verified")
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def meta_webhook(request: Request):
    """Receive Meta Cloud API events (messages + status updates)."""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        return {"status": "error"}

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Incoming messages
            for msg in value.get("messages", []):
                phone = msg.get("from", "")
                if phone and not phone.startswith("+"):
                    phone = f"+{phone}"

                # Extract sender name from contacts
                contact_name = ""
                for contact in value.get("contacts", []):
                    profile = contact.get("profile", {})
                    contact_name = profile.get("name", "")

                text = ""
                if msg.get("type") == "text":
                    text = msg.get("text", {}).get("body", "")
                elif msg.get("type") == "interactive":
                    interactive = msg.get("interactive", {})
                    if interactive.get("type") == "list_reply":
                        text = interactive.get("list_reply", {}).get("id", "")
                    elif interactive.get("type") == "button_reply":
                        text = interactive.get("button_reply", {}).get("id", "")

                if text:
                    await handle_incoming_message(phone, text, contact_name)

            # Status updates
            for status_update in value.get("statuses", []):
                sid = status_update.get("id", "")
                new_status = status_update.get("status", "")
                if sid and new_status:
                    await database.update_message_status(sid, new_status)

    return {"status": "ok"}


# ── Twilio Webhook ────────────────────────────────────────────

@app.post("/twilio-webhook")
async def twilio_incoming(request: Request):
    """Handle incoming WhatsApp messages via Twilio."""
    form = await request.form()
    phone = str(form.get("From", "")).replace("whatsapp:", "")
    text = str(form.get("Body", ""))
    name = str(form.get("ProfileName", ""))

    if phone and text:
        await handle_incoming_message(phone, text, name)

    return Response(content="<Response></Response>", media_type="application/xml")


@app.post("/twilio-status")
async def twilio_status(request: Request):
    """Handle Twilio delivery status callbacks."""
    form = await request.form()
    sid = str(form.get("MessageSid", ""))
    status = str(form.get("MessageStatus", ""))

    if sid and status:
        await database.update_message_status(sid, status)

    return {"status": "ok"}


# ── Health Check ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "provider": config.WA_PROVIDER,
    }


@app.get("/")
async def root():
    """Landing page / API info."""
    return {
        "name": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "github": config.COMMUNITY_URL,
        "website": config.WEBSITE_URL,
        "endpoints": {
            "health": "/health",
            "webhook_meta": "/webhook",
            "webhook_twilio": "/twilio-webhook",
            "docs": "/docs",
        },
    }
