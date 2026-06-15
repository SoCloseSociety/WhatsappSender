# NEO_CONNECTOR -- WhatsApp Bulk Sender
- service: whatsappsender
- base_url_prod: UNKNOWN -- no public URL declared (DEPLOYMENT.md nginx proxies 127.0.0.1:8000; README docs http://localhost:8000). Not deployed to a named soclose.co host in repo.
- auth: none on the FastAPI server itself. The Meta webhook (GET /webhook) verifies a `hub.verify_token` query param against env `WA_VERIFY_TOKEN`; POST endpoints are unauthenticated (no HMAC signature check found).
- env_required: [WA_PROVIDER, WA_VERIFY_TOKEN, WEBHOOK_HOST, WEBHOOK_PORT, DB_PATH] -- (sending creds, NOT for the HTTP API: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN, WA_API_VERSION; control: TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS, DASHBOARD_PASSWORD, DASHBOARD_PORT)
- generated_at:

> IMPORTANT FOR NEO: This project has NO outbound action API. The HTTP surface is a
> FastAPI server (webhook.py) whose endpoints are INBOUND callbacks consumed BY Meta/Twilio
> (delivery-status receipts) plus health/root. There is NO HTTP endpoint to trigger a send,
> create a campaign, import contacts, or read data. Bulk sending and all operations are
> driven only via the local CLI (`cli.py`), the Streamlit dashboard (`dashboard.py`), and the
> Telegram bot (`telegram_bot.py`) -- none of which expose callable HTTP routes.
> => Do NOT wire this repo as Neo HTTP tools. The only thing Neo could do over HTTP is poll
> GET /health. To control sends, Neo would talk to its Telegram bot, not an API.

## Endpoints

All endpoints live in `webhook.py` (FastAPI app, mounted on uvicorn at WEBHOOK_HOST:WEBHOOK_PORT, default 0.0.0.0:8000).

### GET /webhook
- auth: yes -- Meta challenge-response. Succeeds only if `hub.mode=subscribe` AND `hub.verify_token` (hmac.compare_digest) equals env `WA_VERIFY_TOKEN`.
- async: false
- input:
  | param | type | required | description |
  |-------|------|----------|-------------|
  | hub.mode | query str | yes | must be "subscribe" |
  | hub.verify_token | query str | yes | must match WA_VERIFY_TOKEN |
  | hub.challenge | query str | yes | echoed back on success |
- output: text/plain body = the `hub.challenge` value (200) on success.
- errors: 403 if mode != subscribe or token mismatch or WA_VERIFY_TOKEN unset.
- example_curl: `curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=$WA_VERIFY_TOKEN&hub.challenge=12345"`
- note: This is Meta's webhook handshake, NOT a Neo-callable action.

### POST /webhook
- auth: no -- no signature/token verification on the POST body (potential gap, see Gaps).
- async: false
- input: raw JSON body in Meta Cloud API webhook shape. Read path: `entry[].changes[].value.statuses[]`, each with `id` (str) and `status` (str). Only statuses in {queued, sent, delivered, read, failed} are applied via `database.update_message_status(id, status)`; others logged + ignored.
- output: `{"status": "ok"}` always (also `{"status":"error"}` if JSON parse fails).
- errors: none returned as HTTP error codes (returns 200 with status field on bad JSON).
- example_curl: `curl -X POST http://localhost:8000/webhook -H 'Content-Type: application/json' -d '{"entry":[{"changes":[{"value":{"statuses":[{"id":"wamid.X","status":"delivered"}]}}]}]}'`
- note: Inbound delivery receipt from Meta. NOT a Neo action.

### POST /twilio-status
- auth: no -- no Twilio signature (X-Twilio-Signature) validation found.
- async: false
- input: `application/x-www-form-urlencoded` form. Fields read: `MessageSid` (str), `MessageStatus` (str). Twilio status mapped: undelivered/failed -> "failed"; queued/sent/delivered/read pass through.
- output: `{"status": "ok"}`.
- errors: none (always 200).
- example_curl: `curl -X POST http://localhost:8000/twilio-status -d 'MessageSid=SMxxxx&MessageStatus=delivered'`
- note: Inbound Twilio delivery callback. NOT a Neo action.

### GET /health
- auth: no
- async: false
- input: none
- output: `{"status":"ok","bot":"WhatsApp Bulk Sender","version":"1.0.0","provider":<WA_PROVIDER>}`
- errors: none
- example_curl: `curl http://localhost:8000/health`
- note: The ONLY endpoint useful to Neo (liveness/provider probe).

### GET /
- auth: no
- async: false
- input: none
- output: `{"name":...,"version":...,"endpoints":{"health":"/health","webhook_meta":"/webhook","twilio_status":"/twilio-status","docs":"/docs"}}`
- errors: none
- example_curl: `curl http://localhost:8000/`

(FastAPI also auto-serves GET /docs and /openapi.json -- standard Swagger, not application logic.)

## Flows

No request/response action flow exists for a caller. The only multi-party flow is inbound,
driven by external providers (Neo is NOT a participant):
1. WhatsApp send happens via CLI / dashboard / Telegram bot -> message logged in SQLite with `wa_message_id` (sid).
2. Meta/Twilio later POST a delivery receipt to /webhook or /twilio-status.
3. `database.update_message_status(sid, status)` updates the row -> dashboard/Telegram report reflects it.

To actually send/control from Neo there is no HTTP path; the control interfaces are:
- Telegram bot (`telegram_bot.py`, admin-only via TELEGRAM_ADMIN_IDS) -- Neo could relay commands here.
- CLI (`cli.py`) and Streamlit dashboard (`dashboard.py`, optional DASHBOARD_PASSWORD) -- local/human only.

## Gaps
- base_url_prod UNKNOWN -- verify deployed host; nothing in README/DEPLOYMENT/config names a public domain (DEPLOYMENT.md only shows generic nginx -> 127.0.0.1:8000). Check infra/DNS outside this repo.
- POST /webhook and POST /twilio-status have NO inbound auth -- no Meta app-secret HMAC (X-Hub-Signature-256) and no Twilio X-Twilio-Signature validation in webhook.py. Anyone reaching the port can spoof delivery statuses. Verify whether an upstream proxy enforces this.
- No send/campaign/contact/report HTTP API by design -- confirm with owner whether one is wanted before Neo expects programmatic sending over HTTP.

## Recap
- Endpoints found: 5 application routes (GET/POST /webhook, POST /twilio-status, GET /health, GET /) + 2 framework (/docs, /openapi.json).
- Neo-callable as action tools: 0 (all are inbound provider callbacks or liveness probes).
- Already covered in bot/integrations.py: 0. New to wire: 0 -- this service must NOT be wired as Neo HTTP tools (no outbound action API). At most, register GET /health as a monitoring probe if/when a base URL is known.
