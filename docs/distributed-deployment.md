# Distributed deployment

Taranis-NG runs by default as a single all-in-one Docker Compose stack on one
host (see [`docker/README.md`](../docker/README.md) and
[`ansible/playbooks/site.yml`](../ansible/playbooks/site.yml)). This document
covers the **distributed** path: moving one or more worker containers
(collectors / bots / presenters / publishers / public-web) to a separate machine that is
reachable from the Core host over SSH.

## When to distribute

- You want to isolate collection workloads (network egress, headless browser
  memory) from the Core host.
- You want to scale a worker type horizontally (multiple collectors nodes,
  each on its own host).
- A worker needs to run on a host with different network reachability than
  the Core (e.g. a collector that can only reach a specific internal feed).

## Architecture

The deployment model preserves the single-host default by adding an
**opt-in** distributed path:

```
                     ┌──────────────────────────────────────────────┐
                     │ Core host (default all-in-one stack)         │
                     │  - core, gui, postgres, redis, traefik       │
                     │  - the default collectors/bots/presenters/    │
                     │    publishers services if you keep them in    │
                     │    docker-compose.yml                         │
                     │  - Ansible control node                      │
                     └──────────────────┬───────────────────────────┘
                                        │ SSH (provisioning)
                                        │ HTTPS (runtime: both directions)
                                        ▼
                     ┌──────────────────────────────────────────────┐
                     │ Worker host (e.g. collector-01)               │
                     │  - Docker Engine (installed by Ansible)       │
                     │  - one or more worker containers + Traefik   │
                     │  - per-worker-type API key + TLS cert        │
                     └──────────────────────────────────────────────┘
```

The connection is **bidirectional**:

| Direction                 | Path                                  | Purpose                                  |
| ------------------------- | ------------------------------------- | ---------------------------------------- |
| Worker → Core             | `https://<core>/api/v1/...`           | Workers poll Core for work (collectors fetch source list, bots poll presets) |
| Worker → Core (bots only) | `https://<core>/sse`                  | Long-lived SSE stream of bot events      |
| Core → Worker             | `https://<worker>/api/v1/...`         | Core pushes work (collectors refresh, presenter generate, publisher publish) |

Both legs must be reachable. Failures here are the most common distributed
deployment issue.

## Prerequisites

On the **Core host** (the ansible control node):

- The all-in-one stack is already up and reachable (run `site.yml` or
  `docker compose up -d` against `docker/docker-compose.yml`).
- The Core host can SSH into each remote worker host as a non-root user with
  passwordless sudo (or with `--ask-become-pass`).
- The worker image either exists locally on the Core host (built from source
  or pulled from `skcert/...`), or `worker_image_build: true` is set in
  `group_vars/all.yml` so Ansible builds it from the source tree.

On each **worker host**:

- A supported Linux distribution (Debian/Ubuntu or RHEL/Fedora/Rocky/Alma).
- **Docker is NOT required in advance** — the `taranis-ng-docker` role installs
  Docker Engine and the Compose plugin idempotently. Nothing on the worker needs
  the Docker SDK for Python: the roles drive the `docker compose` CLI through
  `community.docker.docker_compose_v2`. (The SDK *is* needed on the Ansible
  control host, where `taranis-ng-image-transfer` builds and saves images —
  `pip install docker`.)
- Ports 80, 443 and 8443 must be free for the per-worker Traefik: 80 for ACME
  validation and the http→https redirect, 443 for a public web's own hostnames,
  8443 (`worker_api_port`) for the worker API Core calls. The role opens them in
  firewalld/ufw when either is active (`worker_open_firewall: false` to skip);
  any firewall in front of the host is still yours to open.
- **Both directions must be reachable**, and they are not the same port:
  - Core → worker on `worker_api_port` (8443) — the node API, plus DNS and NAT
    for `<type>.<worker_base_hostname>`; see the addressing section below.
  - Worker → Core on `core_satellite_port` (8443) — `/api/v1/{collectors,bots,
    public-web}`, `/sse` and `/traefik/dynamic/node` are carved out of Core's
    443 router and served only here, so a worker that can reach Core's 443 but
    not its 8443 registers fine and then does no work.

  Core does not publish that port unless told to: set
  `TARANIS_NG_SATELLITE_BIND=0.0.0.0` in the Core host's `.env` and restrict it
  to your worker addresses.

## Addressing model — VM hostname vs public API hostname

Three distinct concepts must not be confused:

| Concept | Where it's set | Used for |
| --- | --- | --- |
| **SSH target** — where Ansible connects to install Docker + run compose | `ansible_host` in `distributed.local.yml` | Anything Ansible SSHes to |
| **Subdomain base** — the DNS name each worker_type's API lives under | `worker_base_hostname` in `host_vars/<host>.yml` (defaults to `inventory_hostname`) | Builds the API URL `https://<type>.<worker_base_hostname>:<worker_api_port>` and Traefik's `Host()` router label |
| **Per-type FQDN** — final address Core uses for that worker_type's API | computed as `<type>.<worker_base_hostname>`, on `worker_api_port` | Sent to Core's node-registration API → stored in `*Node.api_url` → drives the ACME cert SAN |

