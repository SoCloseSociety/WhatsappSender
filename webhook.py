"""
WhatsApp Bulk Sender — Webhook Server
FastAPI endpoints for WhatsApp delivery status callbacks.
Handles both Meta Cloud API and Twilio status updates.
"""

import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

import config
import database

logger = logging.getLogger(__name__)

# Valid delivery statuses (anything else is rejected)
_VALID_STATUSES = {"queued", "sent", "delivered", "read", "failed"}

# -- Lifespan -------------------------------------------------

_initialized = False


def mark_initialized():
    """Called by main.py to prevent double-init in telegram mode."""
    global _initialized
    _initialized = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _initialized
    if not _initialized:
        await database.init()
        _initialized = True
        logger.info(f"{config.BOT_NAME} v{config.BOT_VERSION} webhook server started")
    yield


app = FastAPI(title=config.BOT_NAME, version=config.BOT_VERSION, lifespan=lifespan)


# -- Meta Cloud API Webhook ------------------------------------

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
    """Receive Meta Cloud API delivery status updates."""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        return {"status": "error"}

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Status updates (delivery receipts)
            for status_update in value.get("statuses", []):
                sid = status_update.get("id", "")
                new_status = status_update.get("status", "")
                if sid and new_status in _VALID_STATUSES:
                    await database.update_message_status(sid, new_status)
                    logger.debug(f"Status update: {sid} -> {new_status}")
                elif new_status:
                    logger.warning(f"Unknown status '{new_status}' for {sid}, ignoring")

    return {"status": "ok"}


# -- Twilio Status Callback ------------------------------------

@app.post("/twilio-status")
async def twilio_status(request: Request):
    """Handle Twilio delivery status callbacks."""
    form = await request.form()
    sid = str(form.get("MessageSid", ""))
    status = str(form.get("MessageStatus", ""))

    # Normalize Twilio status to match our naming
    status_map = {
        "queued": "queued",
        "sent": "sent",
        "delivered": "delivered",
        "read": "read",
        "undelivered": "failed",
        "failed": "failed",
    }
    normalized = status_map.get(status)

    if sid and normalized:
        await database.update_message_status(sid, normalized)

    return {"status": "ok"}


# -- Health Check ----------------------------------------------

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
    return {
        "name": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "endpoints": {
            "health": "/health",
            "webhook_meta": "/webhook",
            "twilio_status": "/twilio-status",
            "docs": "/docs",
        },
    }
