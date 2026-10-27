<p align="center">
  <img src="assets/banner.svg" alt="1st Player RT LCD — Linux toolkit" width="100%">
</p>

<h1 align="center">1st Player RT LCD</h1>

<p align="center">
  <b>Linux control for the built-in USB LCD display of 1st Player RT5 / RT7 / RT9 cases.</b><br>
  CPU/GPU telemetry, a scrolling marquee and a panel stress test — pure Python, no vendor app.
</p>

<p align="center">
  <img alt="Linux" src="https://img.shields.io/badge/Linux-hidraw-0f172a?style=for-the-badge&logo=linux&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="USB HID" src="https://img.shields.io/badge/USB-HID-7c3aed?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#scripts">Scripts</a> ·
  <a href="#frame-format">Frame format</a> ·
  <a href="#segment-map">Segment map</a> ·
  <a href="README.md">Українська</a>
</p>

---

> [!NOTE]
> This is an unofficial community project. It is not affiliated with 1st Player and contains no vendor code or binaries. Use it at your own risk.

## Overview

| | |
|---|---|
| **Case** | 1st Player RT5 / RT7 / RT9 with a built-in 6-digit 7-segment LCD |
| **Interface** | USB HID, 64-byte output reports, `/dev/hidraw*` |
| **OS** | Linux (`hidraw`, `sysfs`, `hwmon`) |
| **Dependencies** | Python 3.8+ standard library only |
| **Test unit** | `5131:2007`, exposed as `/dev/hidraw3` on the test machine |

> [!NOTE]
> On the test machine `lsusb` labels this device as `MSR MSR-101U Mini HID magnetic card reader` — that is just a VID/PID match in the `usb.ids` database. Look for the `hidraw` node that appears when the case display is connected and for 64-byte HID reports.

The panel has six 7-segment digits (three for CPU, three for GPU), two 10-segment bars and status labels such as `CPU`, `GPU`, `USAGE`, `%` and `°C`. These scripts implement the most useful mode: live CPU/GPU temperature and load.

## Quick start

```bash
git clone https://github.com/TaZ1kS/1stplayer-rt-lcd.git
cd 1stplayer-rt-lcd

# One-time hidraw permissions. Check VID/PID in the udev rule first!
sudo install -m 644 udev/99-1stplayer-rt-lcd.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

# Replug the display's USB cable, then:
python3 scripts/lcd.py
```

With multiple hidraw devices, pass the path explicitly:

```bash
ls -l /dev/hidraw*
python3 scripts/lcd.py /dev/hidraw5
```

Or use the Makefile:

```bash
make monitor              # python3 scripts/lcd.py
make marquee              # python3 scripts/lcd_sym.py
make stress               # python3 scripts/unlock.py
```

## Scripts

| Script | What it does | Refresh |
|---|---|---|
| [`lcd.py`](scripts/lcd.py) | Live CPU/GPU temperatures on the digits, load on the bars | 1 Hz |
| [`lcd_sym.py`](scripts/lcd_sym.py) | Scrolling text on the six digits; Latin, Cyrillic and digits | 0.25 s per step |
| [`unlock.py`](scripts/unlock.py) | All-segments stress test at a configurable refresh rate | 1–200 Hz |

### `lcd.py`

```bash
python3 scripts/lcd.py
```

Sensor discovery:

| Metric | Source |
|---|---|
| CPU temperature | `hwmon` named `coretemp`, `k10temp`, `zenpower` or `cpu_thermal`, `temp1_input` |
| CPU load | `/proc/stat`, idle/total delta |
| GPU temperature | `hwmon` under `/sys/class/drm/card*/device/`, `temp1_input` |
| GPU load | `/sys/class/drm/card*/device/gpu_busy_percent` (AMD) |

Temperatures use three digits; load uses a 10-segment bar (~10% per segment). Missing sensors fall back to `0`. `gpu_busy_percent` is AMD-specific; NVIDIA load is not supported by this script.

### `lcd_sym.py`

```bash
python3 scripts/lcd_sym.py
```

Type text and press Enter; an empty line is ignored and `q` quits. A six-character window scrolls with a 0.25 s step, padded with six spaces at both ends.

Supported characters: digits `0–9`, space, `-`, `_`; Latin `a b c d e f g h i j l n o p r s t u y z`; Cyrillic `а б в г д е є з и і ї к л м н о п р с т у ч ш ь`. Unsupported characters are rendered as blanks. The font is a dictionary in `lcd_sym.py` and can be extended.

