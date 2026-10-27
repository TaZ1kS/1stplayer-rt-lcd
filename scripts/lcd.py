#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Live CPU/GPU telemetry for the 1st Player RT5/RT7/RT9 case LCD.

Reads temperatures and load from Linux sysfs/procfs and renders them into the
64-byte HID report expected by the display. The device is auto-detected via
/dev/1stplayer-rt-lcd or USB ID 5131:2007; pass an explicit hidraw path as the
first argument to override it. --wait makes the script wait for the device to
appear; the systemd service uses it because the USB display may enumerate after
boot.
"""
import time
import sys
import os
import glob

# --- АВТОВИЗНАЧЕННЯ HIDRAW-ВУЗЛА ---
USB_VID = 0x5131
USB_PID = 0x2007
STABLE_PATH = "/dev/1stplayer-rt-lcd"


def _hid_id(sys_node):
    """Повертає (VID, PID) з sysfs uevent або None."""
    try:
        with open(os.path.join(sys_node, "device", "uevent"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("HID_ID="):
                    _, vid, pid = line.strip().split("=", 1)[1].split(":")
                    return int(vid, 16), int(pid, 16)
    except (OSError, ValueError):
        pass
    return None


def _hidraw_devices():
    """Список (dev_node, (VID, PID) або None) для всіх hidraw."""
    result = []
    for sys_node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        result.append(("/dev/" + os.path.basename(sys_node), _hid_id(sys_node)))
    return result


def find_lcd_device(explicit=None):
    """Знаходить вузол дисплея: аргумент -> symlink -> VID/PID."""
    if explicit:
        return explicit
    if os.path.exists(STABLE_PATH):
        return STABLE_PATH

    devices = _hidraw_devices()
    matches = [node for node, ids in devices if ids == (USB_VID, USB_PID)]
    if len(matches) == 1:
        return matches[0]

    lines = []
    if len(matches) > 1:
        lines.append(f"[!] Знайдено кілька дисплеїв {USB_VID:04x}:{USB_PID:04x}:")
        lines.extend(f"      {node}" for node in matches)
        lines.append("    Вкажи потрібний шлях явно.")
    else:
        lines.append(f"[!] Дисплей 1st Player ({USB_VID:04x}:{USB_PID:04x}) не знайдено.")
        if devices:
            lines.append("    Доступні hidraw-пристрої:")
            for node, ids in devices:
                hid = f"{ids[0]:04x}:{ids[1]:04x}" if ids else "HID ID недоступний"
                lines.append(f"      {node}  ({hid})")
            lines.append("    Вкажи шлях явно: python3 scripts/lcd.py /dev/hidrawN")
        else:
            lines.append("    У системі немає /dev/hidraw*.")
            lines.append("    Перевір, чи підключено USB-кабель дисплея.")
        lines.append("    Або встанови udev-правило: sudo ./install.sh")
    raise SystemExit("\n".join(lines))


def wait_for_lcd_device(explicit=None, timeout=120.0, interval=2.0):
    """Чекає, поки вузол дисплея з'явиться (режим systemd-сервісу)."""
    deadline = time.monotonic() + timeout
    announced = False
    last_error = None

    while True:
        try:
            node = find_lcd_device(explicit)
        except SystemExit as exc:
            last_error = exc
        else:
            if os.path.exists(node):
                return node
            last_error = SystemExit(
                f"[!] Пристрій {node} не з'явився за {timeout:g} с.\n"
                "    Перевір USB-кабель і udev-правило: sudo ./install.sh"
            )

        if not announced:
            print(f"[i] Дисплей ще не готовий, чекаю до {timeout:g} с...", flush=True)
            announced = True

        if time.monotonic() >= deadline:
            raise last_error
        time.sleep(interval)

# Точна мапа 7-сегментних розрядів [A, B, C, D, E, F, G]
SEGMENT_MAP = {
    'CPU1': [(40,0), (42,0), (52,0), (50,0), (48,0), (44,0), (46,0)],
    'CPU2': [(52,1), (44,1), (42,1), (46,1), (40,1), (50,1), (48,1)],
    'CPU3': [(42,2), (50,2), (44,2), (52,2), (48,2), (40,2), (46,2)],
    'GPU1': [(50,3), (40,3), (46,3), (48,3), (44,3), (52,3), (42,3)],
    'GPU2': [(44,4), (42,4), (52,4), (48,4), (50,4), (40,4), (46,4)],
    'GPU3': [(48,5), (50,5), (42,5), (44,5), (40,5), (52,5), (46,5)]
}

