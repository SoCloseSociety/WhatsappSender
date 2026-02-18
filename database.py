"""
SoClose Community Bot — Database Layer
SQLite async database for users, broadcasts, projects cache, and message logs.
"""

import aiosqlite
import json
from datetime import datetime

import config

_DB = config.DB_PATH

# ── Schema ────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT UNIQUE NOT NULL,
    name            TEXT DEFAULT '',
    language        TEXT DEFAULT 'fr',
    subscribed      INTEGER DEFAULT 1,
    first_seen      TEXT DEFAULT (datetime('now')),
    last_seen       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE NOT NULL,
    description     TEXT DEFAULT '',
    url             TEXT DEFAULT '',
    language        TEXT DEFAULT '',
    stars           INTEGER DEFAULT 0,
    category        TEXT DEFAULT 'bot',
    updated_at      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    status          TEXT DEFAULT 'draft',
    target_filter   TEXT DEFAULT '{}',
    created_at      TEXT DEFAULT (datetime('now')),
    sent_at         TEXT
);

CREATE TABLE IF NOT EXISTS message_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    broadcast_id    INTEGER,
    user_id         INTEGER,
    phone           TEXT NOT NULL,
    direction       TEXT DEFAULT 'outbound',
    content         TEXT DEFAULT '',
    status          TEXT DEFAULT 'queued',
    provider_sid    TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (broadcast_id) REFERENCES broadcasts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE NOT NULL,
    category        TEXT DEFAULT 'general',
    body            TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

_DEFAULT_TEMPLATES = [
    (
        "welcome",
        "onboarding",
        (
            "Bienvenue dans la communaute SoClose Society ! 🚀\n\n"
            "Tu as maintenant acces a tous nos outils open-source :\n"
            "bots, scrapers, automatisations...\n\n"
            "Tape *menu* pour decouvrir nos projets.\n"
            "Tape *aide* pour obtenir de l'aide."
        ),
    ),
    (
        "project_list",
        "info",
        (
            "📦 *Nos Projets Open-Source*\n\n"
            "{project_list}\n\n"
            "Tape le *numero* du projet pour plus de details.\n"
            "Tape *menu* pour revenir au menu principal."
        ),
    ),
    (
        "project_detail",
        "info",
        (
            "🔧 *{project_name}*\n\n"
            "{project_description}\n\n"
            "⭐ Stars: {stars}\n"
            "💻 Langage: {language}\n"
            "🔗 GitHub: {project_url}\n\n"
            "Tape *menu* pour revenir au menu."
        ),
    ),
    (
        "broadcast_announcement",
        "broadcast",
        (
            "📢 *Annonce SoClose Society*\n\n"
            "{announcement_text}\n\n"
            "🔗 {link}\n\n"
            "Tape *stop* pour te desabonner."
        ),
    ),
    (
        "help",
        "info",
        (
            "ℹ️ *Aide — SoClose Community Bot*\n\n"
            "*menu* — Menu principal\n"
            "*projets* — Liste des projets\n"
            "*aide* — Ce message\n"
            "*stop* — Se desabonner\n"
            "*start* — Se reabonner\n\n"
            "Tu peux aussi taper le nom d'un projet pour le rechercher.\n\n"
            "🌐 GitHub: github.com/SoCloseSociety\n"
            "🌐 Site: soclose.co"
        ),
    ),
]


# ── Init ──────────────────────────────────────────────────────

async def init():
    """Create tables and seed default templates."""
    async with aiosqlite.connect(_DB) as db:
        await db.executescript(_SCHEMA)
        for name, category, body in _DEFAULT_TEMPLATES:
            await db.execute(
                "INSERT OR IGNORE INTO templates (name, category, body) VALUES (?, ?, ?)",
                (name, category, body),
            )
        await db.commit()


# ── Users ─────────────────────────────────────────────────────

async def upsert_user(phone: str, name: str = "") -> int:
    """Create or update a user. Returns user ID."""
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute(
            """INSERT INTO users (phone, name)
               VALUES (?, ?)
               ON CONFLICT(phone) DO UPDATE SET
                 name = CASE WHEN excluded.name != '' THEN excluded.name ELSE users.name END,
                 last_seen = datetime('now')""",
            (phone, name or ""),
        )
        await db.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        row_cursor = await db.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        row = await row_cursor.fetchone()
        return row[0] if row else 0


