#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""All-segments stress test for the 1st Player RT5/RT7/RT9 case LCD.

Alternates all-on/all-off frames at a configurable refresh rate and reports
the actual FPS. The panel is cleared when the script exits.
"""
import time
import sys
import os
import threading

DEV_PATH = "/dev/1stplayer-rt-lcd"
if not os.path.exists(DEV_PATH):
    DEV_PATH = "/dev/hidraw3"

# Всі байти для увімкнення абсолютно всіх сегментів на екрані
ALL_ON_FRAME = bytearray([
    0x61, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
    0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])

ALL_OFF_FRAME = bytearray([
    0x61, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])

class LCDSpeedTester:
    def __init__(self, dev_path=DEV_PATH):
        self.dev_path = dev_path
        self.seq_id = 0x61
        self.target_hz = 10.0  # Початкова частота 10 Гц
        self.mode = "strobe"   # Режими: strobe (мигання), counter (надшвидкий рахунок)
        self.running = True
        self.actual_fps = 0.0

    def _get_seq(self):
        curr = self.seq_id
        self.seq_id = (self.seq_id + 1) & 0xFF
        return curr

    def _write_packet(self, packet: bytearray):
        packet[0] = self._get_seq()
        try:
            with open(self.dev_path, "wb") as dev:
                dev.write(packet)
                dev.flush()
        except Exception:
            pass

    def render_loop(self):
        frame_state = False
        counter_val = 0
        frames_count = 0
        last_fps_calc = time.time()

        while self.running:
            t_start = time.time()

            if self.mode == "strobe":
                # Режим стробоскопа: перемикання ВКЛ / ВИКЛ
                if frame_state:
                    self._write_packet(ALL_ON_FRAME)
                else:
                    self._write_packet(ALL_OFF_FRAME)
                frame_state = not frame_state

            frames_count += 1
            now = time.time()
            if now - last_fps_calc >= 1.0:
                self.actual_fps = frames_count / (now - last_fps_calc)
                frames_count = 0
                last_fps_calc = now

            # Затримка відповідно до заданої частоти Гц
            target_delay = 1.0 / self.target_hz if self.target_hz > 0 else 0.1
            elapsed = time.time() - t_start
            sleep_time = target_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

def main():
    dev_node = sys.argv[1] if len(sys.argv) > 1 else DEV_PATH
    tester = LCDSpeedTester(dev_node)

    # Запускаємо рендеринг у фоновому потоці
    thread = threading.Thread(target=tester.render_loop, daemon=True)
    thread.start()

    print("=" * 65)
    print(f'[*] ТЕСТ "РОЗГОНУ" LCD ДИСПЛЕЯ НА {dev_node}')
    print("=" * 65)
    print("      Команди:")
    print("      - Введи число (напр. 2, 10, 30, 60, 120, 200) -> встановити Гц")
    print("      - 'q' -> вийти з тесту")
    print("=" * 65)

    try:
        while True:
            time.sleep(0.2)
            sys.stdout.write(f"\r[Поточна частота: {tester.target_hz:.1f} Гц | Фактичний FPS: {tester.actual_fps:.1f}] Нова частота (Гц): ")
            sys.stdout.flush()

            user_input = input().strip()

            if user_input.lower() == 'q':
                tester.running = False
                break

            try:
                val = float(user_input)
                if val > 0:
                    tester.target_hz = val
                    print(f"   [+] Частоту змінено на {val} Гц ({1000/val:.1f} мс/кадр)")
                else:
                    print("   [!] Значення має бути більше 0")
            except ValueError:
                print("   [!] Введи число у Гц (наприклад: 20 або 60)")

    except KeyboardInterrupt:
        print("\n[*] Завершено.")
        tester.running = False

    # Повертаємо пустий екран при виході
    tester._write_packet(ALL_OFF_FRAME)

if __name__ == "__main__":
    main()
