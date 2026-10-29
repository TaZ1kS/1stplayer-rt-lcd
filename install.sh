#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Install the 1st Player RT LCD systemd service.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/opt/1stplayer-rt-lcd}"
UNIT="${UNIT:-/etc/systemd/system/1stplayer-rt-lcd.service}"
UDEV="${UDEV:-/etc/udev/rules.d/99-1stplayer-rt-lcd.rules}"
CONFIG="${CONFIG:-/etc/1stplayer-rt-lcd.conf}"

INSTALL_SERVICE=1
ANIMATION=""
USE_TUI=1

usage() {
    cat <<'EOF'
Usage: sudo ./install.sh [OPTIONS]

  --no-service        install files and the udev rule without enabling the systemd unit
  --animation MODE    animation style: parallel (default), sequence or off
  --no-tui            do not show the animation menu
  -h, --help          show this help

Without --animation or --no-tui, an interactive terminal gets a menu.
EOF
}

die() {
    echo "$*" >&2
    exit 1
}

valid_animation() {
    case "$1" in
        parallel|sequence|off) return 0 ;;
        *) return 1 ;;
    esac
}

current_animation() {
    local value=""
    if [[ -r "${CONFIG}" ]]; then
        value=$(sed -n 's/^[[:space:]]*ANIMATION[[:space:]]*=[[:space:]]*//p' "${CONFIG}" | tail -n 1)
        value="${value//[[:space:]]/}"
        value="${value//\"/}"
        value="${value//\'/}"
    fi
    if valid_animation "${value}"; then
        printf '%s\n' "${value}"
    else
        printf '%s\n' "parallel"
    fi
}

choose_animation_tui() {
    local current choice
    current=$(current_animation)

    if command -v whiptail >/dev/null 2>&1; then
        if ! choice=$(whiptail --title "1st Player RT LCD" \
            --default-item "${current}" \
            --menu "Animation style:" 18 84 3 \
            "parallel" "All 6 digits fill around the perimeter together + bars in parallel (recommended)" \
            "sequence" "Digits fill one by one from left to right + bars in parallel" \
            "off"      "No animation (the panel is cleared on exit)" \
            3>&1 1>&2 2>&3); then
            echo "Cancelled." >&2
            exit 1
        fi
    elif command -v dialog >/dev/null 2>&1; then
        if ! choice=$(dialog --stdout --title "1st Player RT LCD" \
            --default-item "${current}" \
            --menu "Animation style:" 18 84 3 \
            "parallel" "All 6 digits fill around the perimeter together + bars in parallel (recommended)" \
            "sequence" "Digits fill one by one from left to right + bars in parallel" \
            "off"      "No animation (the panel is cleared on exit)"); then
            echo "Cancelled." >&2
            exit 1
        fi
    else
        echo
        echo "Animation style:"
        echo "  1) parallel  all 6 digits fill around the perimeter together, bars in parallel (recommended)"
        echo "  2) sequence  digits fill one by one, bars in parallel"
        echo "  3) off       no animation"
        while true; do
            read -r -p "Choice [1-3, Enter = ${current}]: " answer || answer=""
            case "${answer:-}" in
                1) choice="parallel"; break ;;
                2) choice="sequence"; break ;;
                3) choice="off"; break ;;
                "") choice="${current}"; break ;;
                *) echo "Invalid choice." ;;
            esac
        done
    fi

    ANIMATION="${choice}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-service) INSTALL_SERVICE=0; shift ;;
        --animation)
            [[ $# -ge 2 ]] || die "--animation requires a value"
            ANIMATION="$2"
            shift 2
            ;;
        --animation=*)
            ANIMATION="${1#*=}"
            shift
            ;;
        --no-tui) USE_TUI=0; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

if [[ -n "${ANIMATION}" ]] && ! valid_animation "${ANIMATION}"; then
    die "Unknown animation mode: ${ANIMATION} (use parallel, sequence or off)"
fi

if [[ ${EUID} -ne 0 ]]; then
    echo "Run as root: sudo ./install.sh" >&2
    exit 1
fi

if [[ -z "${ANIMATION}" ]]; then
    if [[ ${USE_TUI} -eq 1 && -t 0 && -t 1 ]]; then
        choose_animation_tui
    else
        ANIMATION=$(current_animation)
    fi
fi

if ! valid_animation "${ANIMATION}"; then
    die "Unknown animation mode: ${ANIMATION} (use parallel, sequence or off)"
fi

install -d "${PREFIX}/scripts" "${PREFIX}/docs" "${PREFIX}/assets"
install -m 755 "${ROOT}/scripts/lcd.py" "${ROOT}/scripts/lcd_sym.py" "${ROOT}/scripts/unlock.py" "${PREFIX}/scripts/"
install -m 644 "${ROOT}/README.md" "${ROOT}/README.en.md" "${ROOT}/CHANGELOG.md" "${ROOT}/LICENSE" "${PREFIX}/"
install -m 644 "${ROOT}"/docs/*.md "${PREFIX}/docs/"
install -m 644 "${ROOT}"/assets/*.svg "${PREFIX}/assets/"
install -m 644 "${ROOT}/udev/99-1stplayer-rt-lcd.rules" "${UDEV}"
install -m 644 "${ROOT}/systemd/1stplayer-rt-lcd.service" "${UNIT}"

install -d "$(dirname "${CONFIG}")"
{
    echo "# 1st Player RT LCD settings"
    echo "# Animation style: parallel | sequence | off"
    echo "ANIMATION=${ANIMATION}"
} > "${CONFIG}"
chmod 644 "${CONFIG}"

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
echo "Animation: ${ANIMATION}"
if [[ ${INSTALL_SERVICE} -eq 1 ]]; then
    echo "Status:  systemctl status 1stplayer-rt-lcd.service"
    echo "Logs:    journalctl -u 1stplayer-rt-lcd.service -f"
else
    echo "System service not enabled (--no-service)."
    echo "For a user service: make install-user-service"
fi
