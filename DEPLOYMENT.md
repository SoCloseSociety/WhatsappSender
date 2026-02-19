# Guide de Deploiement — WhatsApp Bulk Sender

<p align="center">
  <em>By <a href="https://github.com/SoCloseSociety">SoClose Society</a> — <a href="https://soclose.co">soclose.co</a></em>
</p>

Ce guide couvre le deploiement en production sur un VPS ou avec Docker.

---

## Option 1 : VPS (Ubuntu/Debian)

### Pre-requis serveur

- Ubuntu 22.04+ ou Debian 12+
- Python 3.11+
- Un nom de domaine pointe vers le serveur
- Ports 80, 443 ouverts

### 1.1 Installation

```bash
# Mise a jour du systeme
sudo apt update && sudo apt upgrade -y

# Installer Python et outils
sudo apt install python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx -y

# Creer un utilisateur dedie
sudo useradd -m -s /bin/bash wasender
sudo su - wasender

# Cloner le projet
git clone https://github.com/SoCloseSociety/WhatsappSender.git
cd WhatsappSender

# Environnement virtuel
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
nano .env  # Remplir les identifiants
```

### 1.2 Certificat SSL (Let's Encrypt)

```bash
sudo certbot --nginx -d bot.votre-domaine.com
```

### 1.3 Configuration Nginx

```bash
sudo nano /etc/nginx/sites-available/wa-sender
```

```nginx
server {
    listen 443 ssl;
    server_name bot.votre-domaine.com;

    ssl_certificate /etc/letsencrypt/live/bot.votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.votre-domaine.com/privkey.pem;

    # Webhook API (FastAPI)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Dashboard Streamlit (optionnel)
    location /dashboard/ {
        proxy_pass http://127.0.0.1:8501/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}

server {
    listen 80;
    server_name bot.votre-domaine.com;
    return 301 https://$server_name$request_uri;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/wa-sender /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 1.4 Service systemd

```bash
sudo nano /etc/systemd/system/wa-sender.service
```

```ini
[Unit]
Description=WhatsApp Bulk Sender
After=network.target

[Service]
Type=simple
User=wasender
WorkingDirectory=/home/wasender/WhatsappSender
Environment=PATH=/home/wasender/WhatsappSender/venv/bin:/usr/bin
ExecStart=/home/wasender/WhatsappSender/venv/bin/python main.py --telegram
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wa-sender
sudo systemctl start wa-sender
```

### 1.5 Dashboard Streamlit (optionnel)

```bash
sudo nano /etc/systemd/system/wa-dashboard.service
```

```ini
[Unit]
Description=WhatsApp Bulk Sender Dashboard
After=network.target

[Service]
Type=simple
User=wasender
WorkingDirectory=/home/wasender/WhatsappSender
Environment=PATH=/home/wasender/WhatsappSender/venv/bin:/usr/bin
ExecStart=/home/wasender/WhatsappSender/venv/bin/streamlit run dashboard.py --server.port 8501 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wa-dashboard
sudo systemctl start wa-dashboard
```

### 1.6 Verification

```bash
# Verifier les services
sudo systemctl status wa-sender
sudo systemctl status wa-dashboard

# Health check
curl https://bot.votre-domaine.com/health

# Logs
sudo journalctl -u wa-sender -f
```

---

## Option 2 : Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["python", "main.py", "--telegram"]
```

### Lancer avec Docker

```bash
# Build
docker build -t wa-sender .

# Run (mode Telegram + Webhook)
docker run -d \
  --name wa-sender \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  wa-sender

# Run Dashboard
docker run -d \
  --name wa-dashboard \
  --env-file .env \
  -p 8501:8501 \
  --restart unless-stopped \
  wa-sender \
  streamlit run dashboard.py --server.port 8501 --server.headless true
```

### Docker Compose

```yaml
version: '3.8'

services:
  bot:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    command: python main.py --telegram

  dashboard:
    build: .
    env_file: .env
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    command: streamlit run dashboard.py --server.port 8501 --server.headless true
```

```bash
docker compose up -d
```

---

## Commandes utiles en production

```bash
# Redemarrer le bot
sudo systemctl restart wa-sender

# Voir les logs en temps reel
sudo journalctl -u wa-sender -f

# Mise a jour du code
cd /home/wasender/WhatsappSender
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart wa-sender

# Backup de la base de donnees
cp whatsapp_sender.db whatsapp_sender.db.bak

# Verifier la sante
curl -s https://bot.votre-domaine.com/health | python3 -m json.tool
```

---

## Securite

- **Ne jamais commiter le fichier `.env`** — il contient les secrets
- **Restreindre les admin Telegram** — `TELEGRAM_ADMIN_IDS`
- **Sauvegarder la DB regulierement** — `whatsapp_sender.db`
- **SSL/TLS obligatoire** — Meta et Twilio l'exigent pour les webhooks
- **Ne pas exposer le port 8000** directement — toujours passer par Nginx
- **Definir un `DASHBOARD_PASSWORD`** — si le dashboard est expose

---

## Configuration des webhooks apres deploiement

### Pour Twilio
1. Console Twilio > Messaging > WhatsApp Sandbox Settings
2. **Status callback URL** : `https://bot.votre-domaine.com/twilio-status`

### Pour Meta
1. Meta Developers > WhatsApp > Configuration
2. **Callback URL** : `https://bot.votre-domaine.com/webhook`
3. **Verify Token** : valeur de `WA_VERIFY_TOKEN` dans `.env`
4. S'abonner aux champs : `messages`

---

## Prochaines etapes

- [SETUP_GUIDE.md](SETUP_GUIDE.md) — Configuration des providers
- [README.md](README.md) — Documentation complete

---

<p align="center">
  <em><a href="https://github.com/SoCloseSociety">SoClose Society</a> — <a href="https://soclose.co">soclose.co</a> — <a href="mailto:hello@soclose.co">hello@soclose.co</a></em>
</p>
