"""
WhatsApp Bulk Sender — WhatsApp Client
Multi-provider async WhatsApp messaging (Twilio / Meta Cloud API).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from typing import Callable

import requests

import config

logger = logging.getLogger(__name__)


def _render_message(template: str, placeholders: dict) -> str:
    """Single-pass placeholder substitution (prevents second-pass injection)."""
    safe = defaultdict(str, placeholders)
    try:
        return template.format_map(safe)
    except (KeyError, ValueError):
        # Fallback for templates with literal braces
        result = template
        for key, val in placeholders.items():
            result = result.replace(f"{{{key}}}", val)
        return result


class WhatsAppClient:
    """Unified WhatsApp client supporting Twilio and Meta Cloud API."""

    # Class-level rate state shared across all instances
    _shared_last_send = 0.0

    def __init__(self):
        self.provider = config.WA_PROVIDER
        self._rate_interval = 1.0 / max(1, config.WA_MESSAGES_PER_SECOND)

    async def _rate_limit(self):
        """Enforce rate limiting between sends (shared across all instances)."""
        elapsed = time.monotonic() - WhatsAppClient._shared_last_send
        if elapsed < self._rate_interval:
            await asyncio.sleep(self._rate_interval - elapsed)
        WhatsAppClient._shared_last_send = time.monotonic()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone for Meta API (digits only)."""
        return re.sub(r"[^0-9]", "", phone)

    async def send_message(self, to: str, body: str) -> dict:
        """Send a single WhatsApp message. Returns {"sid": ..., "status": ...}."""
        await self._rate_limit()

        if self.provider == "twilio":
            return await self._send_twilio(to, body)
        elif self.provider == "meta":
            return await self._send_meta(to, body)
        else:
            return {"sid": "", "status": "failed", "error": f"Unknown provider: {self.provider}"}

    async def _send_twilio(self, to: str, body: str) -> dict:
        """Send via Twilio WhatsApp API."""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"
        to_number = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        data = {
            "From": config.TWILIO_WHATSAPP_FROM,
            "To": to_number,
            "Body": body,
        }
        auth = (config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

        try:
            resp = await asyncio.to_thread(
                requests.post, url, data=data, auth=auth, timeout=15
            )
            result = resp.json()
            if resp.status_code in (200, 201):
                return {"sid": result.get("sid", ""), "status": "sent"}
            else:
                error_msg = result.get("message", resp.text[:200])
                logger.error(f"Twilio error for {to}: {error_msg}")
                return {"sid": "", "status": "failed", "error": error_msg}
        except Exception as e:
            logger.error(f"Twilio exception for {to}: {e}")
            return {"sid": "", "status": "failed", "error": str(e)}

    async def _send_meta(self, to: str, body: str) -> dict:
        """Send via Meta Cloud API."""
        phone = self.normalize_phone(to)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body},
        }

        try:
            resp = await asyncio.to_thread(self._meta_post, payload)
            if resp.status_code in (200, 201):
                result = resp.json()
                msg_id = result.get("messages", [{}])[0].get("id", "")
                return {"sid": msg_id, "status": "sent"}
            else:
                result = resp.json()
                error = result.get("error", {}).get("message", resp.text[:200])
                logger.error(f"Meta API error for {to}: {error}")
                return {"sid": "", "status": "failed", "error": error}
        except Exception as e:
            logger.error(f"Meta API exception for {to}: {e}")
            return {"sid": "", "status": "failed", "error": str(e)}

    @staticmethod
    def _meta_post(payload: dict) -> requests.Response:
        """Synchronous POST to Meta Graph API (called via asyncio.to_thread)."""
        headers = {
            "Authorization": f"Bearer {config.WA_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        return requests.post(config.WA_BASE_URL, json=payload, headers=headers, timeout=15)

    async def send_bulk(
        self,
        recipients: list[dict],
        message_template: str,
        campaign_id: int | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> dict:
        """
        Send messages to multiple recipients.

        recipients: list of {"phone": "+33...", "first_name": "...", "last_name": "...", "id": ...}
        message_template: message with placeholders {first_name}, {last_name}, {phone}
        Returns: {"sent": N, "failed": N, "results": [...]}
        """
        import database

        results = {"sent": 0, "failed": 0, "results": []}

        for i, recipient in enumerate(recipients):
            phone = recipient.get("phone") or ""
            first_name = recipient.get("first_name") or "Contact"
            last_name = recipient.get("last_name") or ""
            contact_id = recipient.get("id")

            body = _render_message(message_template, {
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "name": f"{first_name} {last_name}".strip(),
            })

            result = await self.send_message(phone, body)

            # Log to database
            await database.log_message(
                phone=phone,
                content=body[:500],
                status=result["status"],
                campaign_id=campaign_id,
                contact_id=contact_id,
                wa_message_id=result.get("sid", ""),
                error_message=result.get("error", ""),
            )

            if result["status"] == "sent":
                results["sent"] += 1
            else:
                results["failed"] += 1
            results["results"].append({"phone": phone, **result})

            if on_progress:
                on_progress(i + 1, len(recipients), result["status"])

        return results
