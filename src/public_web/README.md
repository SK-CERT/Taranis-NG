# public-web — Taranis-NG public vulnerability report feed

A public, human-readable web feed of vulnerability reports (homepage list,
per-report page, RSS, feedback form, localization, custom branding).

It is a **web-only** build: instead of reading report JSON files from disk, it
fetches report data **live from the Taranis-NG API**. The reporting/processing
half of the original app (Sner, Warden, IDEA-message generation) is intentionally
omitted.

## How it gets data

public-web is a Taranis-NG **node**: it authenticates to core with the shared
node ApiKey (`Authorization: ApiKey …`), exactly like the collector/presenter/
publisher/bot nodes. `lib/web/taranis_client.py`:

1. Lists published products — `GET /api/v1/public-web/products`.
2. Fetches each product — `GET /api/v1/public-web/products/<id>`.

Core serializes each **published** product directly from its database (no
presenter involved): product info plus report items, each with a flat list of
attributes (`{"key", "value", "description"}`). Unpublished/unknown products
come back as 404 and are skipped; products that are not valid TLP:CLEAR
vulnerability reports are skipped by the web. Results are cached
(`lib/web/cache.py`) with a TTL. The node is managed under core's Configuration
(seeded automatically from `api_key.txt` by `prestart_core.sh`).

## Configuration

There is **no config file**. Per-web presentation (branding text per language,
feed sizes, languages, images) is configured entirely in the Taranis GUI
(Configuration → Public Web) and fetched from core. Built-in fallback defaults in
`lib/config_reader.py` apply only to fields a web leaves unset, or while core is
unreachable; the per-language interface strings live in `conf/i18n/<lang>.json`.

- The node ApiKey comes from the shared Docker secret `api_key` (same
  `api_key.txt` as the other nodes), or the `PUBLIC_WEB_API_KEY` env var.
- Operational settings are environment variables:
  - `TARANIS_NG_CORE_URL` (default `http://core`) — core API base URL.
  - `PUBLIC_WEB_CACHE_TTL` (default `5400`) — cache lifetime in seconds.
  - `PUBLIC_WEB_MAX_REPORTS` — products to fetch (default: max of homepage/RSS limits).
  - `PUBLIC_WEB_DEFAULT_LANGUAGE` (default `en`).
  - `PUBLIC_WEB_MAIL_ADMINS` — fallback feedback/error mail recipients.
  - `PUBLIC_WEB_PRODUCTION` (default `true`) — set `false` to disable outgoing mail.
  - `PUBLIC_WEB_LOG_DIR` (default `/tmp/public-web-logs`).

## Running on a separate machine

public-web can run on a different host from core — you just point it *at* core,
not the other way around. This is why the public-web node has **no URL field** in
the GUI, unlike collectors/presenters/publishers/bots:

- Those are **worker nodes that core connects to**, so core stores each one's
  `api_url` and dials it (e.g. `CollectorsApi(node.api_url, …)`). To run one
  remotely you register it in the GUI with its own reachable URL.
- public-web is the **opposite** (like the *Remote Access* node type): it dials
  *out* to core's `/api/v1/public-web/*` using its ApiKey. Core never initiates a
  connection back, so it needs nothing about public-web's location. (Core still
  knows it's alive — public-web updates the node's `last_seen` on every call.)

To run public-web on another machine:

1. Set `TARANIS_NG_CORE_URL` to core's reachable **public** API URL — the host
   Traefik serves `/api/` on, e.g. `https://taranis.example.org` (not the
   internal `http://core`).
2. Provide the shared node **ApiKey**: mount the same `api_key` Docker secret, or
   set `PUBLIC_WEB_API_KEY` (it must match the value registered on the
   public-web node in core).
3. Set each web's **`hostname`** (in the GUI) and the DNS/TLS for the machine that
   actually serves it, so absolute RSS/OG links and `Host` routing are correct.

No firewall rule from core to public-web is needed — only outbound reachability
from public-web to core's API.

## Development (live reload, no image rebuild)

This is a plain Flask app, so the `npm run dev` equivalent is Flask's
auto-reloading debug server. Every dev knob is an env var:

| Env var | Purpose |
|---|---|
| `PUBLIC_WEB_PRODUCTION=false` | Dev mode — no outgoing e-mail, debug server |
| `TARANIS_NG_CORE_URL` | Base URL of a reachable Taranis core |
| `PUBLIC_WEB_API_KEY` | Node ApiKey (skips the Docker secret) — must match the registered node |

### Option A — on the host (no Docker)

```sh
cd src/public_web
python3 -m venv .venv && . .venv/bin/activate
pip install .            # or: pip install -e .

export PUBLIC_WEB_PRODUCTION=false
export PUBLIC_WEB_API_KEY=<the-shared-node-api-key>   # contents of docker/secrets/api_key.txt
export TARANIS_NG_CORE_URL=https://<your-taranis-host>   # or an exposed core, e.g. http://localhost:8080
flask --app run:app run --port 5001 --debug
```

Open http://localhost:5001/. Editing any `.py` (reloader restart) or Jinja
template (per-request auto-reload) is picked up immediately.

Reaching core from the host: the compose stack only exposes core through
Traefik, so use the public URL (`https://<taranis-host>`), or temporarily publish
core's port for dev (add `ports: ["127.0.0.1:8080:80"]` to the `core` service and
set `TARANIS_NG_CORE_URL=http://localhost:8080`).

### Option B — in the container (uses the compose network, reaches `http://core`)

Bind-mounts the source and runs the debug server; no rebuild on edits:

```sh
cd docker
docker compose -f docker-compose.yml -f docker-compose.public-web-dev.yml up public-web
```

Open http://localhost:5001/ (see `docker-compose.public-web-dev.yml`).
