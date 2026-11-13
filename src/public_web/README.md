# public-web — Taranis-NG public report feed

A public, human-readable web feed of published products (homepage list,
per-report page, RSS, feedback form, localization, custom branding). Products are
rendered through report templates, so any kind of product can be shown; out of the
box it shows vulnerability reports.

It is a **web-only** build: instead of reading report JSON files from disk, it
fetches report data **live from the Taranis-NG API**. The reporting/processing
half of the original app (Sner, Warden, IDEA-message generation) is intentionally
omitted.

## How it gets data

public-web is a Taranis-NG **node**: it authenticates to core with the shared
node ApiKey (`Authorization: ApiKey …`), exactly like the collector/presenter/
publisher/bot nodes. `lib/web/taranis_client.py`:

1. Lists published products — `GET /api/v1/public-web/products?web_id=…`.
2. Fetches each product in the page's language — `GET /api/v1/public-web/products/<id>?web_id=…&lang=…`.
3. Fetches the custom report templates — `GET /api/v1/public-web/templates`.

Core serializes each **published** product directly from its database (no
presenter involved): product info (with its product preset and its sources,
`links`) plus report items, each with a flat list of attributes (`{"key",
"value", "description", "label", "group", "attribute_type", "multiple",
"order"}`). Link citations arrive already numbered (`[1]`, `[2]`…, indexing
`links`), so public-web never renumbers them. Unpublished/unknown products, and
products whose product preset does not show them on the web, come back as 404 and
are skipped.
With `lang` (the visitor's page language), core shows the product in that language
where it is translated into it; what is not stays as written, with no English in
between. It says which language the product and each report item are shown in
(`language`); a report item's labels and choice constants follow its own language,
a constant arriving as its translation (`value`) with the constant itself in
`source_value`.
Results and templates are cached (`lib/web/cache.py`) with a TTL; core pushes a
cache reset when a web, a template or a published product changes, and an administrator
can clear it on demand with the cache button on the node in Configuration -> Public web
(`POST /api/v1/config/public-web-nodes/<id>/reset-cache`, which waits for the node's
answer). The node is
managed under core's Configuration (seeded automatically from `api_key.txt` by
`prestart_core.sh`).

## Which products a web shows

- A product's **product preset** (Configuration → Products) decides whether
  it appears on the public web at all, and on which webs (none listed: every
  web). Core does the filtering, so other products never leave core.
- A product preset with a **report template** of its own shows all its published
  products. One without shows only those that contain a vulnerability report, as
  public-web always did - and none at all once the built-in
  `product_vulnerability.html` is switched off (see below).
- **TLP**: if any report item carries a TLP, the highest one must be CLEAR (or
  WHITE). A product with no TLP at all is shown only when its product preset's
  template turns *Requires TLP:CLEAR* off; the built-in templates always require it.

## Report templates

Every product is rendered by a Jinja template, in a sandbox with autoescaping:

- **Product page**, homepage entry and RSS text: the custom template of the
  product's preset, else `builtin/product_vulnerability.html` for
  vulnerability reports, else `builtin/product_base.html`.
