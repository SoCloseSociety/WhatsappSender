<p align="center">
  <img src="https://github.com/SoCloseSociety.png" width="120" alt="SoClose Society — Digital Innovation Through Automation & AI">
</p>

<h1 align="center">SoClose Community Bot</h1>

<p align="center">
  <strong>WhatsApp bot open-source pour la communaute SoClose Society</strong><br>
  Accede a tous nos projets, bots et outils d'automatisation directement depuis WhatsApp.<br>
  <em>Digital Innovation Through Automation & AI</em>
</p>

<p align="center">
  <a href="https://github.com/SoCloseSociety/WhatsappSender/stargazers"><img src="https://img.shields.io/github/stars/SoCloseSociety/WhatsappSender?style=for-the-badge&color=gold" alt="Stars"></a>
  <a href="https://github.com/SoCloseSociety/WhatsappSender/network/members"><img src="https://img.shields.io/github/forks/SoCloseSociety/WhatsappSender?style=for-the-badge&color=blue" alt="Forks"></a>
  <a href="https://github.com/SoCloseSociety/WhatsappSender/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SoCloseSociety/WhatsappSender?style=for-the-badge&color=green" alt="License"></a>
  <a href="https://github.com/SoCloseSociety"><img src="https://img.shields.io/badge/Community-SoClose_Society-purple?style=for-the-badge" alt="Community"></a>
</p>

<p align="center">
  <a href="#-fonctionnalites">Fonctionnalites</a> •
  <a href="#-installation-rapide">Installation</a> •
  <a href="#-modes-de-lancement">Lancement</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-nos-projets">Projets</a> •
  <a href="#-deploiement">Deploiement</a>
</p>

---

## Qu'est-ce que c'est ?

