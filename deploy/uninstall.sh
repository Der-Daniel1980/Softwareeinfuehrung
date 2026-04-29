#!/usr/bin/env bash
# deploy/uninstall.sh — SysIntro clean removal
# Usage: sudo bash uninstall.sh --yes
# The data directory is intentionally left in place.
set -euo pipefail

SYSINTRO_HOME="${SYSINTRO_HOME:-/opt/sysintro}"
CONFIRMED=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

usage() {
    cat <<EOF
Usage: sudo bash uninstall.sh --yes [--home /opt/sysintro]

Options:
  --yes           Required confirmation flag — actually perform the removal
  --home PATH     Override install directory (default: /opt/sysintro)
  --help          Show this message
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Parse CLI flags
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes)     CONFIRMED=1; shift ;;
        --home)    SYSINTRO_HOME="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) error "Unknown option: $1 — run with --help for usage" ;;
    esac
done

if [[ "$CONFIRMED" -ne 1 ]]; then
    cat <<MSG
This script will remove:
  - systemd unit   /etc/systemd/system/sysintro.service
  - nginx site     /etc/nginx/sites-enabled/sysintro
                   /etc/nginx/sites-available/sysintro
  - system user    sysintro

The application data directory ($SYSINTRO_HOME) will NOT be deleted.

To proceed, run:
  sudo bash uninstall.sh --yes
MSG
    exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
    error "This script must be run as root. Use: sudo bash $0 --yes"
fi

# ---------------------------------------------------------------------------
# Stop and disable systemd unit
# ---------------------------------------------------------------------------
info "Stopping and disabling sysintro service..."
if systemctl is-active --quiet sysintro 2>/dev/null; then
    systemctl stop sysintro
fi
if systemctl is-enabled --quiet sysintro 2>/dev/null; then
    systemctl disable sysintro
fi
if [[ -f /etc/systemd/system/sysintro.service ]]; then
    rm -f /etc/systemd/system/sysintro.service
    info "Removed /etc/systemd/system/sysintro.service"
fi
systemctl daemon-reload

# ---------------------------------------------------------------------------
# Remove nginx site
# ---------------------------------------------------------------------------
info "Removing nginx configuration..."
rm -f /etc/nginx/sites-enabled/sysintro
rm -f /etc/nginx/sites-available/sysintro
if nginx -t 2>/dev/null; then
    systemctl reload nginx
    info "nginx reloaded."
else
    info "nginx config test failed after removal — skipping reload (manual check needed)."
fi

# ---------------------------------------------------------------------------
# Remove system user (home dir kept intentionally)
# ---------------------------------------------------------------------------
info "Removing system user 'sysintro'..."
if id sysintro &>/dev/null; then
    # Do NOT pass --remove: the data directory must survive
    userdel sysintro
    info "User 'sysintro' removed."
else
    info "User 'sysintro' not found — skipping."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
cat <<DONE

============================================================
SysIntro wurde entfernt.
------------------------------------------------------------
Datenverzeichnis $SYSINTRO_HOME bleibt erhalten.
Manuell löschen mit:

  rm -rf $SYSINTRO_HOME

============================================================
DONE
