#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Remove the 1st Player RT LCD systemd service and installed files.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
    echo "Run as root: sudo ./uninstall.sh" >&2
    exit 1
fi

systemctl disable --now 1stplayer-rt-lcd.service 2>/dev/null || true
rm -f /etc/systemd/system/1stplayer-rt-lcd.service
rm -f /etc/udev/rules.d/99-1stplayer-rt-lcd.rules
rm -f /dev/1stplayer-rt-lcd
rm -rf /opt/1stplayer-rt-lcd

systemctl daemon-reload
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

echo "1st Player RT LCD service removed."
