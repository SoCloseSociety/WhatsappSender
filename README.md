<p align="center">
  <img src="https://github.com/SoCloseSociety.png" width="120" alt="SoClose Society Logo">
</p>

<h1 align="center">WhatsApp Bulk Sender</h1>

<p align="center">
  <strong>Outil open-source d'envoi de messages WhatsApp en masse</strong><br>
  Importez vos contacts par CSV, personnalisez vos messages et envoyez en un clic.<br>
  <em>Multi-provider : Twilio & Meta Cloud API — CLI, Dashboard Web & Bot Telegram</em>
</p>

<p align="center">
  <a href="https://github.com/SoCloseSociety/WhatsappSender/stargazers"><img src="https://img.shields.io/github/stars/SoCloseSociety/WhatsappSender?style=for-the-badge&color=gold" alt="Stars"></a>
  <a href="https://github.com/SoCloseSociety/WhatsappSender/network/members"><img src="https://img.shields.io/github/forks/SoCloseSociety/WhatsappSender?style=for-the-badge&color=blue" alt="Forks"></a>
  <a href="https://github.com/SoCloseSociety/WhatsappSender/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SoCloseSociety/WhatsappSender?style=for-the-badge&color=green" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="WhatsApp">
</p>

<p align="center">
  <a href="#fonctionnalites">Fonctionnalites</a> &bull;
  <a href="#installation-rapide">Installation</a> &bull;
  <a href="#utilisation">Utilisation</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#configuration">Configuration</a> &bull;
  <a href="#deploiement">Deploiement</a> &bull;
  <a href="#contribuer">Contribuer</a>
</p>

---

## Qu'est-ce que c'est ?

**WhatsApp Bulk Sender** est un outil Python open-source pour envoyer des messages WhatsApp en masse a une liste de contacts. Il supporte **Twilio** et **Meta Cloud API** comme providers, offre 3 interfaces (CLI, Dashboard Web, Bot Telegram) et gere automatiquement le rate limiting, le suivi de livraison et les templates de messages.

**Cas d'usage :** Notifications clients, campagnes marketing, rappels, confirmations de commande, communications de masse pour associations, startups et PMEs.

## Fonctionnalites

| Fonctionnalite | Description |
|---|---|
| **Import CSV intelligent** | Importe depuis Shopify, Google Contacts ou n'importe quel CSV. Detection automatique des colonnes. |
| **Envoi en masse** | Envoi personnalise a des centaines de contacts avec suivi en temps reel |
| **Multi-Provider** | Twilio (sandbox gratuit) ou Meta Cloud API (business) |
| **Placeholders dynamiques** | Personnalisez avec `{first_name}`, `{last_name}`, `{phone}`, `{name}` |
| **Templates reutilisables** | Sauvegardez vos messages et reutilisez-les |
| **Gestion par campagnes** | Organisez vos envois, consultez l'historique et les stats |
| **Delivery Tracking** | Suivi automatique : sent → delivered → read → failed |
| **Rate Limiting** | Debit configurable pour respecter les limites des providers |
| **3 Interfaces** | CLI interactive, Dashboard Web (Streamlit), Bot Telegram |
| **Dry Run** | Testez vos campagnes sans envoyer de vrais messages |
| **Normalisation E.164** | Numeros normalises automatiquement (+33612345678) |
| **Base SQLite async** | WAL mode pour la concurrence, zero config |

## Installation rapide

### Pre-requis