- **Report item block**: the custom template of the item's type, else
  `builtin/item_vulnerability.html` for the "Vulnerability Report" type as Taranis
  creates it, else `builtin/item_generic.html` (every attribute with its label, in the
  type's order). No type has a role of its own: the page opens with the product's
  description, and every item follows in order. A page that wants one item apart (an
  introduction above the others, say) does it in a custom product template.

The built-ins fit the report item types Taranis creates and nothing more. A type that
was changed (other attributes, another title) or added gets the generic template until
it is given one of its own - start from a built-in in the template editor. The phrases
`in_versions` and `original_version_format` stay in the catalogs for such templates
(`tests/fixtures/templates/` holds the ones of an instance that lists affected systems
with their versions).

A custom template applies to the webs it lists, or to every web when it lists none,
so one web can look different from another: a product preset or report item type may
have a template for every web and others for chosen webs. A web uses the template that
lists it, else the one for every web, else the built-in; core refuses two templates of
the same preset or type that claim the same web. Which products a web shows follows its
own templates too (a preset with no template for that web shows only vulnerability reports there).

Custom templates are written in the GUI (Configuration → Public Web → Report
templates), which also lists the built-in ones (they live in
`shared/public_web_templates/`). The built-ins cannot be deleted, but those public-web
falls back on can be switched off there, to rely on custom templates alone:

- `product_vulnerability.html` off: only products whose preset has a template of its
  own are shown;
- `item_vulnerability.html` off: those items use `item_generic.html`;
- `item_generic.html` off: a report item left without a template is left out of
  the product - its block, the RSS text, search and the links only it cites (its TLP
  still counts) - and a product left with no item is not shown. An item whose own
  template fails renders as nothing.

`product_base.html` and `_macros.html` are always on: custom templates extend and
import them, and a failing product template falls back on the base. Core sends the
switched-off names with the templates (`disabled_builtins`); an older core sends none,
so everything is on. A product template must
`{% extends "builtin/product_base.html" %}` (or `product_vulnerability.html`) and
overrides blocks of it: `detail` (made of `header`, `items`, `links`), `summary`
(the homepage entry) and `rss`. A template that fails to render is logged and the
built-in one takes over, so one mistake never takes a page down. Core checks a
template when it is saved (syntax, known filters, the `extends`).

Context:

- `product`: `id`, `title`, `description`, `published`, `author`, `product_preset`
  {id, title}, `language` (the language it is shown in; None when unknown),
  `max_tlp`, `max_cvss`, `links`, `report_items` (in order; `?items=` counts them
  from 1). `lead` and `body_items` are the same as `description` and `report_items`,
  for templates written when an intro item could stand apart.
- each item: `name`, `name_prefix`, `uuid`, `language` (the language it is shown
  in, which its labels and constants follow; None when unknown), `type` (the type's
  title as written, for comparing), `type_label` (its name in the language shown), `type_id`,
  `created`, `last_updated`, `attrs` (named and shaped as in presenter templates:
  the attribute title in snake_case; one value, or a list where the attribute
  allows more; choice constants as written, so comparisons such as
  `attrs.impact == 'High'` work in every language), `attrs_display` (the same
  with constants as shown), `attributes` (`[{key, label, group, type, value,
  source_value, description}]`) and `fields` (one entry per attribute, as shown:
  `{key, label, group, type, value_list}`).
- `data` = {`product`, `report_items`}, as in presenter templates; `links`,
  `visible_links` (the `?items=` subset keeps the numbers, and the sources the
  description cites), `selected_items`,
  `lang` (the page's language), `site`, `t(key)` (conf/i18n `report` phrases,
  then `interface` ones), and `render_item(item, index)` in product templates.

A report not translated into the page's language is shown in the one it was written
in, and the page says so. Its own phrases follow it: `t()` gives `report` phrases in
the language of what the template renders (the product, or the item in an item
template), so a report nobody translated reads in one language. Only the homepage
entry (`summary`) belongs to the page, so its phrases are in the page's language, as
are `interface` phrases everywhere. Mark such text with
`{{ macros.content_lang(product, lang) }}` (or `item` in an item template) on the
element (`{% import "builtin/_macros.html" as macros %}`), as the built-in templates
do, so it carries a `lang` attribute when it differs from the page's.

Filters: `clean` (escapes everything but `<a>` links), `clean_rich`,
`link_refs(links)` (turns `[n]` into links), `safe_url`, `cvss_score`,
`cvss_severity`, `iso_date`, `ymd_date`, `affected_system`, `single`, `as_list`,
`capitalize_first`, `fix_spaces`, and the presenter filters `strfdate`,
`regex_replace`, `truncate_on_symbol`, `tlp_color`.

### Preview

The template dialog (Configuration → Public Web → Report templates) previews a template
before it is saved: core checks the source, then asks the web's node
(`POST /management/preview`, authenticated with the node key) to render a published
product with it - the newest one the template applies to, or one picked in the dialog -
as the report page, the homepage entry, or the whole RSS item. The node renders it with
the web's stored templates, the previewed one in place of its target's, in the web's own
page with its branding; its stylesheet and images are inlined, so the preview does not
depend on the browser reaching the web's hostname, and its scripts are left out but the
web's page script (see [Colour mode and the preview's language](#colour-mode-and-the-previews-language)).
A custom template that fails is replaced by the built-in one, as on the site, and the failure
(template, line, message) is listed under the preview. The node caches nothing; core keeps
the rendered page for ten minutes under a random ticket and serves it from
`/api/v1/config/public-web-templates/preview/<ticket>` with a policy of its own (the web's
CDN stylesheets and fonts allowed, no script but the page script, framed only by the
GUI), shown in the dialog's Preview tab and, from there, in a browser tab. No node that
core can reach, no preview.

A built-in template is previewed in its own dialog the same way, on a published product it
shows in (the item ones on a product holding items of their types, the others on any). The node
renders it with the built-ins alone, every one of them on, whatever the web's own templates
and switches, so the preview shows what the built-ins make of the product.

### Colour mode and the preview's language

Every page has a colour-mode button beside the language menu; each click goes to the next
mode: auto -> light -> dark -> auto, and the button shows the mode in use. Auto, the
default, follows the browser's setting, also when it changes; a pick is kept in the
browser's storage. The script doing it is `shared/public_web_script.py`, inline in each
page's head so the mode is set before the page is drawn. The template preview runs it too: core's policy
for the preview page allows exactly that script by its hash, and the frame is sandboxed
without an origin. Such a frame has no storage, so the page posts a pick to the GUI, which
opens the next rendering with it (`#theme=dark`).

The preview's language is picked in the page's own language menu. The node marks the preview
page (`data-taranis-preview`), where Bootstrap's script does not run: the page script opens
the menu, and a language picked in it is posted to the GUI, which renders the preview in it.

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
  - `PUBLIC_WEB_CACHE_TTL` (default `5400`) — cache lifetime in seconds. Older products are
    still shown while they load again in the background.
  - `PUBLIC_WEB_MAX_REPORTS` — at most this many of the newest products (default: every
    published product, shown a page at a time and all in the RSS feed).
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
