"""
SoClose Community Bot — Interactive CLI
Colored terminal interface for local testing and management.
"""

import asyncio
import sys

import database
import github_api
from whatsapp import WhatsAppClient
import config

# ── ANSI Colors ───────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

wa_client = WhatsAppClient()


def banner():
    print(f"""
{CYAN}{BOLD}
  ╔══════════════════════════════════════════════╗
  ║     SoClose Community Bot — CLI v{config.BOT_VERSION}     ║
  ║         github.com/SoCloseSociety            ║
  ╚══════════════════════════════════════════════╝
{RESET}""")


def menu():
    print(f"""
{BOLD}Menu Principal{RESET}
{DIM}─────────────────────────────{RESET}
  {GREEN}1{RESET}  📊  Statistiques
  {GREEN}2{RESET}  👥  Utilisateurs
  {GREEN}3{RESET}  📦  Projets GitHub
  {GREEN}4{RESET}  🔄  Sync GitHub
  {GREEN}5{RESET}  📢  Envoyer un broadcast
  {GREEN}6{RESET}  📋  Templates
  {GREEN}7{RESET}  💬  Tester un message WhatsApp
  {GREEN}8{RESET}  🔍  Rechercher un projet
  {GREEN}9{RESET}  📨  Historique des broadcasts
  {GREEN}0{RESET}  🚪  Quitter
{DIM}─────────────────────────────{RESET}""")


async def show_stats():
    user_count = await database.get_user_count()
    msg_stats = await database.get_message_stats()
    projects = await database.get_all_projects()

    print(f"""
{BOLD}📊 Statistiques{RESET}
{DIM}─────────────────────────────{RESET}
  👥 Utilisateurs:  {CYAN}{user_count}{RESET}
  📦 Projets:       {CYAN}{len(projects)}{RESET}

  {BOLD}Messages{RESET}
  ⏳ En attente:    {YELLOW}{msg_stats.get('queued', 0)}{RESET}
  ✅ Envoyes:       {GREEN}{msg_stats.get('sent', 0)}{RESET}
  📬 Livres:        {GREEN}{msg_stats.get('delivered', 0)}{RESET}
  👁  Lus:           {BLUE}{msg_stats.get('read', 0)}{RESET}
  ❌ Echoues:       {RED}{msg_stats.get('failed', 0)}{RESET}
  📥 Recus:         {MAGENTA}{msg_stats.get('inbound', 0)}{RESET}
""")


async def show_users():
    users = await database.get_all_users()
    if not users:
        print(f"\n  {YELLOW}Aucun utilisateur enregistre.{RESET}\n")
        return

    print(f"\n{BOLD}👥 Utilisateurs ({len(users)}){RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")
    print(f"  {'Status':<8} {'Telephone':<20} {'Nom':<20} {'Derniere visite'}")
    print(f"{DIM}{'─' * 60}{RESET}")

    for u in users[:50]:
        sub = f"{GREEN}✅{RESET}" if u.get("subscribed") else f"{RED}❌{RESET}"
        name = (u.get("name") or "Anonyme")[:18]
        last = (u.get("last_seen") or "")[:10]
        print(f"  {sub:<17} {u['phone']:<20} {name:<20} {last}")

    if len(users) > 50:
        print(f"\n  {DIM}... et {len(users) - 50} de plus{RESET}")
    print()


async def show_projects():
    projects = await database.get_all_projects()
    if not projects:
        print(f"\n  {YELLOW}Aucun projet. Lancez l'option 4 pour sync GitHub.{RESET}\n")
        return

    print(f"\n{BOLD}📦 Projets ({len(projects)}){RESET}")
    print(f"{DIM}{'─' * 70}{RESET}")

    for i, p in enumerate(projects, 1):
        emoji = {"bot": "🤖", "scraper": "🔍", "automation": "⚡", "template": "📄"}.get(
            p.get("category", ""), "🔧"
        )
        stars = f" ⭐{p['stars']}" if p.get("stars") else ""
        lang = p.get("language", "N/A")
        print(f"  {GREEN}{i:>2}{RESET}. {emoji} {BOLD}{github_api.friendly_name(p['name'])}{RESET}{stars} [{CYAN}{lang}{RESET}]")
        if p.get("description") and p["description"] != "No description":
            print(f"      {DIM}{p['description'][:65]}{RESET}")

    print()


async def sync_github():
    print(f"\n  {YELLOW}🔄 Synchronisation GitHub en cours...{RESET}")
    repos = await github_api.sync_projects()
    print(f"  {GREEN}✅ {len(repos)} projets synchronises depuis github.com/{config.GITHUB_ORG}{RESET}\n")