The port belongs to the URL, not to the name: `Host()` routing is invisible to a
packet filter, so the API had to leave the world-open 443 before any rule about
it could mean anything. The certificate covers the *name*, so it is the same
certificate either way — only the port it is served on differs. DNS records carry
no port, so `<type>.<worker_base_hostname>` must still resolve publicly for ACME
to validate it, even though only Core may connect to `worker_api_port`.

The key decoupling: **`worker_base_hostname` does NOT default to `ansible_host`**.
It defaults to `inventory_hostname`, and operators can override it to any
public DNS name they've configured — independent of how Ansible reaches the VM.

### Two side-by-side examples

**Pattern A — VM hostname == public API hostname.**

The VM IS the public FQDN; operator wants `collectors.example.org` to be
both the SSH target and the worker_type's API URL:

```yaml
# distributed.local.yml
worker_hosts:
  hosts:
    collectors.example.org:
      ansible_host: collectors.example.org   # SSH target
      ansible_user: ops

# host_vars/collectors.example.org.yml
worker_types: ["collectors"]
worker_base_hostname: "example.org"
# → collectors API at https://collectors.example.org  (matches the VM's hostname ✓)
```

*(Without the `worker_base_hostname: "example.org"` override, the default
`inventory_hostname` would produce `collectors.collectors.example.org` —
usually not what you want.)*

**Pattern B — VM hostname ≠ public API hostname.**

VM is named `taranis1` (internal IP SSH target), but the worker_type APIs
should be public under `collectors.taranis1.example.org` etc.:

```yaml
# distributed.local.yml
worker_hosts:
  hosts:
    taranis1:                              # inventory key — any short string
      ansible_host: taranis1.example.org     # SSH target (the VM)
      ansible_user: ops

# host_vars/taranis1.yml   (filename matches inventory key)
worker_types: ["collectors", "bots"]
worker_base_hostname: "taranis1.example.org"
# → collectors API at https://collectors.taranis1.example.org  ✓
# → bots API at       https://bots.taranis1.example.org        ✓
# (Cert SANs match — Traefik requests them via the per-type Host() labels.)
```

### A public-web worker

`public-web` is a worker type like the others, with one difference that shapes
everything else: it serves the **internet**, not just Core.

```yaml
# host_vars/feed-01.example.com.yml
worker_types: ["public-web"]
worker_base_hostname: "example.com"
worker_tls_mode: "acme"
```

That gives Core a node at `https://public-web.example.com:8443`, reachable only
from the Core host. The webs themselves are added in the GUI under
*Configuration → Public Web*, each with its own hostname — and each of those
hostnames needs **its own DNS record pointing at the worker**. This is the part
that differs from the other types: they need one record for
`<type>.<worker_base_hostname>`, a public-web host needs one per web on top of it.

The worker's Traefik learns those hostnames from Core: it polls
`/traefik/dynamic/node` on the Core host's satellite port, authenticated with
this node's own API key, and gets back its routers, its certificates and the
security-headers middleware. Only its own — the unscoped payload carries every
node's webs and the private keys inlined beside them, and is not published at
all. A hostname nobody configured still lands on the node's catch-all router and
gets a clean 404.

### Concrete example matrix

For host "taranis1" (`ansible_host: taranis1.example.org`) running collectors + bots
with `worker_base_hostname: "taranis1.example.org"`:

| What | Value | Source |
| --- | --- | --- |
| SSH target | `taranis1.example.org` | `ansible_host` in `distributed.local.yml` |
| Inventory key (host identifier) | `taranis1` | top-level host key in `distributed.local.yml` |
| Filename for host_vars | `host_vars/taranis1.yml` | must match the inventory key |
| Subdomain base for worker FQDNs | `taranis1.example.org` | `worker_base_hostname` in host_vars |
| Collectors container's public FQDN | `collectors.taranis1.example.org` | computed as `<type>.<base>` |
| Bots container's public FQDN | `bots.taranis1.example.org` | same |
| ACME cert SAN for collectors router | `collectors.taranis1.example.org` | driven by Traefik `Host()` label |
| Core's `CollectorsNode.api_url` | `https://collectors.taranis1.example.org` | registered by `taranis-ng-node-register` |
| Core's `BotsNode.api_url` | `https://bots.taranis1.example.org` | registered by `taranis-ng-node-register` |

## Addressing & TLS

Each worker host runs its own Traefik that terminates TLS. Three modes are
supported — set `worker_tls_mode` in your gitignored `group_vars/<group>.yml`
or `host_vars/<host>.yml`:

1. **`selfsigned`** (default) — Ansible generates a self-signed cert on the
   worker host via `community.crypto`. Core then reaches the worker at
   `https://<worker_fqdn>/...` but the Core host must trust the cert.
   Currently a manual step: copy the worker cert into the Core host's trust
   store (`/usr/local/share/ca-certificates/` + `update-ca-certificates`).
   See TODO below.

   For a **public-web** worker there is a second trust store to think about.
   That advice covers core's own Python `requests` calls; when Core's Traefik
   proxies to the node it is the *traefik* container that verifies the
   certificate. Either use `acme`/`provided` there, or set a CA bundle under
   *Configuration → Application Settings → Routing & TLS*.
