"""
WhatsApp Bulk Sender — Interactive CLI
Colored terminal interface for importing contacts, composing messages,
and sending WhatsApp messages in bulk.
"""

from __future__ import annotations

import asyncio
import glob
import sys

import database
import csv_handler
from whatsapp import WhatsAppClient, _render_message
import config

# -- ANSI Colors -----------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"

wa_client = WhatsAppClient()


# -- UI Helpers ------------------------------------------------

def safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def banner():
    print(f"""
{CYAN}{BOLD}
  ╔════════════════════════════════════════════╗
  ║   WhatsApp Bulk Sender — v{config.BOT_VERSION}          ║
  ║     by SoClose Society                     ║
  ╚════════════════════════════════════════════╝
{RESET}""")


def menu():
    print(f"""
{BOLD}Menu Principal{RESET}
{DIM}─────────────────────────────{RESET}
  {GREEN}1{RESET}  📥  Importer des contacts (CSV)
  {GREEN}2{RESET}  👥  Voir les contacts
  {GREEN}3{RESET}  📢  Envoyer des messages
  {GREEN}4{RESET}  📊  Statistiques
  {GREEN}5{RESET}  📋  Templates
  {GREEN}6{RESET}  📨  Historique des envois
  {GREEN}7{RESET}  💬  Tester un message
  {GREEN}8{RESET}  🗑   Supprimer tous les contacts
  {GREEN}0{RESET}  🚪  Quitter
{DIM}─────────────────────────────{RESET}""")


def pick(options: list[str], prompt: str = "Choix") -> int | None:
    """Show numbered options, return selected index or None for cancel."""
    for i, opt in enumerate(options, 1):
        print(f"  {GREEN}{i}{RESET}  {opt}")
    print(f"  {DIM}0{RESET}  Retour")

    choice = safe_input(f"\n  {BOLD}{prompt}:{RESET} ").strip()
    if not choice or choice == "0":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    print(f"  {RED}Choix invalide.{RESET}")
    return None


def progress_bar(current: int, total: int, status: str = ""):
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
    color = GREEN if status == "sent" else RED
    sys.stdout.write(f"\r  {bar} {current}/{total} {color}{status}{RESET}")
    sys.stdout.flush()
    if current == total:
        print()


# -- Commands --------------------------------------------------

async def cmd_import():
    """Import contacts from a CSV file."""
    print(f"\n{BOLD}📥 Importer des contacts{RESET}\n")

    # Scan for CSV files in current directory
    csv_files = sorted(glob.glob("*.csv"))
    if not csv_files:
        print(f"  {YELLOW}Aucun fichier CSV trouve dans le repertoire courant.{RESET}")
        print(f"  {DIM}Place un fichier .csv ici et relance l'import.{RESET}\n")
        return

    print(f"  Fichiers CSV trouves:\n")
    idx = pick(csv_files, "Choisir un fichier")
    if idx is None:
        return

    csv_path = csv_files[idx]
    print(f"\n  {YELLOW}Lecture de {csv_path}...{RESET}")

    with open(csv_path, "rb") as f:
        content = f.read()

    contacts, errors = csv_handler.parse_csv(content)

    if errors:
        print(f"\n  {YELLOW}⚠ {len(errors)} avertissement(s):{RESET}")
        for err in errors[:5]:
            print(f"    {DIM}{err}{RESET}")
        if len(errors) > 5:
            print(f"    {DIM}... et {len(errors) - 5} de plus{RESET}")

    if not contacts:
        print(f"\n  {RED}Aucun contact valide trouve.{RESET}\n")
        return

    print(f"\n  {GREEN}✅ {len(contacts)} contacts valides trouves{RESET}")
    print(f"\n  {DIM}Apercu (3 premiers):{RESET}")
    for c in contacts[:3]:
        print(f"    {c['first_name']} {c['last_name']} — {CYAN}{c['phone']}{RESET}")

    # Create a campaign for this import
    campaign_name = safe_input(f"\n  {BOLD}Nom de la campagne:{RESET} ").strip()
    if not campaign_name:
        campaign_name = f"Import {csv_path}"

    # Save to database
    print(f"\n  {YELLOW}Enregistrement...{RESET}")
    contact_ids = []
    for c in contacts:
        cid = await database.upsert_contact(
            first_name=c["first_name"],
            last_name=c["last_name"],
            phone=c["phone"],
            email=c.get("email", ""),
        )
        contact_ids.append(cid)

    # Create campaign and link contacts
    campaign_id = await database.create_campaign(name=campaign_name, message="")
    await database.add_contacts_to_campaign(campaign_id, contact_ids)

    print(f"  {GREEN}✅ {len(contacts)} contacts importes dans la campagne '{campaign_name}'{RESET}")
    print(f"  {DIM}ID campagne: {campaign_id}{RESET}\n")


