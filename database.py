"""
WhatsApp Bulk Sender — Database Layer
SQLite async database for contacts, campaigns, message logs, and templates.
"""

from __future__ import annotations

import logging

import aiosqlite
from datetime import datetime

import config

logger = logging.getLogger(__name__)

_DB = config.DB_PATH

# -- Schema ---------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name  TEXT DEFAULT 'Contact',
    last_name   TEXT DEFAULT '',
    phone       TEXT UNIQUE NOT NULL,
    email       TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaigns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    message     TEXT DEFAULT '',
    status      TEXT DEFAULT 'draft',
    created_at  TEXT DEFAULT (datetime('now')),
    sent_at     TEXT
);

CREATE TABLE IF NOT EXISTS campaign_contacts (
    campaign_id INTEGER NOT NULL,
    contact_id  INTEGER NOT NULL,
    PRIMARY KEY (campaign_id, contact_id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS message_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id      INTEGER,
    campaign_id     INTEGER,
    phone           TEXT NOT NULL,
    content         TEXT DEFAULT '',
    status          TEXT DEFAULT 'queued',
    wa_message_id   TEXT DEFAULT '',
    error_message   TEXT DEFAULT '',
    sent_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    category    TEXT DEFAULT 'general',
    body        TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

_DEFAULT_TEMPLATES = [
    (
        "simple_hello",
        "general",
        "Bonjour {first_name} ! Ceci est un message de la part de SoClose Society.",
    ),
    (
        "promo",
        "broadcast",
        (
            "Salut {first_name} !\n\n"
            "Decouvrez nos derniers outils et projets open-source.\n"
            "Plus d'infos sur https://soclose.co\n\n"
            "A bientot !"
        ),
    ),
    (
        "reminder",
        "broadcast",
        "Bonjour {first_name}, un petit rappel de SoClose Society. N'hesitez pas a nous contacter !",
    ),
]


# -- Connection helper ----------------------------------------

async def _connect() -> aiosqlite.Connection:
    """Open a connection with WAL mode and foreign keys enabled."""
    db = await aiosqlite.connect(_DB)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


# -- Init -----------------------------------------------------

async def init():
    """Create tables and seed default templates."""
    db = await _connect()
    try:
        await db.executescript(_SCHEMA)
        for name, category, body in _DEFAULT_TEMPLATES:
            await db.execute(
                "INSERT OR IGNORE INTO templates (name, category, body) VALUES (?, ?, ?)",
                (name, category, body),
            )
        await db.commit()
    finally:
        await db.close()


# -- Contacts -------------------------------------------------

async def upsert_contact(first_name: str, last_name: str, phone: str, email: str = "") -> int:
    """Create or update a contact. Returns contact ID."""
    db = await _connect()
    try:
        cursor = await db.execute(
            """INSERT INTO contacts (first_name, last_name, phone, email)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(phone) DO UPDATE SET
                 first_name = CASE WHEN excluded.first_name != 'Contact' THEN excluded.first_name ELSE contacts.first_name END,
                 last_name = CASE WHEN excluded.last_name != '' THEN excluded.last_name ELSE contacts.last_name END,
                 email = CASE WHEN excluded.email != '' THEN excluded.email ELSE contacts.email END""",
            (first_name or "Contact", last_name or "", phone, email or ""),
        )
        await db.commit()
        # Always fetch the actual ID to avoid returning 0
        row_cursor = await db.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
        row = await row_cursor.fetchone()
        return row[0] if row else 0
    finally:
        await db.close()


async def get_contact_by_phone(phone: str) -> dict | None:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_all_contacts() -> list[dict]:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM contacts ORDER BY created_at DESC")
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def get_contact_count() -> int:
    db = await _connect()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM contacts")
        row = await cursor.fetchone()
        return row[0]
    finally:
        await db.close()


async def delete_all_contacts() -> int:
    """Delete all contacts. Nullifies references in message_log."""
    db = await _connect()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM contacts")
        row = await cursor.fetchone()
        count = row[0]
        await db.execute("UPDATE message_log SET contact_id = NULL")
        await db.execute("DELETE FROM campaign_contacts")
        await db.execute("DELETE FROM contacts")
        await db.commit()
        return count
    finally:
        await db.close()


# -- Campaigns ------------------------------------------------

async def create_campaign(name: str, message: str = "") -> int:
    db = await _connect()
    try:
        cursor = await db.execute(
            "INSERT INTO campaigns (name, message) VALUES (?, ?)",
            (name, message),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def get_campaign(campaign_id: int) -> dict | None:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_campaign_status(campaign_id: int, status: str) -> None:
    db = await _connect()
    try:
        if status == "sent":
            await db.execute(
                "UPDATE campaigns SET status = ?, sent_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), campaign_id),
            )
        else:
            await db.execute(
                "UPDATE campaigns SET status = ? WHERE id = ?",
                (status, campaign_id),
            )
        await db.commit()
    finally:
        await db.close()


async def update_campaign_message(campaign_id: int, message: str) -> None:
    """Save the actual message sent for audit trail."""
    db = await _connect()
    try:
        await db.execute(
            "UPDATE campaigns SET message = ? WHERE id = ?",
            (message, campaign_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_all_campaigns() -> list[dict]:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT c.*, COUNT(cc.contact_id) as contact_count
               FROM campaigns c
               LEFT JOIN campaign_contacts cc ON c.id = cc.campaign_id
               GROUP BY c.id
               ORDER BY c.created_at DESC"""
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def add_contacts_to_campaign(campaign_id: int, contact_ids: list[int]) -> int:
    """Link contacts to a campaign. Returns number actually added."""
    added = 0
    db = await _connect()
    try:
        for cid in contact_ids:
            if cid <= 0:
                continue
            try:
                cursor = await db.execute(
                    "INSERT OR IGNORE INTO campaign_contacts (campaign_id, contact_id) VALUES (?, ?)",
                    (campaign_id, cid),
                )
                if cursor.rowcount > 0:
                    added += 1
            except Exception as e:
                logger.warning(f"Failed to link contact {cid} to campaign {campaign_id}: {e}")
        await db.commit()
    finally:
        await db.close()
    return added


async def get_contacts_for_campaign(campaign_id: int) -> list[dict]:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT c.* FROM contacts c
               INNER JOIN campaign_contacts cc ON c.id = cc.contact_id
               WHERE cc.campaign_id = ?
               ORDER BY c.first_name""",
            (campaign_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def get_contact_count_for_campaign(campaign_id: int) -> int:
    db = await _connect()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM campaign_contacts WHERE campaign_id = ?",
            (campaign_id,),
        )
        row = await cursor.fetchone()
        return row[0]
    finally:
        await db.close()


# -- Message Log ----------------------------------------------

async def log_message(
    phone: str,
    content: str = "",
    status: str = "queued",
    campaign_id: int | None = None,
    contact_id: int | None = None,
    wa_message_id: str = "",
    error_message: str = "",
) -> int:
    db = await _connect()
    try:
        cursor = await db.execute(
            """INSERT INTO message_log
               (contact_id, campaign_id, phone, content, status, wa_message_id, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (contact_id, campaign_id, phone, content, status, wa_message_id, error_message),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def update_message_status(wa_message_id: str, status: str) -> None:
    db = await _connect()
    try:
        await db.execute(
            "UPDATE message_log SET status = ? WHERE wa_message_id = ?",
            (status, wa_message_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_send_stats() -> dict:
    """Get overall sending statistics."""
    db = await _connect()
    try:
        stats = {}
        for s in ("queued", "sent", "delivered", "read", "failed"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM message_log WHERE status = ?", (s,)
            )
            row = await cursor.fetchone()
            stats[s] = row[0]
        cursor = await db.execute("SELECT COUNT(*) FROM message_log")
        row = await cursor.fetchone()
        stats["total"] = row[0]
        return stats
    finally:
        await db.close()


async def get_campaign_stats(campaign_id: int) -> dict:
    db = await _connect()
    try:
        stats = {}
        for s in ("queued", "sent", "delivered", "read", "failed"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM message_log WHERE campaign_id = ? AND status = ?",
                (campaign_id, s),
            )
            row = await cursor.fetchone()
            stats[s] = row[0]
        return stats
    finally:
        await db.close()


async def get_recent_messages(limit: int = 20) -> list[dict]:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM message_log ORDER BY sent_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


# -- Templates ------------------------------------------------

async def get_all_templates() -> list[dict]:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates ORDER BY category, name")
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def get_template(name: str) -> dict | None:
    db = await _connect()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def create_template(name: str, category: str, body: str) -> None:
    db = await _connect()
    try:
        await db.execute(
            """INSERT INTO templates (name, category, body) VALUES (?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET category = excluded.category, body = excluded.body""",
            (name, category, body),
        )
        await db.commit()
    finally:
        await db.close()


async def delete_template(name: str) -> None:
    db = await _connect()
    try:
        await db.execute("DELETE FROM templates WHERE name = ?", (name,))
        await db.commit()
    finally:
        await db.close()