2. **`provided`** — operator supplies a CA-issued cert + key, already on
   the worker host, via `worker_tls_cert` / `worker_tls_key`. No trust-store
   step needed if the cert chains to a CA the Core host already trusts.
3. **`acme`** — Traefik requests a real certificate from a Let's Encrypt /
   ZeroSSL / custom ACME CA on first start, and renews it automatically.
   Core's registration probe and runtime Core→worker HTTPS calls verify TLS
   without any manual trust-store install. Supports HTTP-01, TLS-ALPN-01, and
   DNS-01 challenges, and External Account Binding (EAB) for CAs that
   require it (ZeroSSL, most private ACME servers).

### Ports and exposure

Two exposure classes, so two ports. A packet filter cannot see Host headers, so
an API and a public website sharing one port must be opened to everybody or to
nobody — hence the split.

| Host | Port | Open to | Serves |
| --- | --- | --- | --- |
| Worker | 80 | world | ACME HTTP-01 + http→https redirect |
| Worker | 443 | world | public-web's own web hostnames (idle on hosts without one) |
| Worker | `worker_api_port` (8443) | Core host only | the worker API Core calls |
| Core | 443 | world | GUI, the browser API, `/sse` |
| Core | `TARANIS_NG_SATELLITE_PORT` (8443) | worker hosts only | `/api/v1/{collectors,bots,public-web}`, `/sse`, `/traefik/dynamic/node` |

**A host firewall does not restrict the container ports.** Docker publishes a port
by writing DNAT rules into `nat/PREROUTING` and filter rules into its own chain in
`filter/FORWARD`; ufw and firewalld write to `filter/INPUT`, which container-bound
traffic never traverses. So 80, 443 and the API port are reachable whatever
`firewall_allowed_tcp_ports` lists, and the `taranis-ng-firewall` role governs only
traffic terminating on the host itself — sshd above all. Keep 22 there and set the
rest per host in `host_vars/<host>.yml`, not in the role defaults.

To narrow the API port for real, pick one of:

```yaml
# host_vars/<host>.yml — bind the listener to one address. Docker honours this,
# and it needs no firewall rule. Use the address Core reaches this host on.
worker_api_bind: "10.0.0.5"
```

```bash
# Or filter in Docker's own chain: DOCKER-USER is traversed before Docker's rules
# and is never flushed by it.
iptables -I DOCKER-USER -p tcp --dport 8443 '!' -s 198.51.100.10 -j DROP
```

Doing neither is a defensible choice — every worker endpoint requires
`Authorization: ApiKey <node key>`, including `isalive` — but then authentication is
the only control, not one layer of two.

**Do not close port 80.** ACME validates every hostname there, including
hostnames whose router lives on the API port, so closing it does not fail at
once — it fails at renewal, about thirty days later. TLS-ALPN-01 uses 443 and
DNS-01 needs no inbound at all.

On a single host none of this applies: the satellites reach core at
`http://core` over the compose network, never through Traefik, and no ACME or
certificate files are required at all. TLS there only decides whether browsers
trust the hostname you use.

### ACME configuration

