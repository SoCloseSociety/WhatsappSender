"""
SoClose Community Bot — Telegram Admin Bot
Remote administration via Telegram: broadcasts, user management, stats, project sync.
"""

import asyncio
import logging
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import config
import database
import github_api
from whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)
wa_client = WhatsAppClient()

# Conversation states
BROADCAST_MESSAGE, BROADCAST_CONFIRM = range(2)


# ── Auth Decorator ────────────────────────────────────────────

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
            if update.message:
                await update.message.reply_text("⛔ Acces refuse. Admin uniquement.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Acces refuse.", show_alert=True)
            return ConversationHandler.END if hasattr(func, '_is_conversation') else None
        return await func(update, context)
    return wrapper


# ── Commands ──────────────────────────────────────────────────

@admin_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("👥 Utilisateurs", callback_data="users"),
        ],
        [
            InlineKeyboardButton("📦 Projets", callback_data="projects"),
            InlineKeyboardButton("🔄 Sync GitHub", callback_data="sync"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
            InlineKeyboardButton("📋 Templates", callback_data="templates"),
        ],
        [
            InlineKeyboardButton("📨 Historique", callback_data="history"),
            InlineKeyboardButton("ℹ️ Aide", callback_data="help"),
        ],
    ]
    await update.message.reply_text(
        f"🤖 *{config.BOT_NAME}* v{config.BOT_VERSION}\n\n"
        f"Panel d'administration Telegram.\n"
        f"Choisis une option :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_count = await database.get_user_count()
    msg_stats = await database.get_message_stats()
    projects = await database.get_all_projects()

    text = (
        f"📊 *Statistiques*\n\n"
        f"👥 Utilisateurs: {user_count}\n"
        f"📦 Projets: {len(projects)}\n\n"
        f"📨 *Messages*\n"
        f"  ⏳ En attente: {msg_stats.get('queued', 0)}\n"
        f"  ✅ Envoyes: {msg_stats.get('sent', 0)}\n"
        f"  📬 Livres: {msg_stats.get('delivered', 0)}\n"
        f"  👁 Lus: {msg_stats.get('read', 0)}\n"
        f"  ❌ Echoues: {msg_stats.get('failed', 0)}\n"
        f"  📥 Recus: {msg_stats.get('inbound', 0)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@admin_only
async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await database.get_all_users()
    if not users:
        await update.message.reply_text("Aucun utilisateur enregistre.")
        return

    lines = [f"👥 *Utilisateurs* ({len(users)})\n"]
    for u in users[:30]:
        sub = "✅" if u.get("subscribed") else "❌"
        name = (u.get("name") or "Anonyme")
        lines.append(f"{sub} `{u['phone']}` — {name}")

    if len(users) > 30:
        lines.append(f"\n... et {len(users) - 30} de plus")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@admin_only
async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    projects = await database.get_all_projects()
    if not projects:
        await update.message.reply_text("Aucun projet. Lance /sync pour importer depuis GitHub.")
        return

    text = github_api.format_project_list(projects)
    await update.message.reply_text(f"📦 *Projets* ({len(projects)})\n\n{text}", parse_mode="Markdown")


@admin_only
async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Synchronisation GitHub en cours...")
    repos = await github_api.sync_projects()
    await msg.edit_text(f"✅ {len(repos)} projets synchronises depuis GitHub.")


@admin_only
async def cmd_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    templates = await database.get_all_templates()
    if not templates:
        await update.message.reply_text("Aucun template.")
        return

    lines = [f"📋 *Templates* ({len(templates)})\n"]
    for t in templates:
        lines.append(f"• *{t['name']}* [{t['category']}]\n  {t['body'][:60]}...")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Broadcast Conversation ────────────────────────────────────

@admin_only
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Nouveau Broadcast*\n\n"
        "Envoie le message a diffuser a tous les abonnes.\n"
        "Tu peux utiliser `{name}` comme placeholder.\n\n"
        "Tape /cancel pour annuler.",
        parse_mode="Markdown",
    )
    return BROADCAST_MESSAGE


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    context.user_data["broadcast_msg"] = update.message.text
    users = await database.get_subscribed_users()

    await update.message.reply_text(
        f"📋 *Apercu du broadcast*\n\n"
        f"Message:\n{update.message.text[:300]}\n\n"
        f"Destinataires: {len(users)} abonnes\n\n"
        f"Confirmer l'envoi ? Tape *oui* ou /cancel",
        parse_mode="Markdown",
    )
    return BROADCAST_CONFIRM


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    if update.message.text.strip().lower() not in ("oui", "yes", "ok"):
        await update.message.reply_text("❌ Broadcast annule.")
        return ConversationHandler.END

    msg_text = context.user_data.get("broadcast_msg", "")
    users = await database.get_subscribed_users()

    if not users:
        await update.message.reply_text("Aucun abonne a contacter.")
        return ConversationHandler.END

    # Create broadcast record
    broadcast_id = await database.create_broadcast(title="Broadcast", message=msg_text)

    status_msg = await update.message.reply_text(f"📤 Envoi en cours... 0/{len(users)}")
    last_edit = [0.0]

    def on_progress(current, total, result_status):
        now = asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0
        # Throttle edits to every 3 seconds to avoid Telegram rate limits
        if now - last_edit[0] >= 3 or current == total:
            last_edit[0] = now
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    status_msg.edit_text(f"📤 Envoi en cours... {current}/{total}")
                )
            except RuntimeError:
                pass

    recipients = [{"phone": u["phone"], "name": u.get("name") or ""} for u in users]
    results = await wa_client.send_bulk(
        recipients=recipients,
        message_template=msg_text,
        broadcast_id=broadcast_id,
        on_progress=on_progress,
    )

    await database.update_broadcast_status(broadcast_id, "sent")
    await status_msg.edit_text(
        f"✅ *Broadcast termine*\n\n"
        f"Envoyes: {results['sent']}\n"
        f"Echoues: {results['failed']}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Broadcast annule.")
    return ConversationHandler.END