async def cmd_contacts():
    """Display all contacts."""
    contacts = await database.get_all_contacts()
    if not contacts:
        print(f"\n  {YELLOW}Aucun contact. Utilise l'option 1 pour importer un CSV.{RESET}\n")
        return

    print(f"\n{BOLD}👥 Contacts ({len(contacts)}){RESET}")
    print(f"{DIM}{'─' * 65}{RESET}")
    print(f"  {'#':<5} {'Prenom':<15} {'Nom':<15} {'Telephone':<20} {'Email'}")
    print(f"{DIM}{'─' * 65}{RESET}")

    for i, c in enumerate(contacts[:50], 1):
        fn = (c.get("first_name") or "")[:13]
        ln = (c.get("last_name") or "")[:13]
        print(f"  {i:<5} {fn:<15} {ln:<15} {CYAN}{c['phone']:<20}{RESET} {c.get('email', '')}")

    if len(contacts) > 50:
        print(f"\n  {DIM}... et {len(contacts) - 50} de plus{RESET}")
    print()


async def cmd_send():
    """Send messages to a campaign's contacts."""
    print(f"\n{BOLD}📢 Envoyer des messages{RESET}\n")

    campaigns = await database.get_all_campaigns()
    if not campaigns:
        print(f"  {YELLOW}Aucune campagne. Importe d'abord des contacts.{RESET}\n")
        return

    # Select campaign
    options = [
        f"{c['name']} — {c['contact_count']} contacts [{c['status']}]"
        for c in campaigns
    ]
    idx = pick(options, "Choisir une campagne")
    if idx is None:
        return

    campaign = campaigns[idx]
    contacts = await database.get_contacts_for_campaign(campaign["id"])

    if not contacts:
        print(f"\n  {YELLOW}Aucun contact dans cette campagne.{RESET}\n")
        return

    print(f"\n  Campagne: {BOLD}{campaign['name']}{RESET}")
    print(f"  Contacts: {CYAN}{len(contacts)}{RESET}")

    # Select or compose message
    print(f"\n  {BOLD}Message:{RESET}")
    print(f"  {DIM}Placeholders: {{first_name}}, {{last_name}}, {{phone}}, {{name}}{RESET}")

    # Offer templates
    templates = await database.get_all_templates()
    if templates:
        print(f"\n  {BOLD}Templates disponibles:{RESET}")
        tpl_idx = pick(
            [f"{t['name']} [{t['category']}]" for t in templates] + ["Ecrire un message personnalise"],
            "Template"
        )
        if tpl_idx is None:
            return

        if tpl_idx < len(templates):
            message = templates[tpl_idx]["body"]
            print(f"\n  {DIM}Template charge.{RESET}")
        else:
            message = safe_input(f"\n  Message: ").strip()
    else:
        message = safe_input(f"\n  Message: ").strip()

    if not message:
        print(f"  {RED}Annule.{RESET}\n")
        return

    # Preview
    sample = contacts[0]
    preview = _render_message(message, {
        "first_name": sample.get("first_name", "Contact"),
        "last_name": sample.get("last_name", ""),
        "phone": sample.get("phone", ""),
        "name": f"{sample.get('first_name', '')} {sample.get('last_name', '')}".strip(),
    })

    print(f"\n  {BOLD}Apercu:{RESET}")
    print(f"  {DIM}{'─' * 40}{RESET}")
    print(f"  {preview[:300]}")
    print(f"  {DIM}{'─' * 40}{RESET}")
    print(f"\n  Destinataires: {CYAN}{len(contacts)}{RESET}")
    print(f"  Provider: {CYAN}{config.WA_PROVIDER.upper()}{RESET}")

    # Dry run option
    dry = safe_input(f"\n  Mode test (dry run) ? (oui/non) [{GREEN}non{RESET}]: ").strip().lower()
    dry_run = dry in ("oui", "o", "yes", "y")

    if not dry_run:
        confirm = safe_input(f"  Confirmer l'envoi a {len(contacts)} contacts ? (oui/non): ").strip().lower()
        if confirm not in ("oui", "o", "yes", "y"):
            print(f"  {RED}Annule.{RESET}\n")
            return

    # Save message and update campaign
    campaign_id = campaign["id"]
    await database.update_campaign_message(campaign_id, message)
    await database.update_campaign_status(campaign_id, "sending")

    if dry_run:
        print(f"\n  {YELLOW}🧪 DRY RUN — Aucun message envoye{RESET}")
        print(f"  {len(contacts)} messages auraient ete envoyes.\n")
        for c in contacts[:2]:
            body = _render_message(message, {
                "first_name": c.get("first_name", "Contact"),
                "last_name": c.get("last_name", ""),
                "phone": c.get("phone", ""),
                "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
            })
            print(f"  → {c['phone']}: {body[:100]}")
        await database.update_campaign_status(campaign_id, "draft")
        print()
        return

    # Send
    print(f"\n  {YELLOW}📤 Envoi en cours...{RESET}\n")

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
        on_progress=lambda cur, tot, st: progress_bar(cur, tot, st),
    )

    await database.update_campaign_status(campaign_id, "sent")
    print(f"\n  {GREEN}✅ Termine !{RESET}")
    print(f"  Envoyes: {GREEN}{results['sent']}{RESET} | Echoues: {RED}{results['failed']}{RESET}\n")