When `worker_tls_mode: "acme"`, configure these variables in your gitignored
`group_vars/<group>.yml` or `host_vars/<host>.yml` (never in the tracked
`.example` files — they're secrets):

| Variable | Description | Default |
| --- | --- | --- |
| `worker_acme_email` | Email for ACME account notifications. **Required.** | `""` |
| `worker_acme_caserver` | ACME directory URL. Let's Encrypt prod by default. | `https://acme-v02.api.letsencrypt.org/directory` |
| `worker_acme_keytype` | Private key type: `EC256`, `EC384`, `RSA2048`, `RSA4096`, `RSA8192`. | `EC384` |
| `worker_acme_challenge` | Challenge type: `http` (HTTP-01), `tlsalpn` (TLS-ALPN-01), `dns` (DNS-01). | `http` |
| `worker_acme_eab_kid` | EAB key ID. **Required** for ZeroSSL / non-Let's-Encrypt CAs. | `""` |
| `worker_acme_eab_hmac` | EAB HMAC key. **Required** for ZeroSSL / non-Let's-Encrypt CAs. | `""` |
| `worker_acme_dns_provider` | Traefik DNS provider name (e.g. `cloudflare`). Only for `dns` challenge. | `""` |
| `worker_acme_dns_env` | Dict of env vars for the DNS provider (e.g. `{ CF_DNS_API_TOKEN: "..." }`). | `{}` |

**Reachability requirements:**

- **HTTP-01 (`worker_acme_challenge: "http"`)** — the ACME CA must be able
  to reach the worker's port 80, and every per-type FQDN
  (`<type>.<worker_base_hostname>`) must resolve publicly to the worker host.
- **TLS-ALPN-01 (`worker_acme_challenge: "tlsalpn"`)** — same, but port 443.
- **DNS-01 (`worker_acme_challenge: "dns"`)** — the worker does NOT need to
  be publicly reachable; Traefik updates a TXT record via the configured DNS
  provider using `worker_acme_dns_provider` + `worker_acme_dns_env`. Best
  fit for workers behind NAT / on private networks.

**Examples:**

```yaml
# Let's Encrypt, HTTP-01 (simplest — worker must be publicly reachable)
worker_tls_mode: "acme"
worker_acme_email: "ops@example.com"
worker_acme_challenge: "http"

# ZeroSSL with EAB, TLS-ALPN-01 (worker must be publicly reachable on :443)
worker_tls_mode: "acme"
worker_acme_email: "ops@example.com"
worker_acme_caserver: "https://acme.zerossl.com/v2/DV90"
worker_acme_eab_kid: "your-eab-kid"
worker_acme_eab_hmac: "your-eab-hmac"
worker_acme_challenge: "tlsalpn"

# Let's Encrypt, DNS-01 via Cloudflare (worker can be on a private network)
worker_tls_mode: "acme"
worker_acme_email: "ops@example.com"
worker_acme_challenge: "dns"
worker_acme_dns_provider: "cloudflare"
worker_acme_dns_env:
  CF_DNS_API_TOKEN: "your-cloudflare-api-token"
```

Traefik stores the ACME account + cert state in a persistent Docker volume
(`acme_storage`) mounted at `/letsencrypt` inside the Traefik container.
Cert renewals are automatic; the volume survives container redeploys.

## Secrets

Each worker_type on each host gets its own per-type API key (32-byte hex)
generated by the `taranis-ng-worker` role. The key is **never printed to the
play output** for security — only the file paths where it lives are surfaced
(via a `debug:` task after generation). The same key value is written to:

| Location | Purpose |
| --- | --- |
| `/etc/taranis-ng/secrets/api_key.<type>.txt` on the worker host (mode 0600, root:root) | Mounted into the worker container as `/run/secrets/api_key` (via the compose secret's `target:`, which every worker's `read_secret("api_key")` depends on) — the worker uses it to authenticate to Core |
| `docker/secrets/api_key.worker.<host>.<type>.txt` on the Ansible control host (gitignored, mode 0600) | Staging copy used by `taranis-ng-node-register` to feed Core's node-registration API |
| Core's `*Node.api_key` column for the registered node row (e.g. `collectors_node.api_key`) | What Core uses to authenticate to the worker via the `Authorization: ApiKey <key>` header |

All three hold the same key value. After the play finishes, the canonical
source of truth is Core's `*Node` row — the on-disk files are mostly for the
play's own re-runs and rotation workflows.

### Where to find the auto-generated key

If you didn't pre-supply the key via `worker_api_keys:`, the play prints the
file paths during the run, e.g.:

```
TASK [taranis-ng-worker : Show where each per-type API key is stored (path only — value is never printed)] ***
ok: [collector-01] => (item=...) => {
    "msg": "collectors API key on collector-01: worker host → /etc/taranis-ng/secrets/api_key.collectors.txt (mode 0600, root:root); control host staging → /home/you/Taranis-NG/docker/secrets/api_key.worker.collector-01.collectors.txt (gitignored, mode 0600). Core's collectors_node row will store the same key after taranis-ng-node-register runs."
}
```

To inspect the value (as root on either host):

```bash
# On the worker host:
sudo cat /etc/taranis-ng/secrets/api_key.collectors.txt

# On the Ansible control host:
cat docker/secrets/api_key.worker.<host>.<type>.txt
```

### Pre-supplying a key (optional)

If you want to match an existing Core node row, supply keys per worker_type
via the `worker_api_keys` dict in `host_vars/<host>.yml` — the role then
skips auto-generation for those types. See
[`ansible/inventory/host_vars/worker.example.yml`](../ansible/inventory/host_vars/worker.example.yml)
for the exact syntax.

### Rotating a key

To rotate, delete the on-disk files (`/etc/taranis-ng/secrets/api_key.<type>.txt`
on the worker and the control-host staging copy) and re-run the playbook — the
role regenerates a fresh key, and the registration step PUTs it onto the
existing Core node row. Idempotency is based on the file existing, not on the
key value, so leaving the files in place is a no-op.

## Quickstart: deploy a remote collectors node

1. Copy the inventory example files to their `*.yml` gitignored
   counterparts and fill in your values:

   ```bash
   cd ansible/inventory
   cp distributed.example.yml         distributed.local.yml
   cp group_vars/all.example.yml      group_vars/all.yml
   cp group_vars/core.example.yml     group_vars/core.yml
   cp host_vars/worker.example.yml    host_vars/collector-01.yml
   # Edit distributed.local.yml (add your collector-01 host to [worker_hosts]),
   # group_vars/all.yml (core_url, admin creds, TLS/ACME settings),
   # and host_vars/collector-01.yml (set worker_types: ["collectors"]).
   ```

2. Install the required Ansible collections:

   ```bash
   python3 scripts/dev_setup.py --all
   uv run --group ansible ansible-galaxy collection install -r ansible/requirements.yml
   ```

   Not a bare `uv sync --group ansible`: that makes the environment match only
   the groups named, removing pytest, the service dependencies and
   `.venv/bin/uv`. See [testing.md](testing.md).

3. Run the playbook limited to `worker_hosts` (or a single host):

   ```bash
   # Run from ansible/ — ansible.cfg (inventory + roles_path) is only read from
   # the current working directory.
   cd ansible

   # Deploy every host in [worker_hosts].
   uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
     playbooks/distribute-worker.yml --limit worker_hosts

   # Or target a single host directly.
   uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
     playbooks/distribute-worker.yml --limit collector-01
   ```

4. The playbook (per host):
   - Installs Docker Engine on the remote host.
   - For each entry in `worker_types`: builds (or saves) the matching
     `skcert/taranis-ng-<type>` image on the Core host, ships it to the remote
     via scp + `docker load`.
   - Generates a per-worker-type API key + renders the Traefik/compose config
     (one Traefik fronting ALL the host's worker_types, with per-type
     subdomain routing; cert is self-signed with SANs covering every type —
     or use ACME where Traefik requests per-type certs on demand).
   - Authenticates to Core as an admin user and POSTs a node row to
     `/api/v1/config/<type>-nodes` for each `worker_types` entry (the same
     collection endpoint for all four types). Core's `add_*_node` manager probes
     the worker with the supplied key before persisting — so a successful POST
     also verifies the Core→worker direction *and* the key. When a node with
     that `api_url` already exists the playbook PUTs instead, so a rotated key
     reaches Core rather than being silently skipped.

5. The new collectors node appears in the Core GUI under
   `Config → Collector Nodes` and can receive OSINT sources.

## Managing a worker after deployment

### Stopping and starting

`worker-power.yml` changes only the container state — volumes, secrets, TLS
material and the Core node rows are untouched, so it is fully reversible:

```bash
cd ansible

# stop every worker host
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/worker-power.yml -e worker_power=stopped --limit worker_hosts

# start one host again  (also: -e worker_power=restarted)
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/worker-power.yml -e worker_power=started --limit collectors.example.org
```

A stopped worker stays registered, so Core shows it as an unreachable node
rather than dropping it. That is usually what you want for maintenance; use
`worker-remove.yml` when the worker is going away for good.

### Removing a worker

`worker-remove.yml` is the destructive counterpart. It deregisters from Core
**first**, so Core stops dispatching work to a host that is about to lose its
containers — and if Core is unreachable the play fails before touching the
host at all.

```bash
cd ansible

# see exactly what would go
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/worker-remove.yml --limit collectors.example.org --check --diff

# do it
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/worker-remove.yml --limit collectors.example.org
```

By default that removes the Core node rows, the containers, the data volumes,
`/etc/taranis-ng` (compose file, per-type API keys, TLS material) and the staged
keys under `docker/secrets/` on the control host. Docker Engine is left
installed. Each part is independent:

| Variable | Default | Effect when `false` |
| --- | --- | --- |
| `worker_deregister_node` | `true` | Leaves the node rows in Core. Use when Core is already gone, or when re-attaching the worker later. |
| `worker_remove_volumes` | `true` | Keeps collector storage / presenter templates and the ACME certificate store. |
| `worker_remove_config` | `true` | Keeps `/etc/taranis-ng`, including the API keys — so a later re-deploy reuses the same keys. |
| `worker_remove_staged_key` | `true` | Keeps the control-host key copies. |
| `worker_remove_images` | `false` | Set `true` to also delete `skcert/taranis-ng-<type>` from the host. |

> **Always pass `--limit`.** Without it the play targets every host in
> `worker_hosts`.

### Firewalling a worker host

`firewall.yml` applies a deny-by-default inbound policy and leaves outbound
unrestricted:

| Port | Why it stays open |
| --- | --- |
| tcp/22 | SSH — Ansible's own transport |
| tcp/80 | ACME HTTP-01 validation and Traefik's http→https redirect |
| tcp/443 | the worker API Core calls |
| udp/443 | HTTP/3, which the worker's Traefik advertises and publishes |

```bash
cd ansible

uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/firewall.yml --limit worker_hosts
```

It uses ufw on Debian/Ubuntu and firewalld on the RedHat family, and always
writes the allow rules *before* the deny policy takes effect, so the SSH session
it is running over is never cut. It also refuses to run if the SSH port is
missing from `firewall_allowed_tcp_ports` — override with
`-e firewall_guard_ssh=false` only if you have console access.

Other knobs: `-e firewall_hosts=core` to target a different group,
`-e firewall_enable=false` to stage the rules without switching the firewall on,
and `-e '{"firewall_allowed_tcp_ports": [22, 80, 443, 9090]}'` to open more.

> **Docker publishes past the firewall.** Docker inserts its own iptables rules
> ahead of ufw's, so container ports published with `-p` are reachable whatever
> the policy says; firewalld behaves similarly. The worker stack publishes only
> 80 and 443 — the ports this policy opens anyway — so nothing is currently
> exposed beyond it. Publish a container on another port later and it *will* be
> reachable regardless of these rules. The play prints the currently published
> ports at the end so the gap stays visible.

## Moving work items between nodes

Once multiple nodes of a given type exist (e.g. two collectors nodes), you can
move individual work items (OSINT sources, bot presets, product types,
publisher presets) between them directly from the existing admin dialogs in the
**Vue 3 GUI** (`src/gui-v3/`, served at `/`):

1. Open the work item's edit dialog (e.g. `Config → OSINT Sources → Edit`).
2. The **Node** and **Collector/Bot/Presenter/Publisher** `v-select`s are now
   editable in edit mode (previously they were locked to the create-time
   choice — `:disabled="isEdit || ..."`).
3. Pick the target node + worker. Parameter values whose `parameter.key`
   matches are carried over to the new worker's parameter set automatically;
   parameters absent on the new worker fall back to their defaults.
4. Save. The backend `update()` validates that the target worker is of the
   same type as the current worker (so you can move an RSS source between two
   collectors nodes hosting `RSS_COLLECTOR`, but not from `RSS_COLLECTOR`
   to `PLAYWRIGHT_COLLECTOR`).

> **Note:** The Vue 2 GUI (`src/gui/`) is left intentionally untouched by this
> change — operators using the Vue 2 UI will not see the unlock. Move work
> items via the Vue 3 UI or via the admin REST API directly.

## Operator-supplied values never dirty the repo

Real inventory, group_vars, host_vars, worker env files, per-worker key
staging, and TLS material are all gitignored. After filling in your values:

```bash
git status   # → "nothing to commit, working tree clean"
```

If `git status` surfaces any modified or untracked file under
`ansible/inventory/`, `docker/.env.worker` or `docker/secrets/`, the
`.gitignore` `# Ansible operator-supplied values` block is incomplete and must
be fixed.

## Troubleshooting

- **Node registration returns 401/403**: `taranis_admin_user` /
  `taranis_admin_password` in `group_vars/all.yml` are wrong, or the user
  lacks `CONFIG_*_NODE_CREATE` permission.
- **The connectivity probe returns 401**: every worker endpoint is
  authenticated, `isalive` included — it used to be the one open endpoint, which
  in a distributed deployment meant an unauthenticated probe published on the
  internet. The probe now sends `Authorization: ApiKey <node key>`, so a 401 here
  means the key Core was just given is not the key the container is running
  with. Check `/etc/taranis-ng/secrets/api_key.<type>.txt` on the worker and
  re-run the playbook to refresh it.
- **`CERTIFICATE_VERIFY_FAILED: self-signed certificate` for some worker types
  but not others**: Traefik is serving its built-in self-signed certificate for
  those names because ACME has not given it one. Traefik requests a certificate
  per `worker_type` — each type's router carries its own `Host()` — and they
  arrive independently, so a mixed result is normal *while issuance is still in
  flight*. The role waits `worker_trust_retries × worker_trust_delay` (3 min by
  default) per hostname before failing, precisely so that a subset which merely
  hadn't landed yet is not reported as broken. If a name still fails after that
  wait, Traefik has stopped trying, and the worker's own ACME log distinguishes
  the two real causes:

  ```bash
  ssh <worker> 'sudo docker logs $(sudo docker ps -qf name=traefik) 2>&1 \
    | grep -iE "acme|certificate|error" | tail -40'
  ```

  (Addressing the container directly rather than via `docker compose logs`, which
  would need `-p` — the project name is derived per host as
  `taranis-ng-worker-<inventory_hostname>` with every character outside
  `[a-z0-9_-]` replaced by a hyphen, so it is *not* the hostname as written.)

  *Not authorised* (`domains are not whitelisted`, `not authorized`, an order
  rejected at creation) means the ACME account is not approved for the name. A CA
  may pre-validate domains against the CA-side account that the EAB credential
  binds to — ACME provides for exactly this — and then issues only for names
  already approved on the account behind that host's `worker_acme_eab_kid`, and
  the kid **is** the account: names approved for the Core host do not carry over.
  Partial approval therefore fails partially. *Challenge failure* (timeout, 404
  on `/.well-known/acme-challenge`, DNS) is reachability instead: with
  `worker_acme_challenge: "http"`, port 80 must be world-open and the name must
  resolve publicly — the certificate is *used* on `worker_api_port` but
  *validated* on 80.

  Either way Core verifies worker certificates, so the affected types register
  and then never work; this is not cosmetic. A wildcard would collapse the
  approval to one name, but the role does not request one today — that needs
  `tls.domains` on the routers plus DNS-01, since wildcards cannot use HTTP-01.
- **The probe times out on `worker_api_port`, or works over IPv4 but times out
  over IPv6**: the two address families reach a published container port through
  different chains, so they fail independently.
  - **IPv4** is DNAT'd and filtered in `FORWARD`, never touching `INPUT` — the
    familiar "Docker bypasses your firewall". A timeout here means
    `worker_api_bind` is set to an address the client doesn't use, or a
    `DOCKER-USER` rule is dropping it.
  - **IPv6** does *not* bypass it. Docker ships with `ip6tables` management
    disabled, so there is no v6 DNAT: `docker-proxy` listens in the host
    namespace and the traffic traverses `INPUT` like any host service. If the
    port isn't open in ufw/firewalld it is dropped — reachable on v4, timing out
    on v6. The worker role opens `worker_api_port` for exactly this reason, so
    this appears mainly on hosts whose firewall was changed by hand.

  Check both explicitly rather than trusting one:

  ```bash
  for f in 4 6; do curl -sS -$f -o /dev/null -w "v$f -> %{http_code}\n" \
    --max-time 8 https://collectors.<base>:8443/api/v1/isalive; done
  ```

  `401` is the healthy answer on both. The same asymmetry decides how to restrict
  the port: a source rule in the firewall role is effective for IPv6 and ignored
  for IPv4, which needs `DOCKER-USER`.
- **Worker Traefik logs `Provider error … context deadline exceeded` for
  `/traefik/dynamic/node`**: the worker cannot reach Core's satellite port. Nearly
  always the opt-in publish — Core binds `:8443` to loopback by default
  (`TARANIS_NG_SATELLITE_BIND=127.0.0.1`), so from outside the Core host there is
  no listener at all. Set it to `0.0.0.0`, `docker compose up -d traefik`, and
  confirm with `ss -tlnp | grep 8443`.

  The error text tells you which leg is broken, so read it before changing
  anything: **timeout** (`context deadline exceeded`, `i/o timeout`) means packets
  are being *dropped* — a firewall, either the Core host's own (traffic that
  reaches no Docker listener falls through to `filter/INPUT`, where a default-deny
  policy drops it) or a perimeter one. **`connection refused`** means the packets
  arrive and nothing is listening, i.e. the entrypoint or the publish is missing
  rather than filtered. **TLS or 401 errors** mean the port is fine and the
  problem is the certificate or the node's API key.

  Remember this port carries *all* worker→Core traffic, not just the provider:
  `/api/v1/{collectors,bots,public-web}` and `/sse` too. So a node can register
  successfully — registration is control-host→Core on 443 plus Core→worker on
  `worker_api_port`, neither of which uses this leg — and then do no work at all.
