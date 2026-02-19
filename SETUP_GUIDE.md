# Guide de Configuration — WhatsApp Bulk Sender

<p align="center">
  <em>By <a href="https://github.com/SoCloseSociety">SoClose Society</a> — <a href="https://soclose.co">soclose.co</a></em>
</p>

Ce guide explique pas a pas comment configurer les differents services necessaires.

---

## Vue d'ensemble

| Service | Requis | Temps de setup |
|---|---|---|
| **Twilio** OU **Meta Cloud API** | Oui (1 des 2) | 5-15 min |
| Bot Telegram | Optionnel (admin a distance) | 3 min |
| Dashboard Password | Optionnel (securite web) | 1 min |

---

## Etape 1 : Bot Telegram (optionnel)

Le bot Telegram sert d'interface d'administration a distance pour importer des contacts et lancer des campagnes depuis votre telephone.

### 1.1 Creer le bot

1. Ouvrez Telegram et cherchez `@BotFather`
2. Envoyez `/newbot`
3. Choisissez un nom : `WhatsApp Sender Admin`
4. Choisissez un username : `wa_sender_admin_bot` (doit finir par `_bot`)
5. Copiez le **token** : `123456789:ABCdef...`

### 1.2 Trouver votre ID admin

1. Cherchez `@userinfobot` sur Telegram
2. Envoyez `/start`
3. Copiez votre **ID numerique** : `123456789`

### 1.3 Configuration .env

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_ADMIN_IDS=123456789
```

> Pour plusieurs admins : `TELEGRAM_ADMIN_IDS=123456789,987654321`

---

## Etape 2A : Configuration Twilio (recommande pour debuter)

Twilio est le moyen le plus rapide de demarrer avec un sandbox WhatsApp gratuit.

### 2A.1 Creer un compte

1. Allez sur [twilio.com](https://www.twilio.com/)
2. Creez un compte gratuit (credit de test inclus)
3. Validez votre numero de telephone

### 2A.2 Recuperer les identifiants

1. Allez dans la [Console Twilio](https://console.twilio.com/)
2. Copiez :
   - **Account SID** : `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token** : `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2A.3 Activer WhatsApp Sandbox

1. Allez dans **Messaging > Try it out > Send a WhatsApp message**
2. Suivez les instructions pour rejoindre le sandbox
3. Notez le numero sandbox : `whatsapp:+14155238886`

### 2A.4 Configurer les webhooks Twilio

Pour recevoir les statuts de livraison (delivery tracking) :

1. Dans la console Twilio : **Messaging > Settings > WhatsApp Sandbox Settings**
2. Configurez :
   - **Status callback URL** : `https://votre-domaine.com/twilio-status` (POST)

### 2A.5 Configuration .env

```env
WA_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

---

## Etape 2B : Configuration Meta Cloud API

Meta Cloud API est recommande pour la production et les comptes WhatsApp Business verifies.

### 2B.1 Pre-requis

- Un compte Facebook
- Un compte [Meta Business Suite](https://business.facebook.com/)
- Un numero de telephone non associe a WhatsApp

### 2B.2 Creer l'application

1. Allez sur [developers.facebook.com](https://developers.facebook.com/)
2. **Mes applications > Creer une application**
3. Type : **Business**
4. Ajoutez le produit **WhatsApp**
5. Connectez a votre compte Business

### 2B.3 Configurer WhatsApp

1. Dans **WhatsApp > Getting Started** :
   - Notez le **Phone Number ID**
   - Generez un **Access Token temporaire** (valide 24h)
2. Pour un token permanent :
   - Allez dans **System Users** de votre Business Manager
   - Creez un System User
   - Generez un token permanent avec la permission `whatsapp_business_messaging`

### 2B.4 Configurer le webhook Meta

1. Dans **WhatsApp > Configuration** :
   - **Callback URL** : `https://votre-domaine.com/webhook`
   - **Verify Token** : la valeur de `WA_VERIFY_TOKEN` dans votre .env
2. Abonnez-vous aux champs : `messages`

### 2B.5 Configuration .env

```env
WA_PROVIDER=meta
WA_PHONE_NUMBER_ID=123456789012345
WA_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxx
WA_API_VERSION=v21.0
WA_VERIFY_TOKEN=votre-token-de-verification
```

---

## Etape 3 : Verification de la configuration

```bash
# Lancer en mode CLI pour verifier
python main.py
```

Le programme affichera des **warnings** si des variables sont manquantes.

### Test rapide

1. Lancez le CLI : `python main.py`
2. Option `7` : Tester un message → envoyez a votre propre numero
3. Option `4` : Consultez les stats

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

- [DEPLOYMENT.md](DEPLOYMENT.md) — Deployer en production (VPS, Docker)
- [README.md](README.md) — Documentation complete

---

<p align="center">
  <em><a href="https://github.com/SoCloseSociety">SoClose Society</a> — <a href="https://soclose.co">soclose.co</a> — <a href="mailto:hello@soclose.co">hello@soclose.co</a></em>
</p>