async def send_broadcast():
    users = await database.get_subscribed_users()
    print(f"\n{BOLD}📢 Nouveau Broadcast{RESET}")
    print(f"  Abonnes: {CYAN}{len(users)}{RESET}")

    if not users:
        print(f"  {YELLOW}Aucun abonne a contacter.{RESET}\n")
        return

    print(f"  Placeholders: {{name}}, {{phone}}")
    msg = input(f"\n  {BOLD}Message:{RESET} ").strip()
    if not msg:
        print(f"  {RED}Annule.{RESET}\n")
        return

    print(f"\n  {DIM}Apercu:{RESET} {msg[:200]}")
    print(f"  {DIM}Destinataires:{RESET} {len(users)}")
    confirm = input(f"\n  Confirmer ? (oui/non): ").strip().lower()

    if confirm not in ("oui", "o", "yes", "y"):
        print(f"  {RED}Annule.{RESET}\n")
        return

    broadcast_id = await database.create_broadcast(title="CLI Broadcast", message=msg)

    def on_progress(current, total, status):
        bar_len = 30
        filled = int(bar_len * current / total)
        bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
        color = GREEN if status == "sent" else RED
        sys.stdout.write(f"\r  {bar} {current}/{total} {color}{status}{RESET}")
        sys.stdout.flush()

    recipients = [{"phone": u["phone"], "name": u.get("name") or ""} for u in users]
    results = await wa_client.send_bulk(
        recipients=recipients,
        message_template=msg,
        broadcast_id=broadcast_id,
        on_progress=on_progress,
    )

    await database.update_broadcast_status(broadcast_id, "sent")
    print(f"\n\n  {GREEN}✅ Termine — Envoyes: {results['sent']} | Echoues: {results['failed']}{RESET}\n")


async def show_templates():
    templates = await database.get_all_templates()
    if not templates:
        print(f"\n  {YELLOW}Aucun template.{RESET}\n")
        return

    print(f"\n{BOLD}📋 Templates ({len(templates)}){RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")
    for t in templates:
        print(f"  {MAGENTA}{t['name']}{RESET} [{t['category']}]")
        body_preview = t['body'].replace('\n', ' ')[:70]
        print(f"  {DIM}{body_preview}...{RESET}\n")


async def test_message():
    print(f"\n{BOLD}💬 Tester un message WhatsApp{RESET}")
    phone = input(f"  Numero (ex: +33612345678): ").strip()
    if not phone:
        print(f"  {RED}Annule.{RESET}\n")
        return

    message = input(f"  Message: ").strip()
    if not message:
        print(f"  {RED}Annule.{RESET}\n")
        return

    print(f"  {YELLOW}Envoi en cours...{RESET}")
    result = await wa_client.send_message(phone, message)

    if result["status"] == "sent":
        print(f"  {GREEN}✅ Message envoye ! SID: {result.get('sid', 'N/A')}{RESET}\n")
    else:
        print(f"  {RED}❌ Echec: {result.get('error', 'Unknown')}{RESET}\n")


async def search_project():
    query = input(f"\n  {BOLD}🔍 Recherche:{RESET} ").strip()
    if not query:
        return

    results = await database.search_projects(query)
    if not results:
        print(f"  {YELLOW}Aucun resultat pour '{query}'.{RESET}\n")
        return

    print(f"\n  {GREEN}{len(results)} resultat(s) pour '{query}':{RESET}\n")
    for p in results:
        emoji = {"bot": "🤖", "scraper": "🔍", "automation": "⚡"}.get(p.get("category", ""), "🔧")
        print(f"  {emoji} {BOLD}{github_api.friendly_name(p['name'])}{RESET}")
        print(f"    {p.get('description', '')[:70]}")
        print(f"    {CYAN}{p.get('url', '')}{RESET}\n")


async def show_history():
    broadcasts = await database.get_all_broadcasts()
    if not broadcasts:
        print(f"\n  {YELLOW}Aucun historique.{RESET}\n")
        return

    print(f"\n{BOLD}📨 Historique des broadcasts ({len(broadcasts)}){RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")

    for b in broadcasts[:15]:
        status_color = GREEN if b["status"] == "sent" else YELLOW
        status_emoji = {"draft": "📝", "sent": "✅"}.get(b["status"], "⏳")
        print(f"  {status_emoji} {BOLD}{b['title']}{RESET} — {status_color}{b['status']}{RESET} — {b['created_at'][:16]}")
        print(f"    {DIM}{b['message'][:60]}...{RESET}\n")


async def run_cli():
    """Main CLI loop."""
    await database.init()
    banner()

    # Initial sync
    projects = await database.get_all_projects()
    if not projects:
        print(f"  {YELLOW}Premier lancement — synchronisation GitHub...{RESET}")
        await sync_github()

    while True:
        menu()
        choice = input(f"  {BOLD}Choix:{RESET} ").strip()

        if choice == "1":
            await show_stats()
        elif choice == "2":
            await show_users()
        elif choice == "3":
            await show_projects()
        elif choice == "4":
            await sync_github()
        elif choice == "5":
            await send_broadcast()
        elif choice == "6":
            await show_templates()
        elif choice == "7":
            await test_message()
        elif choice == "8":
            await search_project()
        elif choice == "9":
            await show_history()
        elif choice == "0":
            print(f"\n  {CYAN}Au revoir ! 👋{RESET}\n")
            break
        else:
            print(f"\n  {RED}Option invalide.{RESET}")