- **A public web serves the wrong certificate, or 404s every hostname**: the
  worker's Traefik could not poll `/traefik/dynamic/node`. Check that the Core
  host publishes its satellite port (`TARANIS_NG_SATELLITE_BIND=0.0.0.0`) and
  admits this worker, and that the node's API key matches. The catch-all keeps
  answering from `fallback.yml` meanwhile, which is why the site stays up but
  unconfigured.
- **Node registration returns 400 / "Could not create collectors node"**:
  the worker's `/api/v1/<type>` endpoint didn't return 200 when Core probed
  it. Confirm the worker's Traefik is up with

  ```bash
  curl -k -H "Authorization: ApiKey $(sudo cat /etc/taranis-ng/secrets/api_key.collectors.txt)" \
       https://collectors.<worker_base_hostname>:8443/api/v1/isalive
  ```

  which should return `{"isalive": true}`. Both the port and the header are
  required: the API is on `worker_api_port`, not 443, and `isalive` is
  authenticated like every other worker endpoint. Do **not** probe
  `/api/v1/collectors` by hand: it is POST-only, so a GET answers 405
  regardless of whether the worker is healthy. If isalive works but
  registration still fails, the `api_key` file on the worker doesn't match what
  the playbook sent to Core.
- **Collector's `last_seen` never advances**: the worker cannot reach Core.
  Check that `<type>.<worker_base_hostname>` resolves to the worker's real
  address from Core, and that the worker host may reach Core on the **satellite
  port** — `/api/v1/collectors` is carved out of Core's 443 router, so a worker
  aimed at the port-less `core_url` gets a 404 from a Core that is otherwise
  perfectly healthy. The containers are told `{{ core_satellite_url }}`
  (`core_url` plus `core_satellite_port`) precisely so this cannot drift; if you
  overrode `TARANIS_NG_CORE_URL` by hand, that is the first thing to check. For
  self-signed Core certs, the worker host must also trust the Core cert.
