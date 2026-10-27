# Changelog

## v1.0.0 — 2026-10-27

Перший публічний реліз.

### Додано

- `scripts/lcd.py` — телеметрія CPU/GPU: температури на трьох цифрах, завантаження на 10-сегментних смужках.
- `scripts/lcd_sym.py` — бігучий рядок на шести 7-сегментних цифрах (латиниця, кирилиця, цифри).
- `scripts/unlock.py` — стрес-тест усіх сегментів із регульованою частотою та лічильником FPS.
- systemd-сервіс `1stplayer-rt-lcd.service` для автозапуску телеметрії.
- Опційний user-сервіс `1stplayer-rt-lcd.user.service`.
- udev-правило зі стабільним symlink `/dev/1stplayer-rt-lcd` і `TAG+="uaccess"`.
- `install.sh` та `uninstall.sh`, цілі `make install/status/logs/uninstall`.
- Документація: `README.md`, `README.en.md`, `docs/PROTOCOL.md`, `docs/SEGMENT_MAP.md`.
- Схема панелі та банер репозиторію.

### Відомі обмеження

- Завантаження GPU читається лише з `gpu_busy_percent` драйвера `amdgpu`.
- Карта сегментів перевірена на пристрої `5131:2007`; інші ревізії можуть відрізнятися.
- Автовизначення пристрою за VID/PID не реалізовано — використовується udev symlink.