async def cmd_stats():
    """Show sending statistics."""
    stats = await database.get_send_stats()
    contact_count = await database.get_contact_count()
    campaigns = await database.get_all_campaigns()

    print(f"""
{BOLD}📊 Statistiques{RESET}
{DIM}─────────────────────────────{RESET}
  👥 Contacts:     {CYAN}{contact_count}{RESET}
  📢 Campagnes:    {CYAN}{len(campaigns)}{RESET}
  📨 Total envois: {CYAN}{stats.get('total', 0)}{RESET}

  {BOLD}Statuts{RESET}
  ⏳ En attente:   {YELLOW}{stats.get('queued', 0)}{RESET}
  ✅ Envoyes:      {GREEN}{stats.get('sent', 0)}{RESET}
  📬 Livres:       {GREEN}{stats.get('delivered', 0)}{RESET}
  👁  Lus:          {BLUE}{stats.get('read', 0)}{RESET}
  ❌ Echoues:      {RED}{stats.get('failed', 0)}{RESET}
""")


async def cmd_templates():
    """Manage message templates."""
    templates = await database.get_all_templates()

    print(f"\n{BOLD}📋 Templates ({len(templates)}){RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")

    for t in templates:
        print(f"  {MAGENTA}{t['name']}{RESET} [{t['category']}]")
        body_preview = t["body"].replace("\n", " ")[:70]
        ellipsis = "..." if len(t["body"]) > 70 else ""
        print(f"  {DIM}{body_preview}{ellipsis}{RESET}\n")

    print(f"  {BOLD}Actions:{RESET}")
    action = pick(["Creer un template", "Supprimer un template", "Retour"], "Action")

    if action == 0:
        name = safe_input(f"\n  Nom: ").strip()
        category = safe_input(f"  Categorie (general/broadcast/info): ").strip() or "general"
        print(f"  Corps du message (ligne vide pour terminer):")
        lines = []
        while True:
            line = safe_input("  > ")
            if line == "":
                break
            lines.append(line)
        body = "\n".join(lines)
        if name and body:
            await database.create_template(name, category, body)
            print(f"\n  {GREEN}✅ Template '{name}' cree !{RESET}\n")
        else:
            print(f"  {RED}Annule.{RESET}\n")

    elif action == 1:
        if not templates:
            print(f"  {YELLOW}Aucun template.{RESET}\n")
            return
        idx = pick([t["name"] for t in templates], "Supprimer")
        if idx is not None:
            await database.delete_template(templates[idx]["name"])
            print(f"  {GREEN}✅ Template supprime.{RESET}\n")


