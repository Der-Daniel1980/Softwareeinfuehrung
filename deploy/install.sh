#!/usr/bin/env bash
# deploy/install.sh — SysIntro installer for Ubuntu 26.04 LTS
# Usage: sudo bash install.sh [--domain example.com] [--email admin@example.com]
#                             [--admin-password PW] [--tls] [--no-firewall] [--help]
# Idempotent — safe to re-run.
set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SYSINTRO_DOMAIN="${SYSINTRO_DOMAIN:-_}"
SYSINTRO_ADMIN_EMAIL="${SYSINTRO_ADMIN_EMAIL:-admin@example.com}"
SYSINTRO_ADMIN_PASSWORD="${SYSINTRO_ADMIN_PASSWORD:-}"
SYSINTRO_HOME="${SYSINTRO_HOME:-/opt/sysintro}"
SYSINTRO_TLS="${SYSINTRO_TLS:-0}"
SYSINTRO_FIREWALL=1   # can be disabled with --no-firewall

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
SYSINTRO_REPO_DIR="${SYSINTRO_REPO_DIR:-$REPO_ROOT}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; exit 1; }

usage() {
    cat <<EOF
Usage: sudo bash install.sh [OPTIONS]

Options:
  --domain DOMAIN          nginx server_name (default: _ = any host)
  --email EMAIL            admin / certbot e-mail (default: admin@example.com)
  --admin-password PASS    reset admin@demo.local to this password after seed
  --tls                    run certbot after nginx setup
  --no-firewall            skip ufw configuration
  --help                   show this message
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Parse CLI flags
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain)           SYSINTRO_DOMAIN="$2";         shift 2 ;;
        --email)            SYSINTRO_ADMIN_EMAIL="$2";    shift 2 ;;
        --admin-password)   SYSINTRO_ADMIN_PASSWORD="$2"; shift 2 ;;
        --tls)              SYSINTRO_TLS=1;               shift   ;;
        --no-firewall)      SYSINTRO_FIREWALL=0;          shift   ;;
        --help|-h)          usage ;;
        *) error "Unknown option: $1 — run with --help for usage" ;;
    esac
done

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------
info "=== Pre-flight checks ==="

if [[ "$(id -u)" -ne 0 ]]; then
    error "This script must be run as root. Use: sudo bash $0"
fi

if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    source /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
        warn "Not Ubuntu (ID=${ID:-unknown}). Proceeding anyway."
    elif [[ "${VERSION_ID:-}" != "26.04" ]]; then
        warn "Expected Ubuntu 26.04, found VERSION_ID=${VERSION_ID:-unknown}. Proceeding anyway."
    else
        info "Ubuntu ${VERSION_ID} detected — OK"
    fi
else
    warn "/etc/os-release not found; cannot verify OS version."
fi

info "Install directory : $SYSINTRO_HOME"
info "Repo source       : $SYSINTRO_REPO_DIR"
info "Domain            : $SYSINTRO_DOMAIN"
info "TLS               : $SYSINTRO_TLS"
info "Firewall          : $SYSINTRO_FIREWALL"

# ---------------------------------------------------------------------------
# 2. System packages
# ---------------------------------------------------------------------------
info "=== Installing system packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
PKGS=(
    python3 python3-venv python3-pip python3-dev
    build-essential libffi-dev
    nginx
    sqlite3
    openssl
    rsync
    ca-certificates curl
)
if [[ "$SYSINTRO_FIREWALL" -eq 1 ]]; then
    PKGS+=(ufw)
fi
if [[ "$SYSINTRO_TLS" -eq 1 ]]; then
    PKGS+=(certbot python3-certbot-nginx)
fi
apt-get install -y --no-install-recommends "${PKGS[@]}"

info "Python version: $(python3 --version)"

# ---------------------------------------------------------------------------
# 3. System user
# ---------------------------------------------------------------------------
info "=== Creating system user 'sysintro' ==="
useradd --system --home "$SYSINTRO_HOME" --shell /usr/sbin/nologin sysintro 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. Directory structure
# ---------------------------------------------------------------------------
info "=== Creating directory structure under $SYSINTRO_HOME ==="
for d in app data attachments logs venv; do
    install -d -o sysintro -g sysintro -m 750 "$SYSINTRO_HOME/$d"
