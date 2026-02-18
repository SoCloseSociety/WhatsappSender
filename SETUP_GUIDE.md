# Guide de Configuration — SoClose Community Bot

Ce guide explique pas a pas comment configurer les differents services necessaires.

---

## Vue d'ensemble

| Service | Requis | Temps |
|---|---|---|
| Twilio **OU** Meta Cloud API | Oui (1 des 2) | 5-15 min |
| Bot Telegram | Optionnel (admin) | 3 min |
| GitHub Token | Optionnel (rate limits) | 2 min |

---

## Etape 1 : Bot Telegram (optionnel)

Le bot Telegram sert d'interface d'administration a distance.

### 1.1 Creer le bot

1. Ouvre Telegram et cherche `@BotFather`
2. Envoie `/newbot`
3. Choisis un nom : `SoClose Community Admin`
4. Choisis un username : `soclose_admin_bot` (doit finir par `_bot`)
5. Copie le **token** : `123456789:ABCdef...`

### 1.2 Trouver ton ID admin

1. Cherche `@userinfobot` sur Telegram
2. Envoie `/start`
3. Copie ton **ID numerique** : `123456789`

### 1.3 Configuration .env

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_ADMIN_IDS=123456789
```

> Pour plusieurs admins : `TELEGRAM_ADMIN_IDS=123456789,987654321`

---

## Etape 2A : Configuration Twilio (recommande)

Twilio est le moyen le plus rapide de demarrer avec un sandbox WhatsApp.

### 2A.1 Creer un compte

1. Va sur [twilio.com](https://www.twilio.com/)
2. Cree un compte gratuit (credit de test inclus)
3. Valide ton numero de telephone

### 2A.2 Recuperer les identifiants

1. Va dans la [Console Twilio](https://console.twilio.com/)
2. Copie :
   - **Account SID** : `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token** : `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2A.3 Activer WhatsApp Sandbox

1. Va dans **Messaging > Try it out > Send a WhatsApp message**
2. Suis les instructions pour rejoindre le sandbox
3. Note le numero sandbox : `whatsapp:+14155238886`

### 2A.4 Configurer les webhooks Twilio

1. Dans la console Twilio, va dans **Messaging > Settings > WhatsApp Sandbox Settings**
2. Configure :
   - **When a message comes in** : `https://ton-domaine.com/twilio-webhook` (POST)
   - **Status callback URL** : `https://ton-domaine.com/twilio-status` (POST)

### 2A.5 Configuration .env

```env
WA_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

---

## Etape 2B : Configuration Meta Cloud API

Meta Cloud API offre les messages interactifs (listes, boutons) mais le setup est plus long.

### 2B.1 Pre-requis

- Un compte Facebook
- Un compte [Meta Business Suite](https://business.facebook.com/)
- Un numero de telephone non associe a WhatsApp

### 2B.2 Creer l'application

1. Va sur [developers.facebook.com](https://developers.facebook.com/)
2. **Mes applications > Creer une application**
3. Type : **Business**
4. Ajoute le produit **WhatsApp**
5. Connecte a ton compte Business

### 2B.3 Configurer WhatsApp

1. Dans **WhatsApp > Getting Started** :
   - Note le **Phone Number ID**
   - Genere un **Access Token temporaire** (valide 24h)
2. Pour un token permanent :
   - Va dans **System Users** de ton Business Manager
   - Cree un System User
   - Genere un token permanent avec les permissions `whatsapp_business_messaging`

### 2B.4 Configurer le webhook Meta

1. Dans **WhatsApp > Configuration** :
   - **Callback URL** : `https://ton-domaine.com/webhook`
   - **Verify Token** : la valeur de `WA_VERIFY_TOKEN` dans ton .env
2. Abonne-toi aux champs : `messages`, `messaging_postbacks`

### 2B.5 Configuration .env

```env
WA_PROVIDER=meta
WA_PHONE_NUMBER_ID=123456789012345
WA_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxx
WA_API_VERSION=v21.0
WA_VERIFY_TOKEN=soclose-verify-2024
```

---

## Etape 3 : GitHub Token (optionnel)

Un token GitHub augmente la limite d'API de 60 a 5000 requetes/heure.

### 3.1 Creer le token

1. Va sur [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token (classic)**
3. Permissions : `public_repo` seulement
4. Copie le token

### 3.2 Configuration .env

```env
GITHUB_ORG=SoCloseSociety
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Etape 4 : Verification de la configuration

```bash
# Lancer en mode CLI pour verifier
python main.py
```

Le bot affichera les **warnings** si des variables sont manquantes.

### Test rapide

1. Lance le CLI : `python main.py`
2. Option `4` : Synchroniser GitHub → doit afficher ~15 projets
3. Option `7` : Tester un message → envoie a ton numero
4. Option `1` : Voir les stats

---

## Comparatif des couts

| | Meta Cloud API | Twilio |
|---|---|---|
| Messages marketing | ~$0.05/msg (FR) | ~$0.05/msg + markup |
| Messages utilitaires | ~$0.02/msg | ~$0.02/msg + markup |
| Messages service (24h) | Gratuit | ~$0.005/msg |
| Sandbox | Non | Oui (gratuit) |

> Les prix varient selon le pays de destination. Voir [Meta pricing](https://developers.facebook.com/docs/whatsapp/pricing/) et [Twilio pricing](https://www.twilio.com/whatsapp/pricing).

---

## Prochaines etapes

- [DEPLOYMENT.md](DEPLOYMENT.md) — Deployer en production
- [README.md](README.md) — Documentation complete
