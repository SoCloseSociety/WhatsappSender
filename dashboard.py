"""
WhatsApp Bulk Sender — Streamlit Web Dashboard
Web interface for importing contacts, sending campaigns, and viewing stats.
"""

import asyncio
import hmac
import threading

import streamlit as st
import pandas as pd

import config
import database
import csv_handler
from whatsapp import WhatsAppClient, _render_message


# -- Async Bridge ----------------------------------------------

_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()


def run_async(coro):
    """Run an async coroutine from sync Streamlit context."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    try:
        return future.result(timeout=30)
    except TimeoutError:
        future.cancel()
        raise RuntimeError("Database operation timed out")


def init_db():
    if "db_init" not in st.session_state:
        run_async(database.init())
        st.session_state.db_init = True


# -- Page Config -----------------------------------------------

st.set_page_config(
    page_title=config.BOT_NAME,
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Authentication Gate ---------------------------------------

if config.DASHBOARD_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 WhatsApp Bulk Sender")
        st.markdown("Entrez le mot de passe pour acceder au dashboard.")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Connexion"):
            if hmac.compare_digest(password, config.DASHBOARD_PASSWORD):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.stop()

init_db()


# -- Sidebar ---------------------------------------------------

with st.sidebar:
    st.title("📱 WhatsApp Sender")
    st.caption(f"v{config.BOT_VERSION} | {config.WA_PROVIDER.upper()}")

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "📥 Import CSV",
            "📢 Envoyer",
            "👥 Contacts",
            "📊 Statistiques",
            "📋 Templates",
            "💬 Test Message",
            "⚙️ Configuration",
        ],
    )

    st.divider()
    st.markdown(f"[GitHub]({config.COMMUNITY_URL}) | [Site]({config.WEBSITE_URL})")


# -- Dashboard Page --------------------------------------------

if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")

    contact_count = run_async(database.get_contact_count())
    campaigns = run_async(database.get_all_campaigns())
    stats = run_async(database.get_send_stats())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Contacts", contact_count)
    col2.metric("Campagnes", len(campaigns))
    col3.metric("Messages envoyes", stats.get("sent", 0) + stats.get("delivered", 0))
    col4.metric("Echoues", stats.get("failed", 0))

    total_out = sum(stats.get(s, 0) for s in ("sent", "delivered", "read", "failed"))
    delivered = stats.get("delivered", 0) + stats.get("read", 0)
    rate = (delivered / total_out * 100) if total_out > 0 else 0

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Taux livraison", f"{rate:.1f}%")
    col6.metric("Livres", stats.get("delivered", 0))
    col7.metric("Lus", stats.get("read", 0))
    col8.metric("Total", stats.get("total", 0))

    # Recent campaigns
    st.divider()
    st.subheader("Campagnes recentes")
    if campaigns:
        for c in campaigns[:5]:
            status_emoji = {"draft": "📝", "sent": "✅", "sending": "📤"}.get(c["status"], "⏳")
            st.markdown(f"{status_emoji} **{c['name']}** — {c.get('contact_count', 0)} contacts — {c['created_at'][:16]}")
    else:
        st.caption("Aucune campagne.")


# -- Import CSV Page -------------------------------------------

elif page == "📥 Import CSV":
    st.title("📥 Importer des contacts")

    uploaded = st.file_uploader("Choisir un fichier CSV", type=["csv"])
    campaign_name = st.text_input("Nom de la campagne", placeholder="Ma campagne")

    if uploaded and campaign_name:
        if st.button("📥 Importer", type="primary"):
            content = uploaded.read()
            contacts, errors = csv_handler.parse_csv(content)

            if errors:
                with st.expander(f"⚠ {len(errors)} avertissements"):
                    for err in errors[:20]:
                        st.text(err)

            if contacts:
                with st.spinner(f"Import de {len(contacts)} contacts..."):
                    contact_ids = []
                    for c in contacts:
                        cid = run_async(database.upsert_contact(
                            first_name=c["first_name"],
                            last_name=c["last_name"],
                            phone=c["phone"],
                            email=c.get("email", ""),
                        ))
                        contact_ids.append(cid)

                    campaign_id = run_async(database.create_campaign(name=campaign_name, message=""))
                    run_async(database.add_contacts_to_campaign(campaign_id, contact_ids))

                st.success(f"{len(contacts)} contacts importes dans '{campaign_name}'")

                # Preview
                df = pd.DataFrame(contacts)
                st.dataframe(df.head(20), use_container_width=True)
            else:
                st.error("Aucun contact valide trouve.")

    st.divider()
    st.subheader("Format CSV attendu")
    st.code("phone,first_name,last_name,email\n+33612345678,Jean,Dupont,jean@email.com\n+33687654321,Marie,Martin,", language="csv")


# -- Send Page -------------------------------------------------

elif page == "📢 Envoyer":
    st.title("📢 Envoyer des messages")

    campaigns = run_async(database.get_all_campaigns())
    if not campaigns:
        st.warning("Aucune campagne. Importez d'abord des contacts.")
        st.stop()

    # Select campaign
    campaign_options = {
        f"{c['name']} ({c.get('contact_count', 0)} contacts) [{c['status']}]": c["id"]
        for c in campaigns
    }
    selected = st.selectbox("Campagne", list(campaign_options.keys()))
    campaign_id = campaign_options[selected]

    contacts = run_async(database.get_contacts_for_campaign(campaign_id))
    st.info(f"**{len(contacts)}** contacts dans cette campagne.")

    # Template selector
    templates = run_async(database.get_all_templates())
    template_names = ["(Ecrire un message)"] + [t["name"] for t in templates]
    selected_tpl = st.selectbox("Template", template_names)

    default_msg = ""
    if selected_tpl != "(Ecrire un message)":
        tpl = next((t for t in templates if t["name"] == selected_tpl), None)
        if tpl:
            default_msg = tpl["body"]

    message = st.text_area(
        "Message",
        value=default_msg,
        height=200,
        help="Placeholders: {first_name}, {last_name}, {phone}, {name}",
    )

    if message and contacts:
        sample = contacts[0]
        preview = _render_message(message, {
            "first_name": sample.get("first_name", "Contact"),
            "last_name": sample.get("last_name", ""),
            "phone": sample.get("phone", ""),
            "name": f"{sample.get('first_name', '')} {sample.get('last_name', '')}".strip(),
        })
        st.markdown("**Apercu:**")
        st.text(preview)

    col1, col2 = st.columns(2)
    dry_run = col1.checkbox("Mode test (dry run)", value=True)

    if col2.button("📤 Envoyer", type="primary", disabled=not message or not contacts):
        if dry_run:
            st.warning(f"**DRY RUN** — Aucun message envoye. {len(contacts)} destinataires.")
        else:
            run_async(database.update_campaign_message(campaign_id, message))
            wa = WhatsAppClient()
            recipients = [
                {
                    "phone": c["phone"],
                    "first_name": c.get("first_name", "Contact"),
                    "last_name": c.get("last_name", ""),
                    "id": c.get("id"),
                }
                for c in contacts
            ]

            progress = st.progress(0)
            status_text = st.empty()

            sent = 0
            failed = 0
            for i, r in enumerate(recipients):
                body = _render_message(message, {
                    "first_name": r.get("first_name", "Contact"),
                    "last_name": r.get("last_name", ""),
                    "phone": r.get("phone", ""),
                    "name": f"{r.get('first_name', '')} {r.get('last_name', '')}".strip(),
                })
                result = run_async(wa.send_message(r["phone"], body))
                run_async(database.log_message(
                    phone=r["phone"],
                    content=body[:500],
                    status=result["status"],
                    campaign_id=campaign_id,
                    contact_id=r.get("id"),
                    wa_message_id=result.get("sid", ""),
                    error_message=result.get("error", ""),
                ))
                if result["status"] == "sent":
                    sent += 1
                else:
                    failed += 1
                progress.progress((i + 1) / len(recipients))
                status_text.text(f"Envoi: {i + 1}/{len(recipients)} — Envoyes: {sent} | Echoues: {failed}")

            run_async(database.update_campaign_status(campaign_id, "sent"))
            st.success(f"Termine ! Envoyes: {sent} | Echoues: {failed}")


# -- Contacts Page ---------------------------------------------

elif page == "👥 Contacts":
    st.title("👥 Contacts")

    contacts = run_async(database.get_all_contacts())

    if not contacts:
        st.info("Aucun contact. Importez un CSV pour commencer.")
    else:
        st.metric("Total contacts", len(contacts))
        df = pd.DataFrame(contacts)
        display_cols = [c for c in ["phone", "first_name", "last_name", "email", "created_at"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)


# -- Statistics Page -------------------------------------------

elif page == "📊 Statistiques":
    st.title("📊 Statistiques")

    stats = run_async(database.get_send_stats())

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Messages par statut")
        data = {
            "Envoyes": stats.get("sent", 0),
            "Livres": stats.get("delivered", 0),
            "Lus": stats.get("read", 0),
            "Echoues": stats.get("failed", 0),
            "En attente": stats.get("queued", 0),
        }
        df = pd.DataFrame({"Status": list(data.keys()), "Count": list(data.values())})
        st.bar_chart(df.set_index("Status"))

    with col2:
        st.subheader("Campagnes")
        campaigns = run_async(database.get_all_campaigns())
        if campaigns:
            for c in campaigns[:5]:
                camp_stats = run_async(database.get_campaign_stats(c["id"]))
                total = sum(camp_stats.values())
                delivered = camp_stats.get("delivered", 0) + camp_stats.get("read", 0)
                rate = (delivered / total * 100) if total > 0 else 0
                st.markdown(f"**{c['name']}** — {c['created_at'][:10]} — Taux: {rate:.0f}%")
        else:
            st.caption("Aucune campagne.")

    # Recent messages
    st.divider()
    st.subheader("Messages recents")
    messages = run_async(database.get_recent_messages(20))
    if messages:
        df_msg = pd.DataFrame(messages)
        display_cols = [c for c in ["phone", "status", "content", "sent_at"] if c in df_msg.columns]
        st.dataframe(df_msg[display_cols], use_container_width=True)
    else:
        st.caption("Aucun message.")


# -- Templates Page --------------------------------------------

elif page == "📋 Templates":
    st.title("📋 Templates de messages")

    templates = run_async(database.get_all_templates())

    with st.expander("➕ Creer un template"):
        name = st.text_input("Nom du template")
        category = st.selectbox("Categorie", ["general", "broadcast", "info"])
        body = st.text_area("Contenu", height=150, help="Placeholders: {first_name}, {last_name}, {phone}")
        if st.button("Creer") and name and body:
            run_async(database.create_template(name, category, body))
            st.success(f"Template '{name}' cree !")
            st.rerun()

    for t in templates:
        with st.expander(f"📄 {t['name']} [{t['category']}]"):
            st.text(t["body"])
            if st.button(f"Supprimer {t['name']}", key=f"del_{t['name']}"):
                run_async(database.delete_template(t["name"]))
                st.success(f"Template '{t['name']}' supprime.")
                st.rerun()


# -- Test Message Page -----------------------------------------

elif page == "💬 Test Message":
    st.title("💬 Tester l'envoi WhatsApp")

    phone = st.text_input("Numero (format international)", placeholder="+33612345678")
    message = st.text_area("Message", placeholder="Bonjour ! Test depuis WhatsApp Bulk Sender.")

    if st.button("Envoyer", type="primary", disabled=not phone or not message):
        wa = WhatsAppClient()
        with st.spinner("Envoi..."):
            result = run_async(wa.send_message(phone, message))
        if result["status"] == "sent":
            st.success(f"Message envoye ! SID: {result.get('sid', 'N/A')}")
        else:
            st.error(f"Echec: {result.get('error', 'Unknown')}")


# -- Configuration Page ----------------------------------------

elif page == "⚙️ Configuration":
    st.title("⚙️ Configuration")

    warnings = config.validate()
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success("Configuration OK !")

    st.json({
        "Bot": config.BOT_NAME,
        "Version": config.BOT_VERSION,
        "Provider": config.WA_PROVIDER,
        "Webhook Port": config.WEBHOOK_PORT,
        "Rate Limit": f"{config.WA_MESSAGES_PER_SECOND} msg/s",
        "Database": config.DB_PATH,
    })
