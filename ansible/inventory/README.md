# Ansible inventory

This directory holds the inventory files for the Taranis-NG deployment playbooks.

## Default single-host

`localhost.yml` is the default inventory (referenced by `ansible.cfg`). It
targets the local machine and requires no customization — use it for the
standard all-in-one stack:

```bash
cd ansible && uv run --group ansible ansible-playbook playbooks/site.yml
```

(Always run from `ansible/` — `ansible.cfg`, which supplies this default
inventory and `roles_path`, is only read from the current working directory.)

## Distributed (workers on separate hosts — or one host per mixed worker stack)

Real inventory files (those containing your actual hostnames, IPs, and
credentials) are gitignored; the tracked `*.example.yml` files are templates to
copy from.

**Filenames are load-bearing.** Ansible finds `group_vars/` and `host_vars/`
files by exact group or host name, so the real files must be `all.yml`,
`core.yml` and `<inventory_hostname>.yml`. A file named `all.local.yml` or
`collector-01.local.yml` is never read and every value in it is silently
ignored. The `.example` templates are safe to keep alongside them precisely
because their names match no group or host.

The top-level inventory is the exception — it is passed with `-i`, so
`distributed.local.yml` is fine.

### Setup

```bash
cd ansible/inventory

# Top-level inventory (operator-supplied, gitignored)
cp distributed.example.yml distributed.local.yml

# Shared shape (core_url, admin creds, ACME/EAB) — operator-supplied, gitignored
cp group_vars/all.example.yml            group_vars/all.yml
cp group_vars/core.example.yml           group_vars/core.yml

# Per-host overrides — REQUIRED one file per remote host (named after the
# inventory hostname). Defines the worker_types list for that host.
# Examples:
#   host_vars/collector-01.yml:    worker_types: ["collectors"]
#   host_vars/worker-multi-01.yml: worker_types: ["collectors", "bots"]
#   host_vars/worker-all-01.yml:   worker_types: ["collectors", "bots", "presenters", "publishers"]
cp host_vars/worker.example.yml host_vars/collector-01.yml
```

### Key concept: the `worker_types` list

Each remote host runs ONE OR MORE worker containers behind a single Traefik.
Which worker types run on a host is declared in that host's
`host_vars/<host>.yml`:

```yaml
# host_vars/worker-multi-01.yml
worker_types: ["collectors", "bots"]
# Subdomains build on this. Always set it explicitly: the default is the
# inventory key, which doubles the prefix when that key is already a worker FQDN.
worker_base_hostname: "worker-multi-01.example.org"
```

On the host above, Ansible deploys:
- `collectors` container → reachable at `https://collectors.worker-multi-01.example.org`
- `bots` container → reachable at `https://bots.worker-multi-01.example.org`
- ONE Traefik serving both, with per-type subdomain routing
- ONE node row per worker_type registered in Core (so two rows: collectors + bots)

### Run

```bash
cd ansible

# Deploy every host in the [worker_hosts] group.
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/distribute-worker.yml --limit worker_hosts

# Or target a single host directly.
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/distribute-worker.yml --limit worker-multi-01
```

After editing, `git status` should report a clean working tree — all real
inventory files are gitignored under the `*.yml` convention.
