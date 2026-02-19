"""
WhatsApp Bulk Sender — Telegram Admin Bot
Remote administration via Telegram: import CSV, send campaigns, stats.
"""

import asyncio
import html
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
import csv_handler
from whatsapp import WhatsAppClient, _render_message

logger = logging.getLogger(__name__)
wa_client = WhatsAppClient()

# Conversation states
IMPORT_CSV, IMPORT_NAME = range(2)
SEND_CAMPAIGN, SEND_MESSAGE, SEND_CONFIRM = range(10, 13)


def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return html.escape(str(text))


# -- Auth Decorator --------------------------------------------

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
            if update.message:
                await update.message.reply_text("⛔ Acces refuse. Admin uniquement.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Acces refuse.", show_alert=True)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


def _reply(update: Update):
    """Get the appropriate reply method (message or callback query)."""
    if update.message:
        return update.message.reply_text
    if update.callback_query:
        return update.callback_query.edit_message_text
    return None


# -- Commands --------------------------------------------------

@admin_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = _reply(update)
    if not reply:
        return
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("👥 Contacts", callback_data="contacts"),
        ],
        [
            InlineKeyboardButton("📢 Campagnes", callback_data="campaigns"),
            InlineKeyboardButton("📋 Templates", callback_data="templates"),
        ],
        [
            InlineKeyboardButton("ℹ️ Aide", callback_data="help"),
        ],
    ]
    await reply(
        f"📱 <b>{_esc(config.BOT_NAME)}</b> v{config.BOT_VERSION}\n\n"
        f"Panel d'administration.\n"
        f"Provider: {config.WA_PROVIDER.upper()}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = _reply(update)
    if not reply:
        return
    contact_count = await database.get_contact_count()
    stats = await database.get_send_stats()
    campaigns = await database.get_all_campaigns()

    text = (
        f"📊 <b>Statistiques</b>\n\n"
        f"👥 Contacts: {contact_count}\n"
        f"📢 Campagnes: {len(campaigns)}\n"
        f"📨 Total envois: {stats.get('total', 0)}\n\n"
        f"<b>Statuts</b>\n"
        f"  ⏳ En attente: {stats.get('queued', 0)}\n"
        f"  ✅ Envoyes: {stats.get('sent', 0)}\n"
        f"  📬 Livres: {stats.get('delivered', 0)}\n"
        f"  👁 Lus: {stats.get('read', 0)}\n"
        f"  ❌ Echoues: {stats.get('failed', 0)}"
    )
    await reply(text, parse_mode="HTML")


@admin_only
async def cmd_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = _reply(update)
    if not reply:
        return
    contacts = await database.get_all_contacts()
    if not contacts:
        await reply("Aucun contact. Utilise /import pour importer un CSV.")
        return

    lines = [f"👥 <b>Contacts</b> ({len(contacts)})\n"]
    for c in contacts[:30]:
        fn = _esc(c.get("first_name", ""))
        ln = _esc(c.get("last_name", ""))
        lines.append(f"• <code>{_esc(c['phone'])}</code> — {fn} {ln}")

    if len(contacts) > 30:
        lines.append(f"\n... et {len(contacts) - 30} de plus")

    await reply("\n".join(lines), parse_mode="HTML")


@admin_only
async def cmd_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = _reply(update)
    if not reply:
        return
    templates = await database.get_all_templates()
    if not templates:
        await reply("Aucun template.")
        return

    lines = [f"📋 <b>Templates</b> ({len(templates)})\n"]
    for t in templates:
        lines.append(f"• <b>{_esc(t['name'])}</b> [{_esc(t['category'])}]\n  {_esc(t['body'][:60])}...")

    await reply("\n".join(lines), parse_mode="HTML")


# -- Import CSV Conversation -----------------------------------

@admin_only
async def import_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text(
        "📥 <b>Import CSV</b>\n\n"
        "Envoie-moi un fichier CSV avec les colonnes:\n"
        "<code>phone</code>, <code>first_name</code>, <code>last_name</code> (optionnel), <code>email</code> (optionnel)\n\n"
        "Tape /cancel pour annuler.",
        parse_mode="HTML",
    )
    return IMPORT_CSV


async def import_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".csv"):
        await update.message.reply_text("Envoie un fichier .csv")
        return IMPORT_CSV

    file = await doc.get_file()
    data = await file.download_as_bytearray()
    contacts, errors = csv_handler.parse_csv(bytes(data))

    if not contacts:
        err_text = "\n".join(errors[:3]) if errors else "Aucun contact valide."
        await update.message.reply_text(f"❌ Import echoue:\n{err_text}")
        return ConversationHandler.END

    context.user_data["import_contacts"] = contacts
    context.user_data["import_errors"] = errors

    msg = f"✅ {len(contacts)} contacts trouves."
    if errors:
        msg += f"\n⚠ {len(errors)} erreurs."
    msg += "\n\nDonne un nom a cette campagne:"

    await update.message.reply_text(msg)
    return IMPORT_NAME