- **Bots SSE not working**: same reachability leg and the same port — `/sse` is
  served on both entrypoints, but the role points bots at the satellite one so
  that every satellite-generated connection lands on one restrictable port.
  Long-lived connection — intermediate proxies must allow keep-alive and not
  buffer.
- **"Cannot move source to collector of type ... (source is bound to type
  ...)"**: you tried to move a work item between workers of different types.
  Move only works within the same `type` — re-create the source on the new
  collector instead.

## Relevant files

- [`ansible/playbooks/site.yml`](../ansible/playbooks/site.yml) — single-host
  default install.
- [`ansible/playbooks/distribute-worker.yml`](../ansible/playbooks/distribute-worker.yml)
  — remote-only worker deployment + node registration.
- [`ansible/roles/taranis-ng-docker/`](../ansible/roles/taranis-ng-docker/) —
  Docker Engine install role (apt + dnf).
- [`ansible/roles/taranis-ng-image-transfer/`](../ansible/roles/taranis-ng-image-transfer/)
  — `docker save` → scp → `docker load` (air-gapped friendly).
- [`ansible/roles/taranis-ng-worker/`](../ansible/roles/taranis-ng-worker/)
  — worker containers + Traefik + per-worker-type key + TLS (selfsigned /
  provided / acme).