# ── Callback Query Handler ────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in config.TELEGRAM_ADMIN_IDS:
        await query.edit_message_text("⛔ Acces refuse.")
        return

    action = query.data

    if action == "stats":
        user_count = await database.get_user_count()
        msg_stats = await database.get_message_stats()
        projects = await database.get_all_projects()
        text = (
            f"📊 *Statistiques*\n\n"
            f"👥 Utilisateurs: {user_count}\n"
            f"📦 Projets: {len(projects)}\n\n"
            f"📨 Envoyes: {msg_stats.get('sent', 0)} | "
            f"Livres: {msg_stats.get('delivered', 0)} | "
            f"Echoues: {msg_stats.get('failed', 0)} | "
            f"Recus: {msg_stats.get('inbound', 0)}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    elif action == "users":
        users = await database.get_all_users()
        if not users:
            await query.edit_message_text("Aucun utilisateur.")
            return
        lines = [f"👥 *Utilisateurs* ({len(users)})\n"]
        for u in users[:20]:
            sub = "✅" if u.get("subscribed") else "❌"
            name = (u.get("name") or "Anonyme")
            lines.append(f"{sub} `{u['phone']}` — {name}")
        if len(users) > 20:
            lines.append(f"\n... et {len(users) - 20} de plus")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif action == "projects":
        projects = await database.get_all_projects()
        if not projects:
            await query.edit_message_text("Aucun projet. Utilise /sync.")
            return
        text = github_api.format_project_list(projects)
        await query.edit_message_text(f"📦 *Projets*\n\n{text}", parse_mode="Markdown")

    elif action == "sync":
        await query.edit_message_text("🔄 Sync en cours...")
        repos = await github_api.sync_projects()
        await query.edit_message_text(f"✅ {len(repos)} projets synchronises.")

    elif action == "broadcast":
        await query.edit_message_text(
            "📢 Utilise la commande /broadcast pour envoyer un message a tous les abonnes."
        )

    elif action == "templates":
        templates = await database.get_all_templates()
        if not templates:
            await query.edit_message_text("Aucun template.")
            return
        lines = [f"📋 *Templates* ({len(templates)})\n"]
        for t in templates:
            lines.append(f"• *{t['name']}* [{t['category']}]")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif action == "history":
        broadcasts = await database.get_all_broadcasts()
        if not broadcasts:
            await query.edit_message_text("Aucun historique de broadcast.")
            return
        lines = [f"📨 *Historique* ({len(broadcasts)})\n"]
        for b in broadcasts[:10]:
            status_emoji = {"draft": "📝", "sent": "✅"}.get(b["status"], "⏳")
            lines.append(f"{status_emoji} {b['title']} — {b['created_at'][:10]}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif action == "help":
        await query.edit_message_text(
            "ℹ️ *Commandes Admin*\n\n"
            "/start — Menu principal\n"
            "/stats — Statistiques\n"
            "/users — Liste des utilisateurs\n"
            "/projects — Projets GitHub\n"
            "/sync — Synchroniser GitHub\n"
            "/broadcast — Envoyer un broadcast\n"
            "/templates — Voir les templates\n",
            parse_mode="Markdown",
        )


# ── Build Application ────────────────────────────────────────

def build_telegram_app() -> Application:
    """Build and return the Telegram bot application."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Broadcast conversation
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)],
            BROADCAST_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_confirm)],
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
    )

    app.add_handler(broadcast_conv)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(CommandHandler("templates", cmd_templates))
    app.add_handler(CallbackQueryHandler(button_handler))

    return app