done

# ---------------------------------------------------------------------------
# 5. Code deploy
# ---------------------------------------------------------------------------
info "=== Syncing application code ==="
rsync -a --delete \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='data' \
    --exclude='attachments' \
    --exclude='logs' \
    --exclude='*.db' \
    "$SYSINTRO_REPO_DIR/" "$SYSINTRO_HOME/app/"
chown -R sysintro:sysintro "$SYSINTRO_HOME/app"

# ---------------------------------------------------------------------------
# 6. Python venv + dependencies
# ---------------------------------------------------------------------------
info "=== Setting up Python virtual environment ==="
sudo -u sysintro python3 -m venv "$SYSINTRO_HOME/venv"
sudo -u sysintro "$SYSINTRO_HOME/venv/bin/pip" install --upgrade pip wheel --quiet
sudo -u sysintro "$SYSINTRO_HOME/venv/bin/pip" install -r "$SYSINTRO_HOME/app/requirements.txt" --quiet

# ---------------------------------------------------------------------------
# 7. Config (.env) — idempotent, never overwrite
# ---------------------------------------------------------------------------
info "=== Writing .env config ==="
if [[ ! -f "$SYSINTRO_HOME/.env" ]]; then
    SECRET_KEY=$(openssl rand -hex 32)

    # COOKIE_SECURE matches SECURE_COOKIES in config.py
    if [[ "$SYSINTRO_TLS" -eq 1 ]]; then
        SECURE_COOKIES=1
        BASE_URL="https://${SYSINTRO_DOMAIN}"
    else
        SECURE_COOKIES=0
        if [[ "$SYSINTRO_DOMAIN" == "_" ]]; then
            BASE_URL="http://localhost"
        else
            BASE_URL="http://${SYSINTRO_DOMAIN}"
        fi
    fi

    cat > "$SYSINTRO_HOME/.env" <<ENVEOF
# Generated by install.sh — $(date -u +"%Y-%m-%dT%H:%M:%SZ")
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=sqlite:///${SYSINTRO_HOME}/data/sysintro.db
ACCESS_TOKEN_EXPIRE_MINUTES=480
SECURE_COOKIES=${SECURE_COOKIES}
DEBUG=0
CORS_ORIGINS=${BASE_URL}
UPLOAD_DIR=${SYSINTRO_HOME}/attachments
ENVEOF

    chmod 600 "$SYSINTRO_HOME/.env"
    chown sysintro:sysintro "$SYSINTRO_HOME/.env"
    info ".env created."
else
    info ".env already exists — not overwritten."
fi

# Symlink so the app finds .env regardless of working directory
ln -sf "$SYSINTRO_HOME/.env" "$SYSINTRO_HOME/app/.env"
chown -h sysintro:sysintro "$SYSINTRO_HOME/app/.env"

# ---------------------------------------------------------------------------
# 8. Database setup
# ---------------------------------------------------------------------------
info "=== Running database migrations ==="
(cd "$SYSINTRO_HOME/app" && \
    sudo -u sysintro "$SYSINTRO_HOME/venv/bin/alembic" upgrade head)

info "=== Seeding demo data ==="
(cd "$SYSINTRO_HOME/app" && \
    sudo -u sysintro "$SYSINTRO_HOME/venv/bin/python" -m app.seed.run_seed)

if [[ -n "$SYSINTRO_ADMIN_PASSWORD" ]]; then
    # Note: run_seed --reset-admin-password resets to the hardcoded 'demo1234' value.
    # It does NOT accept a password argument. A custom password cannot be set via
    # this flag — please log in as admin@demo.local / demo1234 and change it in
    # the web interface after install.
    warn "SYSINTRO_ADMIN_PASSWORD was set, but the seed script only supports"
    warn "--reset-admin-password (which resets to 'demo1234' — no custom value)."
    warn "Log in as admin@demo.local / demo1234 and change the password via the UI."
fi