- [`ansible/roles/taranis-ng-node-register/`](../ansible/roles/taranis-ng-node-register/)
  — registers the new node in Core via the admin REST API.
- [`ansible/inventory/README.md`](../ansible/inventory/README.md) — the
  `.example` → real-file flow.
- [`docker/docker-compose.worker.yml.example`](../docker/docker-compose.worker.yml.example)
  — standalone worker compose for operators who prefer to run compose
  directly (without Ansible).
- [`docker/.env.worker.example`](../docker/.env.worker.example) — env template
  for the standalone worker compose.

## Multi-VM capabilities & limitations

This solution supports **multiple worker containers per host, mixed across
types**. Each remote host runs ONE Traefik serving N worker services, with
**per-type subdomain routing** (e.g. `collectors.hostA.example.com`,
`bots.hostA.example.com`).

Supported:

- **Multiple VMs, multiple worker types per VM.** Set `worker_types` in each
  host's `host_vars/<host>.yml` — a list of one or more of
  `collectors`, `bots`, `presenters`, `publishers`, `public-web`. Examples:
  - `["collectors"]` — one collectors node on that VM.
  - `["collectors", "bots"]` — collectors + bots on one VM, behind one Traefik.
  - `["collectors", "bots", "presenters", "publishers"]` — full worker stack.
  - `["public-web"]` — a public report feed; see "A public-web worker" above.