# 7-сегментні маски цифр (0-9)
DIGITS = {
    0: [1,1,1,1,1,1,0],
    1: [0,1,1,0,0,0,0],
    2: [1,1,0,1,1,0,1],
    3: [1,1,1,1,0,0,1],
    4: [0,1,1,0,0,1,1],
    5: [1,0,1,1,0,1,1],
    6: [1,0,1,1,1,1,1],
    7: [1,1,1,0,0,0,0],
    8: [1,1,1,1,1,1,1],
    9: [1,1,1,1,0,1,1],
    ' ': [0,0,0,0,0,0,0]
}

# Поділки 10-сегментних смужок навантаження (1..10)
BAR_CPU = [(46,6), (48,6), (50,6), (52,6), (41,0), (45,0), (43,0), (42,6), (44,6), (40,6)]
BAR_GPU = [(49,0), (51,0), (40,7), (42,7), (44,7), (47,0), (52,7), (50,7), (48,7), (46,7)]


class SystemTelemetryLCD:
    def __init__(self, dev_path=None):
        self.dev_path = dev_path or find_lcd_device()
        self.seq_id = 0x61
        self.prev_idle = 0
        self.prev_total = 0
        
        self.cpu_temp_file = self._find_cpu_temp_file()
        self.gpu_temp_file = self._find_gpu_temp_file()
        self.gpu_busy_file = self._find_gpu_busy_file()

    def _get_seq(self):
        curr = self.seq_id
        self.seq_id = (self.seq_id + 1) & 0xFF
        return curr

    def _set_bit(self, buf, byte_idx, bit_idx):
        if byte_idx >= 0 and bit_idx >= 0:
            buf[byte_idx] |= (1 << bit_idx)

    # --- ДЕТЕКЦІЯ СЕНСОРІВ В АРЧ ЛІНУКС ---
    def _find_cpu_temp_file(self):
        """Шукає датчик температури ЦП у sysfs hwmon"""
        for hwmon in glob.glob('/sys/class/hwmon/hwmon*'):
            name_file = os.path.join(hwmon, 'name')
            if os.path.exists(name_file):
                with open(name_file, 'r') as f:
                    name = f.read().strip()
                if name in ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal']:
                    temp_input = os.path.join(hwmon, 'temp1_input')
                    if os.path.exists(temp_input):
                        return temp_input
        # Запасний варіант: перший знайдений temp1_input
        for temp_input in glob.glob('/sys/class/hwmon/hwmon*/temp1_input'):
            return temp_input
        return None

    def _find_gpu_temp_file(self):
        """Шукає датчик температури GPU AMD Radeon"""
        for card in glob.glob('/sys/class/drm/card*/device/hwmon/hwmon*'):
            temp_input = os.path.join(card, 'temp1_input')
            if os.path.exists(temp_input):
                return temp_input
        for hwmon in glob.glob('/sys/class/hwmon/hwmon*'):
            name_file = os.path.join(hwmon, 'name')
            if os.path.exists(name_file):
                with open(name_file, 'r') as f:
                    if f.read().strip() == 'amdgpu':
                        return os.path.join(hwmon, 'temp1_input')
        return None

    def _find_gpu_busy_file(self):
        """Шукає вузол завантаження GPU AMD Radeon"""
        for i in range(4):
            path = f"/sys/class/drm/card{i}/device/gpu_busy_percent"
            if os.path.exists(path):
                return path
        return None

    # --- ЗЧИТУВАННЯ МЕТРИК ---
    def get_cpu_usage(self) -> int:
        try:
            with open('/proc/stat', 'r') as f:
                fields = f.readline().split()[1:]
                vals = [int(x) for x in fields]
                idle = vals[3] + vals[4]
                total = sum(vals)

                diff_idle = idle - self.prev_idle
                diff_total = total - self.prev_total

                self.prev_idle = idle
                self.prev_total = total

                if diff_total == 0:
                    return 0
                return max(0, min(100, int((1.0 - (diff_idle / diff_total)) * 100)))
        except Exception:
            return 0

    def get_cpu_temp(self) -> int:
        if not self.cpu_temp_file:
            return 0
        try:
            with open(self.cpu_temp_file, 'r') as f:
                return int(int(f.read().strip()) / 1000)
        except Exception:
            return 0

    def get_gpu_usage(self) -> int:
        if not self.gpu_busy_file:
            return 0
        try:
            with open(self.gpu_busy_file, 'r') as f:
                return max(0, min(100, int(f.read().strip())))
        except Exception:
            return 0

    def get_gpu_temp(self) -> int:
        if not self.gpu_temp_file:
            return 0
        try:
            with open(self.gpu_temp_file, 'r') as f:
                return int(int(f.read().strip()) / 1000)
        except Exception:
            return 0

    # --- ОНОВЛЕННЯ ДИСПЛЕЯ ---
    def update_display(self, cpu_temp: int, cpu_usage: int, gpu_temp: int, gpu_usage: int):
        buf = bytearray(64)
        buf[0] = self._get_seq()
        buf[1] = 0x00
        buf[2] = 0x02

        # Увімкнення текстових ікон:
        # Цифри показують температуру °C, смужки — завантаження USAGE
        self._set_bit(buf, 41, 2) # CPU label
        self._set_bit(buf, 51, 2) # GPU label
        self._set_bit(buf, 43, 2) # CPU USAGE
        self._set_bit(buf, 47, 2) # GPU USAGE
        self._set_bit(buf, 45, 1) # CPU °C
        self._set_bit(buf, 47, 1) # GPU °C

        # Рендеринг температур у цифри (3 розряди)
        c_str = f"{cpu_temp:>3}"
        g_str = f"{gpu_temp:>3}"

        for idx, char in enumerate(c_str):
            val = int(char) if char != ' ' else ' '
            mask = DIGITS[val]
            digit_name = f"CPU{idx+1}"
            for seg_i, on in enumerate(mask):
                if on:
                    b_idx, bit_i = SEGMENT_MAP[digit_name][seg_i]
                    self._set_bit(buf, b_idx, bit_i)

        for idx, char in enumerate(g_str):
            val = int(char) if char != ' ' else ' '
            mask = DIGITS[val]
            digit_name = f"GPU{idx+1}"
            for seg_i, on in enumerate(mask):
                if on:
                    b_idx, bit_i = SEGMENT_MAP[digit_name][seg_i]
                    self._set_bit(buf, b_idx, bit_i)

        # Рендеринг завантаження (%) у 10-сегментні смужки
        c_bars = min(10, max(0, int(cpu_usage / 10)))
        g_bars = min(10, max(0, int(gpu_usage / 10)))

        for i in range(c_bars):
            b_idx, bit_i = BAR_CPU[i]
            self._set_bit(buf, b_idx, bit_i)

        for i in range(g_bars):
            b_idx, bit_i = BAR_GPU[i]
            self._set_bit(buf, b_idx, bit_i)

        # Запис кадру в HID-вузол
        try:
            with open(self.dev_path, "wb") as dev:
                dev.write(buf)
                dev.flush()
        except Exception as e:
            print(f"[!] Помилка запису в {self.dev_path}: {e}")