# ---------------------------------------------------------------------------
# 9. systemd unit
# ---------------------------------------------------------------------------
info "=== Installing systemd unit ==="
# Substitute SYSINTRO_HOME into the unit file if it differs from /opt/sysintro
UNIT_SRC="$SCRIPT_DIR/sysintro.service"
if [[ ! -f "$UNIT_SRC" ]]; then
    error "Unit file not found: $UNIT_SRC"
fi

if [[ "$SYSINTRO_HOME" == "/opt/sysintro" ]]; then
    cp "$UNIT_SRC" /etc/systemd/system/sysintro.service
else
    sed "s|/opt/sysintro|${SYSINTRO_HOME}|g" "$UNIT_SRC" \
        > /etc/systemd/system/sysintro.service
fi

systemctl daemon-reload
systemctl enable --now sysintro

# Give the service a moment to start, then check
sleep 2
if ! systemctl is-active --quiet sysintro; then
    warn "Service failed to start. Last 30 journal lines:"
    journalctl -u sysintro -n 30 --no-pager >&2
    exit 1
fi
info "Service 'sysintro' is running."

# ---------------------------------------------------------------------------
# 10. nginx
# ---------------------------------------------------------------------------
info "=== Configuring nginx ==="
NGINX_CONF_SRC="$SCRIPT_DIR/sysintro.nginx.conf"
if [[ ! -f "$NGINX_CONF_SRC" ]]; then
    error "nginx config not found: $NGINX_CONF_SRC"
fi

sed "s|__SYSINTRO_DOMAIN__|${SYSINTRO_DOMAIN}|g" "$NGINX_CONF_SRC" \
    > /etc/nginx/sites-available/sysintro

ln -sf /etc/nginx/sites-available/sysintro /etc/nginx/sites-enabled/sysintro
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
info "nginx configured and reloaded."

# ---------------------------------------------------------------------------
# 11. TLS
# ---------------------------------------------------------------------------
if [[ "$SYSINTRO_TLS" -eq 1 ]]; then
    if [[ "$SYSINTRO_DOMAIN" == "_" ]]; then
        error "Cannot run certbot with domain '_'. Set --domain to a real FQDN."
    fi
    info "=== Running certbot for TLS ==="
    certbot --nginx \
        -d "$SYSINTRO_DOMAIN" \
        --non-interactive \
        --agree-tos \
        -m "$SYSINTRO_ADMIN_EMAIL" \
        --redirect
    info "TLS certificate installed."

    # Update SECURE_COOKIES in .env
    if grep -q "^SECURE_COOKIES=0" "$SYSINTRO_HOME/.env"; then
        sed -i 's/^SECURE_COOKIES=0/SECURE_COOKIES=1/' "$SYSINTRO_HOME/.env"
        systemctl restart sysintro
        info "SECURE_COOKIES set to 1 and service restarted."
    fi
fi

# ---------------------------------------------------------------------------
# 12. Firewall
# ---------------------------------------------------------------------------
if [[ "$SYSINTRO_FIREWALL" -eq 1 ]]; then
    info "=== Configuring ufw firewall ==="
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp  comment 'SSH'
    ufw allow 80/tcp  comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    ufw --force enable
    info "Firewall enabled."
else
    info "Firewall configuration skipped (--no-firewall)."
fi

# ---------------------------------------------------------------------------
# 13. Post-install summary
# ---------------------------------------------------------------------------
if [[ "$SYSINTRO_TLS" -eq 1 ]]; then
    PROTO="https"
else
    PROTO="http"
fi

cat <<SUMMARY

============================================================
SysIntro installiert!
------------------------------------------------------------
URL:           ${PROTO}://${SYSINTRO_DOMAIN}
Admin-Login:   admin@demo.local / demo1234   <-- BITTE ÄNDERN!
Service:       systemctl status sysintro
Logs:          journalctl -u sysintro -f
App-Verz.:     ${SYSINTRO_HOME}
============================================================

ACHTUNG: Bitte das Demo-Passwort nach dem ersten Login sofort ändern!
Weitere Hinweise: ${SYSINTRO_HOME}/app/deploy/post_install.md

SUMMARY
