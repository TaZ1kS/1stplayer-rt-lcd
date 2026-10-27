#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Scrolling text for the 1st Player RT5/RT7/RT9 case LCD.

Six 7-segment digits are used as a tiny marquee. The font covers digits,
basic Latin and a subset of Cyrillic letters.
"""
import time
import sys

DEV_PATH = "/dev/hidraw3"

# Точна мапа 6 розрядів у ряд (зліва направо: CPU1-3, GPU1-3)
DIGIT_NODES = ['CPU1', 'CPU2', 'CPU3', 'GPU1', 'GPU2', 'GPU3']

SEGMENT_MAP = {
    'CPU1': [(40,0), (42,0), (52,0), (50,0), (48,0), (44,0), (46,0)],
    'CPU2': [(52,1), (44,1), (42,1), (46,1), (40,1), (50,1), (48,1)],
    'CPU3': [(42,2), (50,2), (44,2), (52,2), (48,2), (40,2), (46,2)],
    'GPU1': [(50,3), (40,3), (46,3), (48,3), (44,3), (52,3), (42,3)],
    'GPU2': [(44,4), (42,4), (52,4), (48,4), (50,4), (40,4), (46,4)],
    'GPU3': [(48,5), (50,5), (42,5), (44,5), (40,5), (52,5), (46,5)]
}

# Розширений шрифт для 7-сегментника [A, B, C, D, E, F, G]
FONT = {
    '0': [1,1,1,1,1,1,0], '1': [0,1,1,0,0,0,0], '2': [1,1,0,1,1,0,1],
    '3': [1,1,1,1,0,0,1], '4': [0,1,1,0,0,1,1], '5': [1,0,1,1,0,1,1],
    '6': [1,0,1,1,1,1,1], '7': [1,1,1,0,0,0,0], '8': [1,1,1,1,1,1,1],
    '9': [1,1,1,1,0,1,1], ' ': [0,0,0,0,0,0,0], '-': [0,0,0,0,0,0,1],
    '_': [0,0,0,1,0,0,0],

    # Латиниця
    'a': [1,1,1,0,1,1,1], 'b': [0,0,1,1,1,1,1], 'c': [1,0,0,1,1,1,0],
    'd': [0,1,1,1,1,0,1], 'e': [1,0,0,1,1,1,1], 'f': [1,0,0,0,1,1,1],
    'g': [1,0,1,1,1,1,0], 'h': [0,1,1,0,1,1,1], 'i': [0,1,1,0,0,0,0],
    'j': [0,1,1,1,0,0,0], 'l': [0,0,0,1,1,1,0], 'n': [0,0,1,0,1,0,1],
    'o': [1,1,1,1,1,1,0], 'p': [1,1,0,0,1,1,1], 'r': [0,0,0,0,1,0,1],
    's': [1,0,1,1,0,1,1], 't': [0,0,0,1,1,1,1], 'u': [0,1,1,1,1,1,0],
    'y': [0,1,1,1,0,1,1], 'z': [1,1,0,1,1,0,1],

    # Кирилиця (адаптивні символи)
    'а': [1,1,1,0,1,1,1], 'б': [0,0,1,1,1,1,1], 'в': [0,0,1,1,1,1,1],
    'г': [1,0,0,0,1,1,0], 'д': [0,1,1,1,1,0,1], 'е': [1,0,0,1,1,1,1],
    'є': [1,0,0,1,1,1,1], 'з': [1,1,1,1,0,0,1], 'и': [0,1,1,1,1,1,0],
    'і': [0,1,1,0,0,0,0], 'ї': [0,1,1,0,0,0,0], 'к': [0,1,1,0,1,1,1],
    'л': [0,0,0,1,1,1,0], 'м': [1,1,1,0,1,1,0], 'н': [0,1,1,0,1,1,1],
    'о': [1,1,1,1,1,1,0], 'п': [0,0,1,0,1,0,1], 'р': [1,1,0,0,1,1,1],
    'с': [1,0,0,1,1,1,0], 'т': [0,0,0,1,1,1,1], 'у': [0,1,1,1,0,1,1],
    'ч': [0,1,1,0,0,1,1], 'ш': [0,1,1,1,1,1,0], 'ь': [0,0,1,1,1,1,1]
}

class MarqueeLCD:
    def __init__(self, dev_path=DEV_PATH):
        self.dev_path = dev_path
        self.seq_id = 0x61

    def _get_seq(self):
        curr = self.seq_id
        self.seq_id = (self.seq_id + 1) & 0xFF
        return curr

    def _set_bit(self, buf, b_idx, bit_i):
        if b_idx >= 0 and bit_i >= 0:
            buf[b_idx] |= (1 << bit_i)

    def render_window(self, window_6char: str):
        buf = bytearray(64)
        buf[0] = self._get_seq()
        buf[1] = 0x00
        buf[2] = 0x02

        # Написи CPU та GPU підсвічені за замовчуванням
        self._set_bit(buf, 41, 2)
        self._set_bit(buf, 51, 2)

        for i, char in enumerate(window_6char):
            ch_lower = char.lower()
            mask = FONT.get(ch_lower, FONT[' '])
            digit_name = DIGIT_NODES[i]
            
            for seg_i, is_on in enumerate(mask):
                if is_on:
                    b_idx, bit_i = SEGMENT_MAP[digit_name][seg_i]
                    self._set_bit(buf, b_idx, bit_i)

        try:
            with open(self.dev_path, "wb") as dev:
                dev.write(buf)
                dev.flush()
        except Exception as e:
            print(f"[!] Помилка запису у {self.dev_path}: {e}")

    def scroll_text(self, text: str, delay=0.25):
        # Додаємо 6 пробілів на початку та в кінці для плавного входу/виходу
        padded = "      " + text + "      "
        for i in range(len(padded) - 5):
            chunk = padded[i:i+6]
            self.render_window(chunk)
            time.sleep(delay)

def main():
    dev_node = sys.argv[1] if len(sys.argv) > 1 else DEV_PATH
    marquee = MarqueeLCD(dev_node)

    print("=" * 60)
    print(f"[*] БІГУЧИЙ РЯДОК ДЛЯ ДИСПЛЕЯ ({dev_node})")
    print("      Введи текст і тисни ENTER (або 'q' для виходу)")
    print("=" * 60)

    try:
        while True:
            text = input("\nВведи текст: ").strip()
            if text.lower() == 'q':
                break
            if not text:
                continue

            print(f"[>] Прокрутка: \"{text}\"")
            marquee.scroll_text(text, delay=0.25)

    except KeyboardInterrupt:
        print("\n[*] Зупинено.")

if __name__ == "__main__":
    main()
