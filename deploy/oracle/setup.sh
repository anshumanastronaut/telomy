#!/usr/bin/env bash
# One-time setup of the Telomy backend on an Oracle Cloud Always Free VM (Oracle Linux 9, works on 1 GB E2.1.Micro).
# Run on the server as the default user (opc):  HOST=<ip>.sslip.io bash setup.sh
#   • 2 GB swap, firewall 80/443, Python 3.13 via uv, the API as a systemd service on 127.0.0.1:8787
#   • Caddy in front with automatic HTTPS (Let's Encrypt) for $HOST
#   • nightly SQLite backup, 14 days kept
# Secrets live only in /etc/telomy.env (root, 600): TELOMY_ACCESS_PASSWORD, TELOMY_SECRET, ANTHROPIC_API_KEY.
set -euo pipefail
: "${HOST:?set HOST, e.g. 129-154-1-2.sslip.io}"
APP=/opt/telomy

echo "== swap"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "== packages + firewall"
sudo dnf -y -q install tar sqlite rsync cronie policycoreutils-python-utils >/dev/null
sudo systemctl enable -q --now crond
sudo firewall-cmd -q --permanent --add-service=http --add-service=https && sudo firewall-cmd -q --reload

echo "== python 3.13 (uv)"
if ! command -v uv >/dev/null; then curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null; fi
export PATH="$HOME/.local/bin:$PATH"
cd "$APP"
# Python lives under /opt (not $HOME): SELinux blocks services from executing files in home directories.
export UV_PYTHON_INSTALL_DIR="$APP/python"
uv python install -q 3.13
uv venv -q --python 3.13 .venv
uv pip install -q --python .venv/bin/python -r requirements.txt
sudo semanage fcontext -a -t bin_t "$APP/python(/.*)?" 2>/dev/null || true
sudo semanage fcontext -a -t bin_t "$APP/\.venv/bin(/.*)?" 2>/dev/null || true
sudo restorecon -R "$APP/python" "$APP/.venv/bin"

echo "== service"
sudo tee /etc/systemd/system/telomy.service >/dev/null <<EOF
[Unit]
Description=Telomy API
After=network-online.target
[Service]
User=opc
WorkingDirectory=$APP
EnvironmentFile=/etc/telomy.env
Environment=TELOMY_DB=$APP/telomy.db
ExecStart=$APP/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787 --workers 1
Restart=always
RestartSec=3
MemoryMax=700M
[Install]
WantedBy=multi-user.target
EOF

echo "== caddy (HTTPS)"
if ! command -v caddy >/dev/null; then
  ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v2.10.2/caddy_2.10.2_linux_${ARCH}.tar.gz" | sudo tar -xz -C /usr/local/bin caddy
fi
sudo mkdir -p /etc/caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
$HOST {
  encode gzip
  reverse_proxy 127.0.0.1:8787
}
EOF
sudo tee /etc/systemd/system/caddy.service >/dev/null <<'EOF'
[Unit]
Description=Caddy
After=network-online.target
[Service]
ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
Restart=always
AmbientCapabilities=CAP_NET_BIND_SERVICE
[Install]
WantedBy=multi-user.target
EOF

echo "== nightly backup (03:15, 14 days)"
sudo tee /etc/cron.d/telomy-backup >/dev/null <<'EOF2'
15 3 * * * opc mkdir -p /opt/telomy/backups && sqlite3 /opt/telomy/telomy.db ".backup /opt/telomy/backups/telomy-$(date +\%F).db" && find /opt/telomy/backups -name 'telomy-*.db' -mtime +14 -delete
EOF2

sudo systemctl daemon-reload
sudo systemctl enable -q --now telomy caddy
sudo systemctl restart telomy caddy
sleep 4
curl -fsS http://127.0.0.1:8787/auth/status && echo && echo "== done: https://$HOST"