**SoClose Community Bot** est un bot WhatsApp qui donne acces a l'ensemble de l'ecosysteme open-source de [SoClose Society](https://github.com/SoCloseSociety). Les utilisateurs peuvent decouvrir, rechercher et obtenir des informations sur tous les projets directement dans WhatsApp.

Le bot propose aussi un **dashboard web** (Streamlit), une **CLI interactive** et un **bot Telegram** pour l'administration.

## Fonctionnalites

| Fonctionnalite | Description |
|---|---|
| **Auto-reply WhatsApp** | Repond automatiquement aux messages : menu, projets, recherche, aide |
| **Catalogue GitHub** | Synchronise et affiche tous les repos SoCloseSociety en temps reel |
| **Broadcast** | Envoie des messages a tous les abonnes avec tracking de livraison |
| **Dashboard Web** | Interface Streamlit pour la gestion complete (stats, users, projets) |
| **CLI Interactive** | Terminal colore pour tests locaux et envoi de messages |
| **Bot Telegram** | Administration a distance via Telegram (stats, sync, broadcast) |
| **Multi-Provider** | Supporte Twilio et Meta Cloud API pour WhatsApp |
| **Templates** | Systeme de templates reutilisables avec placeholders |
| **Rate Limiting** | Controle du debit d'envoi (configurable) |
| **Delivery Tracking** | Suivi des statuts de livraison (sent/delivered/read/failed) |
| **Base de donnees** | SQLite async pour utilisateurs, messages, projets, broadcasts |

## Installation rapide

### Pre-requis

- Python 3.11+
- Un compte [Twilio](https://www.twilio.com/) ou [Meta Developer](https://developers.facebook.com/)

### Setup

```bash
# 1. Cloner le repo
git clone https://github.com/SoCloseSociety/WhatsappSender.git
cd WhatsappSender

# 2. Creer l'environnement virtuel
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows

# 3. Installer les dependances
pip install -r requirements.txt

# 4. Configurer l'environnement
cp .env.example .env
# Editer .env avec vos identifiants (Twilio/Meta, Telegram, etc.)
```

> Voir le [SETUP_GUIDE.md](SETUP_GUIDE.md) pour la configuration detaillee de chaque provider.

## Modes de lancement

### CLI (defaut) — Tests locaux

```bash
python main.py
```

Interface interactive avec menu colore : stats, projets, broadcast, test message.

### Dashboard Web — Streamlit

```bash
python main.py --dashboard
```

Ouvre un dashboard complet sur `http://localhost:8501` avec :
- KPIs et statistiques
- Gestion des projets et utilisateurs
- Envoi de broadcasts avec preview
- Templates et configuration

### Telegram + Webhook — Production

```bash
python main.py --telegram
```

Lance simultanement :
- Le bot Telegram pour l'administration
- Le serveur webhook FastAPI pour les messages WhatsApp entrants
- Auto-reply intelligent avec catalogue de projets

### Webhook seul

```bash
python main.py --webhook
```

API FastAPI sur le port 8000 avec documentation Swagger auto-generee sur `/docs`.

## Architecture

```
Interfaces
├── CLI (cli.py)                    Tests locaux, menu interactif
├── Telegram Bot (telegram_bot.py)  Administration a distance
├── Dashboard (dashboard.py)        Interface web Streamlit
└── Webhook (webhook.py)            Reception WhatsApp + auto-reply

Core
├── WhatsApp Client (whatsapp.py)   Multi-provider (Twilio/Meta)
├── Database (database.py)          SQLite async (users, messages, projets)
├── GitHub API (github_api.py)      Sync repos + formatage
└── Config (config.py)              Variables d'environnement

Entry Point
└── main.py                         Routeur CLI/Telegram/Dashboard/Webhook
```

### Schema de la base de donnees

| Table | Description |
|---|---|
| `users` | Utilisateurs WhatsApp (phone, name, subscribed, langue) |
| `projects` | Repos GitHub caches (name, description, stars, category) |
| `broadcasts` | Campagnes de broadcast (title, message, status) |
| `message_log` | Historique complet (direction, status, provider_sid) |
| `templates` | Templates de messages reutilisables |

## Nos projets

Le bot donne acces a l'ensemble de l'ecosysteme SoClose Society :

### Bots d'automatisation
| Projet | Description |
|---|---|
| [BoosterBot](https://github.com/SoCloseSociety/BoosterBot) | Bot Telegram Follow-For-Follow pour Instagram |
| [PinterestBulkPostBot](https://github.com/SoCloseSociety/PinterestBulkPostBot) | Upload en masse sur Pinterest |
| [BOT-Facebook_Bulk_Invite](https://github.com/SoCloseSociety/BOT-Facebook_Bulk_Invite_Friend_To_FB_Group) | Invitation automatique de groupe Facebook |
| [BOT-Facebook_MP_Bulk](https://github.com/SoCloseSociety/BOT-Facebook_MP_Bulk) | Messages prives Facebook en masse |
| [BOT-Instagram_MP_Bulk](https://github.com/SoCloseSociety/BOT-Instagram_MP_Bulk) | Messages prives Instagram en masse |
| [Twitter_Bulk_Message](https://github.com/SoCloseSociety/Twitter_Bulk_Message_Sender) | Envoi de messages Twitter en masse |

### Scrapers
| Projet | Description |
|---|---|
| [BOT_GoogleMap_Scrapping](https://github.com/SoCloseSociety/BOT_GoogleMap_Scrapping) | Scraping Google Maps |
| [BOT-PagesJaunes_Scrapping](https://github.com/SoCloseSociety/BOT-PagesJaunes_Scrapping) | Scraping PagesJaunes |
| [BOT-Instagram_Scrapping](https://github.com/SoCloseSociety/BOT-Instagram_Scrapping) | Scraping profils Instagram |
| [BOT-Doctorlib_Scrapping](https://github.com/SoCloseSociety/BOT-Doctorlib_Scrapping) | Scraping Doctolib |
| [LinkedinDataScraper](https://github.com/SoCloseSociety/LinkedinDataScraper) | Scraping contacts LinkedIn |
| [FreeWorkDataScraper](https://github.com/SoCloseSociety/FreeWorkDataScraper) | Scraping offres FreeWork |
| [Twitter_Profile_Scrapper](https://github.com/SoCloseSociety/Twitter_Profile_Scrapper) | Scraping profils Twitter |

## Commandes WhatsApp

Les utilisateurs peuvent interagir avec le bot via ces commandes :

| Commande | Action |
|---|---|
| `menu` / `bonjour` / `hi` | Affiche le menu interactif |
| `projets` / `list` | Liste tous les projets |
| `bots` | Filtre les bots d'automatisation |
| `scrapers` | Filtre les outils de scraping |
| `aide` / `help` | Message d'aide |
| `site` / `web` | Liens vers le site et GitHub |
| `stop` | Se desabonner des broadcasts |
| `start` | Se reabonner |
| `1`, `2`, `3`... | Detail d'un projet par numero |
| *(texte libre)* | Recherche dans les projets |

## Commandes Telegram (admin)

| Commande | Action |
|---|---|
| `/start` | Menu principal avec boutons |
| `/stats` | Statistiques globales |
| `/users` | Liste des utilisateurs |
| `/projects` | Projets GitHub |
| `/sync` | Synchroniser depuis GitHub |
| `/broadcast` | Envoyer un broadcast |
| `/templates` | Gerer les templates |

## Endpoints API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Info API |
| `GET` | `/health` | Health check |
| `GET` | `/webhook` | Verification Meta webhook |
| `POST` | `/webhook` | Reception messages Meta |
| `POST` | `/twilio-webhook` | Reception messages Twilio |
| `POST` | `/twilio-status` | Callbacks de livraison Twilio |
| `GET` | `/docs` | Documentation Swagger auto-generee |

## Deploiement

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour le guide complet de deploiement en production (VPS, Docker, Nginx, SSL).

## Configuration

Voir [SETUP_GUIDE.md](SETUP_GUIDE.md) pour la configuration detaillee des providers (Twilio, Meta, Telegram).

## Provider WhatsApp

| | Twilio | Meta Cloud API |
|---|---|---|
| **Difficulte** | Facile (5 min) | Moyen (15 min) |
| **Sandbox** | Oui (gratuit) | Non |
| **Templates** | Optionnel | Requis (hors 24h) |
| **Prix** | ~0.005$/msg + Twilio markup | ~0.005$/msg |
| **Interactive** | Non | Oui (listes, boutons) |

## Contribuer

1. Fork le repo
2. Cree une branche (`git checkout -b feature/ma-feature`)
3. Commit (`git commit -m "Add ma feature"`)
4. Push (`git push origin feature/ma-feature`)
5. Ouvre une Pull Request

## Licence

[MIT](LICENSE) — SoClose Society 2024-2026

---

<p align="center">
  <strong>Built with ❤️ by <a href="https://github.com/SoCloseSociety">SoClose Society</a></strong><br>
  <a href="https://soclose.co">soclose.co</a> •
  <a href="https://github.com/SoCloseSociety">GitHub</a> •
  <a href="mailto:contact@soclose.co">contact@soclose.co</a>
</p>

<!-- SEO Keywords: whatsapp bot, whatsapp automation, open source whatsapp bot, python whatsapp bot, twilio whatsapp, meta cloud api, telegram bot admin, community bot, soclose society, bulk whatsapp sender, whatsapp broadcast, scraping tools, automation bots, social media automation, github community bot -->
