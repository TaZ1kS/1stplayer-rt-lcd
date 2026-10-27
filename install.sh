#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Install the 1st Player RT LCD systemd service.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="/opt/1stplayer-rt-lcd"
UNIT="/etc/systemd/system/1stplayer-rt-lcd.service"
UDEV="/etc/udev/rules.d/99-1stplayer-rt-lcd.rules"

INSTALL_SERVICE=1

usage() {
    cat <<'EOF'
Usage: sudo ./install.sh [--no-service]

  --no-service   install files and the udev rule without enabling the systemd unit
  -h, --help     show this help
EOF
}

case "${1:-}" in
    --no-service) INSTALL_SERVICE=0 ;;
    -h|--help) usage; exit 0 ;;
    "") ;;
    *) usage >&2; exit 2 ;;
esac

if [[ ${EUID} -ne 0 ]]; then
    echo "Run as root: sudo ./install.sh" >&2
    exit 1
fi

install -d "${PREFIX}/scripts" "${PREFIX}/docs" "${PREFIX}/assets"
install -m 755 "${ROOT}/scripts/lcd.py" "${ROOT}/scripts/lcd_sym.py" "${ROOT}/scripts/unlock.py" "${PREFIX}/scripts/"
install -m 644 "${ROOT}/README.md" "${ROOT}/README.en.md" "${ROOT}/CHANGELOG.md" "${ROOT}/LICENSE" "${PREFIX}/"
install -m 644 "${ROOT}"/docs/*.md "${PREFIX}/docs/"
install -m 644 "${ROOT}"/assets/*.svg "${PREFIX}/assets/"
install -m 644 "${ROOT}/udev/99-1stplayer-rt-lcd.rules" "${UDEV}"
install -m 644 "${ROOT}/systemd/1stplayer-rt-lcd.service" "${UNIT}"

systemctl daemon-reload

# A udev problem must not prevent the service from being installed/enabled.
if ! udevadm control --reload-rules; then
    echo "Warning: could not reload udev rules" >&2
fi
if ! udevadm trigger --subsystem-match=hidraw; then
    echo "Warning: could not trigger udev for hidraw" >&2
fi

if [[ ${INSTALL_SERVICE} -eq 1 ]]; then
    systemctl enable 1stplayer-rt-lcd.service
    systemctl reset-failed 1stplayer-rt-lcd.service 2>/dev/null || true
    systemctl restart 1stplayer-rt-lcd.service
fi

if [[ -e /dev/1stplayer-rt-lcd ]]; then
    echo "Device: /dev/1stplayer-rt-lcd"
else
    echo "Warning: /dev/1stplayer-rt-lcd not found yet. Replug the display's USB cable." >&2
fi

echo
echo "Installed to ${PREFIX}"
if [[ ${INSTALL_SERVICE} -eq 1 ]]; then
    echo "Status:  systemctl status 1stplayer-rt-lcd.service"
    echo "Logs:    journalctl -u 1stplayer-rt-lcd.service -f"
else
    echo "System service not enabled (--no-service)."
    echo "For a user service: make install-user-service"
fi