async def import_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    campaign_name = update.message.text.strip()
    contacts = context.user_data.get("import_contacts", [])

    if not contacts:
        await update.message.reply_text("❌ Aucun contact a importer.")
        return ConversationHandler.END

    status_msg = await update.message.reply_text("⏳ Import en cours...")

    contact_ids = []
    for c in contacts:
        cid = await database.upsert_contact(
            first_name=c["first_name"],
            last_name=c["last_name"],
            phone=c["phone"],
            email=c.get("email", ""),
        )
        contact_ids.append(cid)

    campaign_id = await database.create_campaign(name=campaign_name)
    await database.add_contacts_to_campaign(campaign_id, contact_ids)

    await status_msg.edit_text(
        f"✅ <b>Import termine</b>\n\n"
        f"Campagne: {_esc(campaign_name)}\n"
        f"Contacts: {len(contacts)}\n\n"
        f"Utilise /send pour envoyer des messages.",
        parse_mode="HTML",
    )
    return ConversationHandler.END


# -- Send Conversation -----------------------------------------

@admin_only
async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
    campaigns = await database.get_all_campaigns()
    if not campaigns:
        await update.message.reply_text("Aucune campagne. Utilise /import d'abord.")
        return ConversationHandler.END

    keyboard = []
    for c in campaigns[:10]:
        count = c.get("contact_count", 0)
        keyboard.append([InlineKeyboardButton(
            f"{c['name']} ({count} contacts)",
            callback_data=f"send_{c['id']}",
        )])

    await update.message.reply_text(
        "📢 <b>Choisir une campagne:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SEND_CAMPAIGN


async def send_select_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    try:
        campaign_id = int(query.data.replace("send_", ""))
    except (ValueError, TypeError):
        await query.edit_message_text("Campagne invalide.")
        return ConversationHandler.END

    context.user_data["send_campaign_id"] = campaign_id

    contacts = await database.get_contacts_for_campaign(campaign_id)
    if not contacts:
        await query.edit_message_text("Aucun contact dans cette campagne.")
        return ConversationHandler.END

    context.user_data["send_contacts"] = contacts

    # Offer templates
    templates = await database.get_all_templates()
    text = (
        f"📝 {len(contacts)} destinataires.\n\n"
        f"Ecris ton message ou choisis un template.\n"
        f"Placeholders: {{first_name}}, {{last_name}}, {{phone}}\n\n"
    )
    if templates:
        text += "Templates:\n"
        for t in templates:
            text += f"• /tpl_{t['name']}\n"

    text += "\nTape /cancel pour annuler."
    await query.edit_message_text(text)
    return SEND_MESSAGE


async def send_compose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    text = update.message.text.strip()

    # Check if it's a template reference
    if text.startswith("/tpl_"):
        tpl_name = text[5:]
        tpl = await database.get_template(tpl_name)
        if tpl:
            text = tpl["body"]
        else:
            await update.message.reply_text(f"Template '{tpl_name}' introuvable.")
            return SEND_MESSAGE

    context.user_data["send_message"] = text
    contacts = context.user_data.get("send_contacts", [])

    # Preview with safe rendering
    sample = contacts[0] if contacts else {}
    preview = _render_message(text, {
        "first_name": sample.get("first_name", "Contact"),
        "last_name": sample.get("last_name", ""),
        "phone": sample.get("phone", ""),
        "name": f"{sample.get('first_name', '')} {sample.get('last_name', '')}".strip(),
    })

    await update.message.reply_text(
        f"📋 Apercu:\n\n{preview[:300]}\n\n"
        f"Destinataires: {len(contacts)}\n\n"
        f"Confirmer ? Tape oui ou /cancel",
    )
    return SEND_CONFIRM


async def send_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.TELEGRAM_ADMIN_IDS:
        return ConversationHandler.END

    if update.message.text.strip().lower() not in ("oui", "yes", "ok"):
        await update.message.reply_text("❌ Envoi annule.")
        return ConversationHandler.END

    message = context.user_data.get("send_message", "")
    contacts = context.user_data.get("send_contacts", [])
    campaign_id = context.user_data.get("send_campaign_id")

    if not contacts or not message:
        await update.message.reply_text("❌ Donnees manquantes.")
        return ConversationHandler.END

    # Save message to campaign for audit trail
    if campaign_id:
        await database.update_campaign_message(campaign_id, message)

    status_msg = await update.message.reply_text(f"📤 Envoi en cours... 0/{len(contacts)}")
    last_edit = [0.0]
    _edit_task = [None]

    def on_progress(current, total, result_status):
        try:
            now = asyncio.get_running_loop().time()
        except RuntimeError:
            return
        if now - last_edit[0] >= 3 or current == total:
            last_edit[0] = now
            if _edit_task[0] and not _edit_task[0].done():
                return
            _edit_task[0] = asyncio.get_running_loop().create_task(
                status_msg.edit_text(f"📤 Envoi en cours... {current}/{total}")
            )

    recipients = [
        {
            "phone": c["phone"],
            "first_name": c.get("first_name", "Contact"),
            "last_name": c.get("last_name", ""),
            "id": c.get("id"),
        }
        for c in contacts
    ]

    results = await wa_client.send_bulk(
        recipients=recipients,
        message_template=message,
        campaign_id=campaign_id,
        on_progress=on_progress,
    )

    if campaign_id:
        await database.update_campaign_status(campaign_id, "sent")

    await status_msg.edit_text(
        f"✅ <b>Envoi termine</b>\n\n"
        f"Envoyes: {results['sent']}\n"
        f"Echoues: {results['failed']}",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Annule.")
    return ConversationHandler.END


# -- Callback Query Handler ------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in config.TELEGRAM_ADMIN_IDS:
        await query.edit_message_text("⛔ Acces refuse.")
        return

    action = query.data

    if action == "stats":
        contact_count = await database.get_contact_count()
        stats = await database.get_send_stats()
        campaigns = await database.get_all_campaigns()
        text = (
            f"📊 <b>Statistiques</b>\n\n"
            f"👥 Contacts: {contact_count}\n"
            f"📢 Campagnes: {len(campaigns)}\n\n"
            f"✅ Envoyes: {stats.get('sent', 0)} | "
            f"📬 Livres: {stats.get('delivered', 0)} | "
            f"❌ Echoues: {stats.get('failed', 0)}"
        )
        await query.edit_message_text(text, parse_mode="HTML")

    elif action == "contacts":
        contacts = await database.get_all_contacts()
        if not contacts:
            await query.edit_message_text("Aucun contact. Utilise /import.")
            return
        lines = [f"👥 <b>Contacts</b> ({len(contacts)})\n"]
        for c in contacts[:20]:
            lines.append(f"• <code>{_esc(c['phone'])}</code> — {_esc(c.get('first_name', ''))} {_esc(c.get('last_name', ''))}")
        if len(contacts) > 20:
            lines.append(f"\n... et {len(contacts) - 20} de plus")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "campaigns":
        campaigns = await database.get_all_campaigns()
        if not campaigns:
            await query.edit_message_text("Aucune campagne. Utilise /import.")
            return
        lines = [f"📢 <b>Campagnes</b> ({len(campaigns)})\n"]
        for c in campaigns[:10]:
            status_emoji = {"draft": "📝", "sent": "✅", "sending": "📤"}.get(c["status"], "⏳")
            lines.append(f"{status_emoji} {_esc(c['name'])} — {c.get('contact_count', 0)} contacts")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "templates":
        templates = await database.get_all_templates()
        if not templates:
            await query.edit_message_text("Aucun template.")
            return
        lines = [f"📋 <b>Templates</b> ({len(templates)})\n"]
        for t in templates:
            lines.append(f"• <b>{_esc(t['name'])}</b> [{_esc(t['category'])}]")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "help":
        await query.edit_message_text(
            "ℹ️ <b>Commandes</b>\n\n"
            "/start — Menu principal\n"
            "/stats — Statistiques\n"
            "/contacts — Liste des contacts\n"
            "/import — Importer un CSV\n"
            "/send — Envoyer une campagne\n"
            "/templates — Templates\n",
            parse_mode="HTML",
        )


# -- Build Application -----------------------------------------

def build_telegram_app() -> Application:
    """Build and return the Telegram bot application."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Import conversation
    import_conv = ConversationHandler(
        entry_points=[CommandHandler("import", import_start)],
        states={
            IMPORT_CSV: [MessageHandler(filters.Document.ALL, import_csv)],
            IMPORT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, import_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Send conversation
    send_conv = ConversationHandler(
        entry_points=[CommandHandler("send", send_start)],
        states={
            SEND_CAMPAIGN: [CallbackQueryHandler(send_select_campaign, pattern=r"^send_\d+$")],
            SEND_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_compose)],
            SEND_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(import_conv)
    app.add_handler(send_conv)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("contacts", cmd_contacts))
    app.add_handler(CommandHandler("templates", cmd_templates))
    app.add_handler(CallbackQueryHandler(button_handler))

    return app
