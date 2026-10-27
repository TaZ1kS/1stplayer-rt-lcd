#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Live CPU/GPU telemetry for the 1st Player RT5/RT7/RT9 case LCD.

Reads temperatures and load from Linux sysfs/procfs and renders them into the
64-byte HID report expected by the display. Defaults to the stable
/dev/1stplayer-rt-lcd symlink and falls back to /dev/hidraw3. Pass an explicit
path as the first argument to override it.
"""
import time
import sys
import os
import glob

DEV_PATH = "/dev/1stplayer-rt-lcd"
if not os.path.exists(DEV_PATH):
    DEV_PATH = "/dev/hidraw3"

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
    def __init__(self, dev_path=DEV_PATH):
        self.dev_path = dev_path
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
    dev_node = sys.argv[1] if len(sys.argv) > 1 else DEV_PATH
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
