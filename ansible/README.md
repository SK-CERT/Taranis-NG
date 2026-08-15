# Ansible deployment

Taranis-NG ships two supported Ansible playbooks:

- **`playbooks/site.yml`** — the default single-host install. Installs Docker
  Engine on the target host and brings up the all-in-one Compose stack
  (`docker/docker-compose.yml`). No operator customization required when run
  against the default `inventory/localhost.yml`.
- **`playbooks/distribute-worker.yml`** — distributed (remote worker) install.
  Deploys one or more worker containers (collectors/bots/presenters/publishers)
  to each remote host over SSH, then registers every new node in Core. Runs only
  against the worker groups defined in your `inventory/distributed.local.yml`.

Two more playbooks manage a worker after it is deployed:

- **`playbooks/worker-power.yml`** — stop, start or restart the worker
  containers on a remote host. Non-destructive and fully reversible; the Core
  node rows stay in place.
- **`playbooks/worker-remove.yml`** — remove a worker deployment: delete its
  node rows from Core, then the containers, volumes, `/etc/taranis-ng` and the
  control-host copies of its API keys. Destructive; always pass `--limit`.
- **`playbooks/firewall.yml`** — deny-by-default host firewall: allows inbound
  tcp/22, tcp/80, tcp/443 and udp/443 only, outbound unrestricted. ufw on
  Debian/Ubuntu, firewalld on the RedHat family.

See [`docs/distributed-deployment.md`](../docs/distributed-deployment.md) for
the full distributed path (architecture, addressing & TLS, secrets,
troubleshooting) and [`inventory/README.md`](inventory/README.md) for the
inventory scaffolding flow.

## Quickstart

The tooling lives in the project's `.venv`, pinned by the `ansible` dependency
group in the root `pyproject.toml`:

```bash
python3 scripts/dev_setup.py --all
```

Use that rather than a bare `uv sync --group ansible`: `uv sync` makes the
environment match exactly the groups it is given, so naming `ansible` alone
removes pytest, the service dependencies and `.venv/bin/uv` itself — and no
other uv exists to run the command that would put it back.

Every command below is prefixed with `uv run --group ansible` so it uses that
environment; drop the prefix if you have `.venv/bin` on your `PATH`.

> **Run everything from `ansible/`.** Ansible reads `ansible.cfg` from the
> current working directory only, and that file supplies both the default
> inventory and `roles_path`. Invoked from the repository root, the playbooks
> match no hosts and cannot find their roles.

```bash
# Install the required collections.
uv run --group ansible ansible-galaxy collection install -r ansible/requirements.yml

cd ansible

# Single-host default (all-in-one stack on localhost).
uv run --group ansible ansible-playbook playbooks/site.yml

# Distributed — deploy remote worker host(s).
# (See inventory/README.md for the full copy-and-edit workflow.)
cp inventory/distributed.example.yml        inventory/distributed.local.yml
# group_vars/host_vars filenames must equal the group / inventory host name —
# Ansible silently ignores anything else.
cp inventory/group_vars/all.example.yml     inventory/group_vars/all.yml
cp inventory/group_vars/core.example.yml    inventory/group_vars/core.yml
cp inventory/host_vars/worker.example.yml   inventory/host_vars/collector-01.yml
# …edit those files: worker_types AND worker_base_hostname per host…
uv run --group ansible ansible-playbook -i inventory/distributed.local.yml \
  playbooks/distribute-worker.yml --limit worker_hosts
```

See the [Docker deployment guide](../docker/README.md) for the underlying
Docker Compose stack details.