- **Per-worker-type node rows in Core.** Each entry in `worker_types` becomes
  a separate row in the corresponding `*Node` table; each has its own
  per-type subdomain (so Core addresses `https://<type>.<host>/...`) and its
  own `api_key` (separate secret file at
  `/etc/taranis-ng/secrets/api_key.<type>.txt`).
- **ACME** — one ACME resolver on the host's Traefik requests per-type certs
  on-demand based on the `Host(<type>.<host>)` label. One EAB credential per
  host is sufficient; per-host EAB override is via
  `host_vars/<host>.yml`.

  The resolver is *named*, and a name only means something inside the Traefik
  that declares it. The worker declares `worker_acme_resolver_name`
  (`myresolver` by default), and the role sends that name to Core when it
  registers the public-web node, so Core names it in the routers it serves back.
  For a **public web** the resolver is resolved most-specific-first:

  | Level | Where | Use |
  | --- | --- | --- |
  | Web | *Configuration → Public Web →* the web | One hostname needing a different CA |
  | Node | *Configuration → Public Web →* the node | The resolver that node's Traefik declares — the normal case for a remote worker |
  | Instance | *Application Settings → Routing & TLS*, or `TRAEFIK_CERT_RESOLVER` | Core's own Traefik |

  Leave the node level empty only for the node running beside Core. A remote node
  inheriting the instance-wide name gets a resolver it does not declare, and
  Traefik then logs `Router uses a nonexistent certificate resolver`, disables
  ACME for that router and serves its **default self-signed certificate** — the
  hostname answers, on the wrong certificate, with only that log line to say why.
- **Self-signed mode** — generates ONE cert covering all per-type subdomains
  (the SAN list = `worker_types × worker_base_hostname`). Operators must
  install that cert into Core's CA bundle.
- **Idempotent re-runs.** Re-running the playbook for a host with additional
  `worker_types` entries registers + probes only the new ones.
- **Per-host + per-type API keys.** Each worker_type on each host gets its
  own auto-generated 32-byte hex key (or a pre-supplied one via the
  `worker_api_keys` dict). Staged on the control host at
  `docker/secrets/api_key.worker.<host>.<type>.txt` (gitignored).

NOT supported:

- **Multiple instances of the SAME worker_type on one host.** `worker_types:
  ["collectors", "collectors"]` doesn't make sense — there's still only one
  service named `collectors` in the compose. To scale collectors horizontally,
  add another host with `worker_types: ["collectors"]`.

### Worked example: three hosts

The full stack on one machine, a dedicated collectors host, and a third host
running collectors and bots together:

| Host | Deployed via | `host_vars` entry |
| --- | --- | --- |
| `core.example.org` | `site.yml` (all-in-one stack via `docker/docker-compose.yml`) — no `host_vars` needed. Configure Core's own ACME with `docker/acme.env` + `TRAEFIK_CERT_RESOLVER` in `docker/.env` (see the [Docker guide](../docker/README.md#enabling-acme-for-automatic-https-certificates)). | none |
| `collectors.example.org` | `distribute-worker.yml` | `host_vars/collectors.example.org.yml` → `worker_types: ["collectors"]`, `worker_base_hostname: "example.org"` (so subdomain = `collectors.example.org`) |
| `worker-multi-01` | `distribute-worker.yml` | `host_vars/worker-multi-01.yml` → `worker_types: ["collectors", "bots"]`, `worker_base_hostname: "worker-multi-01.example.org"` (so subdomains are `collectors.worker-multi-01.example.org` and `bots.worker-multi-01.example.org`) |

> **Note:** two hosts must not share a `worker_base_hostname` — the per-type
> subdomains would collide, and only one host can serve
> `collectors.example.org`. Give each host its own base (as the third row
> does), or use wildcard DNS like `*.example.org` and assign each host its own
> subdomain prefix.

## TODO / follow-ups

- Add a small Ansible task in `taranis-ng-node-register` to copy the worker's
  self-signed cert into the Core host's CA bundle
  (`/usr/local/share/ca-certificates/taranis-worker-<host>.crt` +
  `update-ca-certificates`) so the registration probe + runtime Core→worker
  calls verify TLS without operator intervention. (Only needed for
  `worker_tls_mode: "selfsigned"`; the `"acme"` and `"provided"` modes
  bypass this step entirely.)
- Optionally add a Playwright E2E for the node-reassignment flow (create a
  source on node A → edit → move to node B → assert source now appears under B).