### `unlock.py`

```bash
python3 scripts/unlock.py
```

Alternates all-on/all-off frames. Enter a target frequency in Hz (`2`, `10`, `60`, `120`, …); the status line shows the target and actual FPS. `q` or `Ctrl+C` exits and clears the panel.

> [!WARNING]
> The all-on frame writes `0xFF` to bytes 24–53, including service bits. The screen may flicker, blank or behave oddly — that is expected for a stress test. Do not use this as a normal display mode.

## Frame format

One frame is exactly 64 bytes, written to the hidraw node in a single `write()`. There is no ACK.

| Byte | Value | Purpose |
|---:|---|---|
| 0 | `seq` | Counter: starts at `0x61`, then `+1 & 0xFF` |
| 1 | `0x00` | Fixed header |
| 2 | `0x02` | Fixed header |
| 3–23 | `0x00` | Reserved |
| 24–39 | `0x00`* | Service/static icons |
| 40–52 | bitmap | Digits, bars and labels |
| 53–63 | `0x00` | Reserved |

\* Vendor frames contain a baseline icon state here; `lcd.py` and `lcd_sym.py` write zeros, while `unlock.py` writes `0xFF`.

Bits are zero-indexed: `0x01` is bit 0, `0x80` is bit 7. To light segment `A` of the first CPU digit, set bit 0 of byte 40. A blank frame is `61 00 02` followed by 61 zeros. The all-on frame is `61 00 02`, 21 zeros, 30 bytes of `FF` (bytes 24–53) and 10 zeros.

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the full breakdown.

## Segment map

<p align="center">
  <img src="assets/panel-map.svg" alt="Panel layout: six 7-segment digits and two 10-segment bars" width="100%">
</p>

Addresses are written as `byte.bit`.

| Digit | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **CPU1** | 40.0 | 42.0 | 52.0 | 50.0 | 48.0 | 44.0 | 46.0 |
| **CPU2** | 52.1 | 44.1 | 42.1 | 46.1 | 40.1 | 50.1 | 48.1 |
| **CPU3** | 42.2 | 50.2 | 44.2 | 52.2 | 48.2 | 40.2 | 46.2 |
| **GPU1** | 50.3 | 40.3 | 46.3 | 48.3 | 44.3 | 52.3 | 42.3 |
| **GPU2** | 44.4 | 42.4 | 52.4 | 48.4 | 50.4 | 40.4 | 46.4 |
| **GPU3** | 48.5 | 50.5 | 42.5 | 44.5 | 40.5 | 52.5 | 46.5 |

CPU2 splits `D` and `G`: `D = 46.1`, `G = 46.2`.

| Bar | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **CPU** | 46.6 | 48.6 | 50.6 | 52.6 | 41.0 | 45.0 | 43.0 | 42.6 | 44.6 | 40.6 |
| **GPU** | 49.0 | 51.0 | 40.7 | 42.7 | 44.7 | 47.0 | 52.7 | 50.7 | 48.7 | 46.7 |

Labels: `CPU` = 41.2, `GPU` = 51.2, `CPU %` = 41.1, `GPU %` = 51.1, `CPU °C` = 45.1, `GPU °C` = 47.1, `CPU USAGE` = 43.2, `GPU USAGE` = 47.2.

Full byte/bit table: [`docs/SEGMENT_MAP.md`](docs/SEGMENT_MAP.md).

## Compatibility

| Component | Status |
|---|---|
| Linux + hidraw | ✅ |
| Windows | ❌ — use [1ST PC Monitoring](https://1stplayer.com/download/) |
| Intel CPU temperature | ✅ `coretemp` |
| AMD CPU temperature | ✅ `k10temp` / `zenpower` |
| AMD GPU temperature + load | ✅ `amdgpu` |
| NVIDIA GPU load | ❌ `gpu_busy_percent` is not used |
| NVIDIA GPU temperature | ⚠️ only if the driver exposes `temp1_input` |
| Other cases with a similar LCD | ⚠️ segment map may differ |

## Safety

The scripts write to the selected hidraw node. Make sure it is the display, not a keyboard, mouse or card reader — especially with `unlock.py`, which sends `0xFF` to bytes 24–53. Check `lsusb`, `udevadm info` and `ls -l /dev/hidraw*` before running anything. This project is not affiliated with 1st Player; use it at your own risk.

## License

[MIT](LICENSE) © 2026 TaZ1kS
