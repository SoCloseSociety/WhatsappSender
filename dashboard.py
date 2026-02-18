"""
SoClose Community Bot — Streamlit Web Dashboard
Web interface for community management, broadcasting, and analytics.
"""

import asyncio
import os
import threading

import streamlit as st
import pandas as pd

import config
import database
import github_api
from whatsapp import WhatsAppClient


# ── Async Bridge ──────────────────────────────────────────────
# Single background event loop reused across all calls

_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()


def run_async(coro):
    """Run an async coroutine from sync Streamlit context."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=30)


def init_db():
    if "db_init" not in st.session_state:
        run_async(database.init())
        st.session_state.db_init = True


# ── Page Config ───────────────────────────────────────────────

st.set_page_config(
    page_title=config.BOT_NAME,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Authentication Gate ───────────────────────────────────────

if config.DASHBOARD_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 SoClose Community Bot")
        st.markdown("Entrez le mot de passe pour acceder au dashboard.")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Connexion"):
            if password == config.DASHBOARD_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.stop()

init_db()


# ── Sidebar ───────────────────────────────────────────────────

with st.sidebar:
    st.image("https://github.com/SoCloseSociety.png", width=80)
    st.title("SoClose Community")
    st.caption(f"v{config.BOT_VERSION} | {config.WA_PROVIDER.upper()}")

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "📦 Projets",
            "👥 Utilisateurs",
            "📢 Broadcast",
            "📋 Templates",
            "📊 Statistiques",
            "💬 Test Message",
            "⚙️ Configuration",
        ],
    )

    st.divider()
    st.markdown(f"[GitHub]({config.COMMUNITY_URL}) | [Site]({config.WEBSITE_URL})")


# ── Dashboard Page ────────────────────────────────────────────

if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.markdown(f"**{config.BOT_NAME}** — Panel de gestion communautaire")

    # KPIs
    user_count = run_async(database.get_user_count())
    projects = run_async(database.get_all_projects())
    msg_stats = run_async(database.get_message_stats())
    broadcasts = run_async(database.get_all_broadcasts())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Utilisateurs", user_count)
    col2.metric("Projets", len(projects))
    col3.metric("Messages envoyes", msg_stats.get("sent", 0) + msg_stats.get("delivered", 0))
    col4.metric("Broadcasts", len(broadcasts))

    # Delivery rate
    total_out = sum(msg_stats.get(s, 0) for s in ("sent", "delivered", "read", "failed"))
    delivered = msg_stats.get("delivered", 0) + msg_stats.get("read", 0)
    rate = (delivered / total_out * 100) if total_out > 0 else 0

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Taux livraison", f"{rate:.1f}%")
    col6.metric("Messages lus", msg_stats.get("read", 0))
    col7.metric("Echoues", msg_stats.get("failed", 0))
    col8.metric("Recus (inbound)", msg_stats.get("inbound", 0))

    # Quick sync
    st.divider()
    if st.button("🔄 Synchroniser les projets GitHub"):
        with st.spinner("Synchronisation..."):
            repos = run_async(github_api.sync_projects())
            st.success(f"{len(repos)} projets synchronises !")
            st.rerun()


# ── Projects Page ─────────────────────────────────────────────

elif page == "📦 Projets":
    st.title("📦 Projets Open-Source")

    projects = run_async(database.get_all_projects())

    if not projects:
        st.warning("Aucun projet. Cliquez ci-dessous pour synchroniser.")
        if st.button("🔄 Sync GitHub"):
            with st.spinner("Synchronisation..."):
                repos = run_async(github_api.sync_projects())
                st.success(f"{len(repos)} projets importes !")
                st.rerun()
    else:
        # Filter
        categories = sorted(set(p.get("category", "tool") for p in projects))
        selected_cat = st.multiselect("Filtrer par categorie", categories, default=categories)

        filtered = [p for p in projects if p.get("category", "tool") in selected_cat]

        for p in filtered:
            emoji = {"bot": "🤖", "scraper": "🔍", "automation": "⚡", "template": "📄"}.get(
                p.get("category", ""), "🔧"
            )
            with st.expander(f"{emoji} {github_api.friendly_name(p['name'])} — ⭐ {p.get('stars', 0)} | {p.get('language', 'N/A')}"):
                st.markdown(f"**Description:** {p.get('description', 'N/A')}")
                st.markdown(f"**Categorie:** {p.get('category', 'N/A')}")
                st.markdown(f"**Derniere MAJ:** {(p.get('updated_at', '') or '')[:10]}")
                st.markdown(f"[Voir sur GitHub]({p.get('url', '')})")

        st.divider()
        if st.button("🔄 Rafraichir depuis GitHub"):
            with st.spinner("Synchronisation..."):
                repos = run_async(github_api.sync_projects())
                st.success(f"{len(repos)} projets mis a jour !")
                st.rerun()


# ── Users Page ────────────────────────────────────────────────

elif page == "👥 Utilisateurs":
    st.title("👥 Utilisateurs")

    users = run_async(database.get_all_users())

    if not users:
        st.info("Aucun utilisateur enregistre. Les utilisateurs apparaitront ici quand ils contacteront le bot.")
    else:
        subscribed = [u for u in users if u.get("subscribed")]
        st.metric("Total", len(users))
        col1, col2 = st.columns(2)
        col1.metric("Abonnes", len(subscribed))
        col2.metric("Desabonnes", len(users) - len(subscribed))

        df = pd.DataFrame(users)
        display_cols = [c for c in ["phone", "name", "subscribed", "language", "first_seen", "last_seen"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)


# ── Broadcast Page ────────────────────────────────────────────

elif page == "📢 Broadcast":
    st.title("📢 Envoyer un Broadcast")

    users = run_async(database.get_subscribed_users())
    st.info(f"**{len(users)}** abonnes recevront le message.")

    # Template selector
    templates = run_async(database.get_all_templates())
    template_names = ["(Aucun)"] + [t["name"] for t in templates]
    selected_tpl = st.selectbox("Utiliser un template", template_names)

    default_msg = ""
    if selected_tpl != "(Aucun)":
        tpl = next((t for t in templates if t["name"] == selected_tpl), None)
        if tpl:
            default_msg = tpl["body"]

    message = st.text_area("Message", value=default_msg, height=200, help="Placeholders: {name}, {phone}")

    if message:
        st.markdown("**Apercu:**")
        preview = message.replace("{name}", "Jean").replace("{phone}", "+33612345678")
        st.text(preview)

    col1, col2 = st.columns(2)
    dry_run = col1.checkbox("Mode test (dry run)", value=True)

    if col2.button("📤 Envoyer", type="primary", disabled=not message or not users):
        if dry_run:
            st.warning(f"**DRY RUN** — Aucun message envoye. {len(users)} destinataires.")
            st.text(message[:300])
        else:
            broadcast_id = run_async(database.create_broadcast(title="Dashboard Broadcast", message=message))
            wa = WhatsAppClient()

            recipients = [{"phone": u["phone"], "name": u.get("name") or ""} for u in users]
            with st.spinner(f"Envoi en cours a {len(recipients)} destinataires..."):
                results = run_async(wa.send_bulk(
                    recipients=recipients,
                    message_template=message,
                    broadcast_id=broadcast_id,
                ))

            run_async(database.update_broadcast_status(broadcast_id, "sent"))
            st.success(f"Envoyes: {results['sent']} | Echoues: {results['failed']}")

    # History
    st.divider()
    st.subheader("Historique")
    broadcasts = run_async(database.get_all_broadcasts())
    if broadcasts:
        for b in broadcasts[:10]:
            status_color = "green" if b["status"] == "sent" else "orange"
            st.markdown(f":{status_color}[{b['status']}] **{b['title']}** — {b['created_at'][:16]}")
    else:
        st.caption("Aucun broadcast envoye.")


# ── Templates Page ────────────────────────────────────────────

elif page == "📋 Templates":
    st.title("📋 Templates de messages")

    templates = run_async(database.get_all_templates())

    # Create new
    with st.expander("➕ Creer un template"):
        name = st.text_input("Nom du template")
        category = st.selectbox("Categorie", ["general", "onboarding", "broadcast", "info"])
        body = st.text_area("Contenu", height=150)
        if st.button("Creer") and name and body:
            run_async(database.create_template(name, category, body))
            st.success(f"Template '{name}' cree !")
            st.rerun()

    # List existing
    for t in templates:
        with st.expander(f"📄 {t['name']} [{t['category']}]"):
            st.text(t["body"])
            if st.button(f"Supprimer {t['name']}", key=f"del_{t['name']}"):
                run_async(database.delete_template(t["name"]))
                st.success(f"Template '{t['name']}' supprime.")
                st.rerun()


# ── Statistics Page ───────────────────────────────────────────

elif page == "📊 Statistiques":
    st.title("📊 Statistiques & Rapports")

    msg_stats = run_async(database.get_message_stats())

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Messages sortants")
        outbound_data = {
            "Envoyes": msg_stats.get("sent", 0),
            "Livres": msg_stats.get("delivered", 0),
            "Lus": msg_stats.get("read", 0),
            "Echoues": msg_stats.get("failed", 0),
            "En attente": msg_stats.get("queued", 0),
        }
        df_out = pd.DataFrame({"Status": list(outbound_data.keys()), "Count": list(outbound_data.values())})
        st.bar_chart(df_out.set_index("Status"))

    with col2:
        st.subheader("Vue d'ensemble")
        total_out = sum(outbound_data.values())
        total_in = msg_stats.get("inbound", 0)
        overview = pd.DataFrame({
            "Direction": ["Sortants", "Entrants"],
            "Count": [total_out, total_in],
        })
        st.bar_chart(overview.set_index("Direction"))

    # Broadcast stats
    st.divider()
    st.subheader("Broadcasts")
    broadcasts = run_async(database.get_all_broadcasts())
    if broadcasts:
        for b in broadcasts[:5]:
            stats = run_async(database.get_broadcast_stats(b["id"]))
            total = sum(stats.values())
            delivered = stats.get("delivered", 0) + stats.get("read", 0)
            rate = (delivered / total * 100) if total > 0 else 0
            st.markdown(f"**{b['title']}** — {b['created_at'][:10]} — Taux: {rate:.0f}%")
    else:
        st.caption("Aucun broadcast.")


# ── Test Message Page ─────────────────────────────────────────

elif page == "💬 Test Message":
    st.title("💬 Tester l'envoi WhatsApp")

    phone = st.text_input("Numero (format international)", placeholder="+33612345678")
    message = st.text_area("Message", placeholder="Bonjour depuis SoClose Community Bot !")

    if st.button("Envoyer", type="primary", disabled=not phone or not message):
        wa = WhatsAppClient()
        with st.spinner("Envoi..."):
            result = run_async(wa.send_message(phone, message))
        if result["status"] == "sent":
            st.success(f"Message envoye ! SID: {result.get('sid', 'N/A')}")
        else:
            st.error(f"Echec: {result.get('error', 'Unknown')}")


# ── Configuration Page ────────────────────────────────────────

elif page == "⚙️ Configuration":
    st.title("⚙️ Configuration")

    warnings = config.validate()
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success("Configuration OK !")

    st.subheader("Parametres actuels")
    st.json({
        "Bot": config.BOT_NAME,
        "Version": config.BOT_VERSION,
        "Provider": config.WA_PROVIDER,
        "GitHub Org": config.GITHUB_ORG,
        "Webhook Port": config.WEBHOOK_PORT,
        "Rate Limit": f"{config.WA_MESSAGES_PER_SECOND} msg/s",
        "Database": config.DB_PATH,
        "Telegram Admins": len(config.TELEGRAM_ADMIN_IDS),
    })

    st.divider()
    st.subheader("Test de connexion")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔗 Test GitHub API"):
            with st.spinner("Test..."):
                repos = run_async(github_api.sync_projects())
            if repos:
                st.success(f"GitHub OK — {len(repos)} repos trouves")
            else:
                st.error("Echec connexion GitHub")

    with col2:
        if st.button("📡 Test WhatsApp"):
            wa = WhatsAppClient()
            st.info(f"Provider: {wa.provider} — Configure et pret")