def main():
    args = sys.argv[1:]
    wait = "--wait" in args
    args = [arg for arg in args if arg != "--wait"]
    explicit = args[0] if args else None
    dev_node = (
        wait_for_lcd_device(explicit)
        if wait
        else find_lcd_device(explicit)
    )
    if os.path.exists(dev_node) and not os.access(dev_node, os.W_OK):
        raise SystemExit(
            f"[!] Немає доступу на запис до {dev_node}.\n"
            "    Встанови udev-правило: sudo ./install.sh\n"
            "    Або запусти з sudo: sudo python3 scripts/lcd.py"
        )
    monitor = SystemTelemetryLCD(dev_node)

    print(f"[*] Телеметрію запущено ({dev_node}). Натисни Ctrl+C для виходу.")
    print(f"    CPU Temp file: {monitor.cpu_temp_file}")
    print(f"    GPU Temp file: {monitor.gpu_temp_file}")
    print(f"    GPU Busy file: {monitor.gpu_busy_file}")

    # Початковий розрахунок тиків CPU
    monitor.get_cpu_usage()
    time.sleep(0.5)

    try:
        while True:
            c_temp = monitor.get_cpu_temp()
            c_usage = monitor.get_cpu_usage()
            g_temp = monitor.get_gpu_temp()
            g_usage = monitor.get_gpu_usage()

            monitor.update_display(
                cpu_temp=c_temp,
                cpu_usage=c_usage,
                gpu_temp=g_temp,
                gpu_usage=g_usage
            )
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[*] Моніторинг зупинено.")

if __name__ == "__main__":
    main()