- **Python 3.11+**
- Un compte [Twilio](https://www.twilio.com/) (sandbox gratuit) **ou** [Meta Developer](https://developers.facebook.com/) (business)

### Setup en 4 etapes

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
# Editer .env avec vos identifiants Twilio ou Meta
```

> **Guide detaille :** [SETUP_GUIDE.md](SETUP_GUIDE.md) — Configuration pas a pas de Twilio, Meta et Telegram

## Utilisation

### Mode CLI (defaut)

```bash
python main.py
```

```
  ╔════════════════════════════════════════════╗
  ║   WhatsApp Bulk Sender — v1.0.0           ║
  ║     by SoClose Society                    ║
  ╚════════════════════════════════════════════╝

  1  📥  Importer des contacts (CSV)
  2  👥  Voir les contacts
  3  📢  Envoyer des messages
  4  📊  Statistiques
  5  📋  Templates
  6  📨  Historique des envois
  7  💬  Tester un message
  8  🗑   Supprimer tous les contacts
  0  🚪  Quitter
```

**Workflow typique :**
1. Placez votre fichier `.csv` dans le repertoire du projet
2. Option `1` : Importez les contacts et creez une campagne
3. Option `3` : Choisissez la campagne, composez le message, confirmez
4. Option `4` : Consultez les stats de livraison

### Mode Dashboard Web (Streamlit)

```bash
python main.py --dashboard
```

Interface web complete sur `http://localhost:8501` avec :
- Import CSV par drag & drop
- Envoi avec apercu en temps reel
- Statistiques visuelles (graphiques)
- Gestion des templates et contacts
- Protection par mot de passe (optionnel)

### Mode Telegram Bot (administration a distance)

```bash
python main.py --telegram
```

Commandes Telegram :
| Commande | Description |
|---|---|
| `/start` | Menu principal avec boutons |
| `/import` | Importer un CSV (envoyer le fichier) |
| `/send` | Choisir une campagne et envoyer |
| `/stats` | Statistiques d'envoi |
| `/contacts` | Liste des contacts |
| `/templates` | Voir les templates |
| `/cancel` | Annuler l'operation en cours |

> Acces restreint aux IDs admin configures dans `.env`

### Mode Webhook seul

```bash
python main.py --webhook
```

Serveur FastAPI pour les callbacks de livraison. API docs sur `http://localhost:8000/docs`.

## Format CSV

Le fichier CSV doit contenir au minimum une colonne **phone**. Exemples :

```csv
phone,first_name,last_name,email
+33612345678,Jean,Dupont,jean@email.com
+33687654321,Marie,Martin,marie@email.com
0612345678,Pierre,Durand,
```

**Colonnes reconnues automatiquement :**

| Interne | Colonnes acceptees |
|---|---|
| `phone` | phone, telephone, tel, mobile, numero, billing phone, shipping phone |
| `first_name` | first_name, first name, firstname, prenom, billing first name |
| `last_name` | last_name, last name, lastname, nom, billing last name |
| `email` | email, e-mail, billing email |
| `name` | name, full_name, fullname (auto-split en first/last) |

> Compatible Shopify, WooCommerce, Google Contacts, Mailchimp et tout CSV standard.
> Les numeros sont normalises automatiquement en format E.164 (+33612345678).

## Architecture

```
WhatsappSender/
│
├── main.py                  # Point d'entree — routeur CLI/Telegram/Dashboard/Webhook
│
├── Interfaces
│   ├── cli.py               # CLI interactive — import, envoi, stats
│   ├── telegram_bot.py      # Bot Telegram — administration a distance
│   ├── dashboard.py         # Dashboard web Streamlit
│   └── webhook.py           # Serveur FastAPI — callbacks de livraison
│
├── Core
│   ├── whatsapp.py          # Client WhatsApp multi-provider (Twilio/Meta)
│   ├── csv_handler.py       # Import CSV & normalisation des numeros
│   ├── database.py          # Couche donnees SQLite async (WAL mode)
│   └── config.py            # Chargement des variables d'environnement
│
├── Config
│   ├── .env.example         # Template de configuration
│   ├── requirements.txt     # Dependances Python
│   └── .gitignore           # Fichiers exclus du repo
│
└── Docs
    ├── README.md             # Ce fichier
    ├── SETUP_GUIDE.md        # Guide de configuration detaille
    └── DEPLOYMENT.md         # Deploiement VPS / Docker
```

### Schema de la base de donnees

```
contacts ─────────┐
  id (PK)          │
  first_name       │
  last_name        ├── campaign_contacts ──── campaigns
  phone (UNIQUE)   │     campaign_id (FK)       id (PK)
  email            │     contact_id (FK)        name
  created_at       │                            message
                   │                            status
message_log ──────┘                            created_at
  id (PK)
  contact_id (FK → SET NULL)    templates
  campaign_id (FK)                id (PK)
  phone                           name (UNIQUE)
  content                         category
  status                          body
  wa_message_id                   created_at
  sent_at
```

## Configuration

### Comparatif des providers

| | Twilio | Meta Cloud API |
|---|---|---|
| **Difficulte** | Facile (5 min) | Moyen (15 min) |
| **Sandbox gratuit** | Oui | Non |
| **Prix (marketing)** | ~$0.05/msg + markup | ~$0.05/msg |
| **Prix (utilitaire)** | ~$0.02/msg + markup | ~$0.02/msg |
| **Recommande pour** | Tests & prototypage | Production & business |

### Variables d'environnement principales

```bash
# Provider WhatsApp (twilio ou meta)
WA_PROVIDER=twilio

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Meta Cloud API
WA_PHONE_NUMBER_ID=123456789012345
WA_ACCESS_TOKEN=your_access_token
WA_API_VERSION=v21.0

# Telegram Bot (optionnel)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_IDS=123456789

# Rate limiting
WA_MESSAGES_PER_SECOND=50

# Dashboard
DASHBOARD_PASSWORD=your_password
```

> **Configuration complete :** voir [.env.example](.env.example) et [SETUP_GUIDE.md](SETUP_GUIDE.md)

## Deploiement

Le projet peut etre deploye sur un VPS (Ubuntu/Debian) ou avec Docker.

```bash
# VPS — Service systemd
python main.py --telegram    # Bot Telegram + webhooks (production)

# Docker
docker build -t whatsapp-sender .
docker run -d --env-file .env -p 8000:8000 whatsapp-sender

# Docker Compose
docker compose up -d
```

> **Guide complet :** [DEPLOYMENT.md](DEPLOYMENT.md) — Nginx, SSL, systemd, Docker Compose

## Securite

- Le fichier `.env` contient les secrets — **ne jamais le commiter**
- Acces Telegram restreint aux `TELEGRAM_ADMIN_IDS`
- Dashboard protege par mot de passe (comparaison timing-safe)
- SQLite en mode WAL pour la concurrence
- Foreign keys actives pour l'integrite referentielle
- Rate limiting configurable pour respecter les limites API
- Template rendering securise contre l'injection

## Contribuer

Les contributions sont les bienvenues ! Que ce soit un bug fix, une nouvelle fonctionnalite ou une amelioration de la documentation.

1. **Fork** le repo
2. Cree une branche (`git checkout -b feature/ma-feature`)
3. **Commit** (`git commit -m "Add ma feature"`)
4. **Push** (`git push origin feature/ma-feature`)
5. Ouvre une **Pull Request**

### Idees de contributions

- Support de nouveaux providers (Vonage, MessageBird)
- Interface web React/Vue en remplacement de Streamlit
- Scheduling des campagnes (envoi differe)
- Support des media (images, documents, audio)
- Import depuis Google Sheets / API CRM

## Licence

[MIT](LICENSE) — Libre d'utilisation, modification et distribution.

---

<p align="center">
  <strong>Developpe par <a href="https://github.com/SoCloseSociety">SoClose Society</a></strong><br>
  <em>Digital Innovation Through Automation & AI</em><br><br>
  <a href="https://soclose.co">soclose.co</a> &bull;
  <a href="https://github.com/SoCloseSociety">GitHub</a> &bull;
  <a href="mailto:hello@soclose.co">hello@soclose.co</a>
</p>

<p align="center">
  <a href="https://soclose.co"><img src="https://img.shields.io/badge/SoClose-Agency-575ECF?style=flat-square" alt="SoClose Agency"></a>
  <a href="https://github.com/SoCloseSociety"><img src="https://img.shields.io/badge/SoClose-Society-1b1b1b?style=flat-square" alt="SoClose Society"></a>
</p>

<!-- SEO Keywords -->
<!-- whatsapp bulk sender, whatsapp mass message, bulk whatsapp python, python whatsapp sender, twilio whatsapp sender, meta cloud api whatsapp, csv whatsapp sender, whatsapp broadcast tool, whatsapp marketing tool, send bulk whatsapp messages, whatsapp automation python, open source whatsapp sender, whatsapp campaign manager, envoi whatsapp en masse, outil whatsapp bulk, soclose society, soclose.co, whatsapp api python, whatsapp bulk messaging, mass whatsapp sender free, whatsapp sender bot, bulk message whatsapp, whatsapp business api python, python whatsapp bot, telegram whatsapp admin bot -->