async def get_user(phone: str) -> dict | None:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_user_subscribed(phone: str, subscribed: bool) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            "UPDATE users SET subscribed = ? WHERE phone = ?",
            (1 if subscribed else 0, phone),
        )
        await db.commit()


async def get_subscribed_users() -> list[dict]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE subscribed = 1")
        return [dict(row) for row in await cursor.fetchall()]


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY last_seen DESC")
        return [dict(row) for row in await cursor.fetchall()]


async def get_user_count() -> int:
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0]


# ── Projects ──────────────────────────────────────────────────

async def upsert_project(
    name: str,
    description: str = "",
    url: str = "",
    language: str = "",
    stars: int = 0,
    category: str = "bot",
    updated_at: str = "",
) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            """INSERT INTO projects (name, description, url, language, stars, category, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 description = excluded.description,
                 url = excluded.url,
                 language = excluded.language,
                 stars = excluded.stars,
                 category = excluded.category,
                 updated_at = excluded.updated_at""",
            (name, description, url, language, stars, category, updated_at),
        )
        await db.commit()


async def get_all_projects() -> list[dict]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects ORDER BY stars DESC, name ASC")
        return [dict(row) for row in await cursor.fetchall()]


async def search_projects(query: str) -> list[dict]:
    escaped = query.replace("%", "\\%").replace("_", "\\_")
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM projects WHERE name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' ORDER BY stars DESC",
            (f"%{escaped}%", f"%{escaped}%"),
        )
        return [dict(row) for row in await cursor.fetchall()]


# ── Broadcasts ────────────────────────────────────────────────

async def create_broadcast(title: str, message: str, target_filter: dict | None = None) -> int:
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute(
            "INSERT INTO broadcasts (title, message, target_filter) VALUES (?, ?, ?)",
            (title, message, json.dumps(target_filter or {})),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def get_broadcast(broadcast_id: int) -> dict | None:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_broadcast_status(broadcast_id: int, status: str) -> None:
    async with aiosqlite.connect(_DB) as db:
        if status == "sent":
            await db.execute(
                "UPDATE broadcasts SET status = ?, sent_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), broadcast_id),
            )
        else:
            await db.execute(
                "UPDATE broadcasts SET status = ? WHERE id = ?",
                (status, broadcast_id),
            )
        await db.commit()


async def get_all_broadcasts() -> list[dict]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM broadcasts ORDER BY created_at DESC")
        return [dict(row) for row in await cursor.fetchall()]


# ── Message Log ───────────────────────────────────────────────

async def log_message(
    phone: str,
    content: str = "",
    direction: str = "outbound",
    status: str = "queued",
    broadcast_id: int | None = None,
    user_id: int | None = None,
    provider_sid: str = "",
) -> int:
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute(
            """INSERT INTO message_log
               (broadcast_id, user_id, phone, direction, content, status, provider_sid)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (broadcast_id, user_id, phone, direction, content, status, provider_sid),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def update_message_status(provider_sid: str, status: str) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            "UPDATE message_log SET status = ?, updated_at = datetime('now') WHERE provider_sid = ?",
            (status, provider_sid),
        )
        await db.commit()


async def get_message_stats() -> dict:
    async with aiosqlite.connect(_DB) as db:
        stats = {}
        for s in ("queued", "sent", "delivered", "read", "failed"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM message_log WHERE status = ? AND direction = 'outbound'",
                (s,),
            )
            row = await cursor.fetchone()
            stats[s] = row[0]
        cursor = await db.execute(
            "SELECT COUNT(*) FROM message_log WHERE direction = 'inbound'"
        )
        row = await cursor.fetchone()
        stats["inbound"] = row[0]
        return stats


async def get_broadcast_stats(broadcast_id: int) -> dict:
    async with aiosqlite.connect(_DB) as db:
        stats = {}
        for s in ("queued", "sent", "delivered", "read", "failed"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM message_log WHERE broadcast_id = ? AND status = ?",
                (broadcast_id, s),
            )
            row = await cursor.fetchone()
            stats[s] = row[0]
        return stats


# ── Templates ─────────────────────────────────────────────────

async def get_template(name: str) -> dict | None:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_templates() -> list[dict]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM templates ORDER BY category, name")
        return [dict(row) for row in await cursor.fetchall()]


async def create_template(name: str, category: str, body: str) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO templates (name, category, body) VALUES (?, ?, ?)",
            (name, category, body),
        )
        await db.commit()


async def delete_template(name: str) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute("DELETE FROM templates WHERE name = ?", (name,))
        await db.commit()