async def cmd_history():
    """Show campaign history."""
    campaigns = await database.get_all_campaigns()
    if not campaigns:
        print(f"\n  {YELLOW}Aucune campagne.{RESET}\n")
        return

    print(f"\n{BOLD}📨 Historique des campagnes ({len(campaigns)}){RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")

    for c in campaigns[:15]:
        status_color = GREEN if c["status"] == "sent" else YELLOW
        status_emoji = {"draft": "📝", "sent": "✅", "sending": "📤"}.get(c["status"], "⏳")
        count = c.get("contact_count", 0)
        print(f"  {status_emoji} {BOLD}{c['name']}{RESET} — {status_color}{c['status']}{RESET} — {count} contacts — {c['created_at'][:16]}")

        if c["status"] == "sent":
            stats = await database.get_campaign_stats(c["id"])
            sent = stats.get("sent", 0) + stats.get("delivered", 0) + stats.get("read", 0)
            failed = stats.get("failed", 0)
            print(f"    {DIM}Resultats: {sent} envoyes, {failed} echoues{RESET}")
        print()


async def cmd_test():
    """Test sending a single message."""
    print(f"\n{BOLD}💬 Tester un message WhatsApp{RESET}")
    phone = safe_input(f"  Numero (ex: +33612345678): ").strip()
    if not phone:
        print(f"  {RED}Annule.{RESET}\n")
        return

    message = safe_input(f"  Message: ").strip()
    if not message:
        print(f"  {RED}Annule.{RESET}\n")
        return

    print(f"  {YELLOW}Envoi en cours...{RESET}")
    result = await wa_client.send_message(phone, message)

    if result["status"] == "sent":
        print(f"  {GREEN}✅ Message envoye ! SID: {result.get('sid', 'N/A')}{RESET}\n")
    else:
        print(f"  {RED}❌ Echec: {result.get('error', 'Unknown')}{RESET}\n")


async def cmd_delete_contacts():
    """Delete all contacts."""
    count = await database.get_contact_count()
    if count == 0:
        print(f"\n  {YELLOW}Aucun contact a supprimer.{RESET}\n")
        return

    confirm = safe_input(f"\n  Supprimer les {RED}{count}{RESET} contacts ? (oui/non): ").strip().lower()
    if confirm in ("oui", "o", "yes", "y"):
        deleted = await database.delete_all_contacts()
        print(f"  {GREEN}✅ {deleted} contacts supprimes.{RESET}\n")
    else:
        print(f"  {RED}Annule.{RESET}\n")


# -- Main Loop -------------------------------------------------

async def run_cli():
    """Main CLI loop."""
    await database.init()
    banner()

    while True:
        menu()
        choice = safe_input(f"  {BOLD}Choix:{RESET} ").strip()

        if choice == "1":
            await cmd_import()
        elif choice == "2":
            await cmd_contacts()
        elif choice == "3":
            await cmd_send()
        elif choice == "4":
            await cmd_stats()
        elif choice == "5":
            await cmd_templates()
        elif choice == "6":
            await cmd_history()
        elif choice == "7":
            await cmd_test()
        elif choice == "8":
            await cmd_delete_contacts()
        elif choice == "0":
            print(f"\n  {CYAN}Au revoir ! 👋{RESET}\n")
            break
        else:
            print(f"\n  {RED}Option invalide.{RESET}")
