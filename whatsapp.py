"""
SoClose Community Bot — WhatsApp Client
Multi-provider async WhatsApp messaging (Twilio / Meta Cloud API).
"""

import asyncio
import logging
import re
from typing import Callable

import requests

import config

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Unified WhatsApp client supporting Twilio and Meta Cloud API."""

    def __init__(self):
        self.provider = config.WA_PROVIDER
        self._rate_limit = config.WA_MESSAGES_PER_SECOND

    async def send_message(self, to: str, body: str) -> dict:
        """Send a single WhatsApp message. Returns {"sid": ..., "status": ...}."""
        if self.provider == "twilio":
            return await self._send_twilio(to, body)
        elif self.provider == "meta":
            return await self._send_meta(to, body)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _normalize_phone_meta(self, phone: str) -> str:
        """Normalize phone number for Meta API (digits only, no +)."""
        return re.sub(r"[^0-9]", "", phone)

    def _normalize_phone_storage(self, phone: str) -> str:
        """Normalize phone number for storage (E.164 with +)."""
        digits = re.sub(r"[^0-9]", "", phone)
        if digits and not phone.startswith("+"):
            return f"+{digits}"
        return f"+{digits}" if digits else phone

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
        url = f"https://graph.facebook.com/{config.WA_API_VERSION}/{config.WA_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {config.WA_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        phone = self._normalize_phone_meta(to)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body},
        }

        try:
            resp = await asyncio.to_thread(
                requests.post, url, json=payload, headers=headers, timeout=15
            )
            result = resp.json()
            if resp.status_code in (200, 201):
                msg_id = result.get("messages", [{}])[0].get("id", "")
                return {"sid": msg_id, "status": "sent"}
            else:
                error = result.get("error", {}).get("message", resp.text[:200])
                logger.error(f"Meta API error for {to}: {error}")
                return {"sid": "", "status": "failed", "error": error}
        except Exception as e:
            logger.error(f"Meta API exception for {to}: {e}")
            return {"sid": "", "status": "failed", "error": str(e)}

    async def send_bulk(
        self,
        recipients: list[dict],
        message_template: str,
        broadcast_id: int | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> dict:
        """
        Send messages to multiple recipients.
        recipients: list of {"phone": "+33...", "name": "...", ...}
        message_template: message body with optional {name} placeholder
        Returns: {"sent": N, "failed": N, "results": [...]}
        """
        import database

        results = {"sent": 0, "failed": 0, "results": []}

        for i, recipient in enumerate(recipients):
            phone = recipient.get("phone") or ""
            name = recipient.get("name") or ""
            body = message_template.replace("{name}", name).replace("{phone}", phone)

            result = await self.send_message(phone, body)

            # Log to database
            user = await database.get_user(phone)
            user_id = user["id"] if user else None
            await database.log_message(
                phone=phone,
                content=body[:500],
                direction="outbound",
                status=result["status"],
                broadcast_id=broadcast_id,
                user_id=user_id,
                provider_sid=result.get("sid", ""),
            )

            if result["status"] == "sent":
                results["sent"] += 1
            else:
                results["failed"] += 1
            results["results"].append({"phone": phone, **result})

            if on_progress:
                on_progress(i + 1, len(recipients), result["status"])

            # Rate limiting delay
            if self._rate_limit > 0:
                await asyncio.sleep(1.0 / self._rate_limit)

        return results

    async def send_interactive_menu(self, to: str) -> dict:
        """Send an interactive list message (Meta API only, falls back to text)."""
        if self.provider != "meta":
            menu_text = (
                "📋 *Menu — SoClose Community Bot*\n\n"
                "1️⃣ *projets* — Nos projets open-source\n"
                "2️⃣ *bots* — Bots d'automatisation\n"
                "3️⃣ *scrapers* — Outils de scraping\n"
                "4️⃣ *aide* — Obtenir de l'aide\n"
                "5️⃣ *site* — Notre site web\n\n"
                "Tape un mot-cle ou un numero pour naviguer."
            )
            return await self.send_message(to, menu_text)

        url = f"https://graph.facebook.com/{config.WA_API_VERSION}/{config.WA_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {config.WA_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        phone = self._normalize_phone_meta(to)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "SoClose Society"},
                "body": {"text": "Bienvenue ! Choisis une option :"},
                "action": {
                    "button": "Explorer",
                    "sections": [
                        {
                            "title": "Navigation",
                            "rows": [
                                {"id": "projects", "title": "📦 Tous les projets", "description": "Liste complete de nos repos"},
                                {"id": "bots", "title": "🤖 Bots", "description": "Bots d'automatisation"},
                                {"id": "scrapers", "title": "🔍 Scrapers", "description": "Outils de scraping"},
                                {"id": "help", "title": "ℹ️ Aide", "description": "Comment utiliser le bot"},
                            ],
                        }
                    ],
                },
            },
        }

        try:
            resp = await asyncio.to_thread(
                requests.post, url, json=payload, headers=headers, timeout=15
            )
            result = resp.json()
            if resp.status_code in (200, 201):
                msg_id = result.get("messages", [{}])[0].get("id", "")
                return {"sid": msg_id, "status": "sent"}
            else:
                logger.warning("Interactive message failed, falling back to text")
                return await self.send_message(to, "Tape *menu* pour voir les options.")
        except Exception as e:
            logger.error(f"Interactive menu error: {e}")
            return await self.send_message(to, "Tape *menu* pour voir les options.")
