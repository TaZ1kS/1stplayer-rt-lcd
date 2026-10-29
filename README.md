<p align="center">
  <img src="assets/banner.svg" alt="1st Player RT LCD — Linux toolkit" width="100%">
</p>

<h1 align="center">1st Player RT LCD</h1>

<p align="center">
  <b>Керування вбудованим USB LCD-дисплеєм корпусів 1st Player RT5 / RT7 / RT9 на Linux.</b><br>
  Телеметрія CPU та GPU, бігучий рядок і тест панелі — на чистому Python, без вендорського застосунку.
</p>

<p align="center">
  <img alt="Linux" src="https://img.shields.io/badge/Linux-hidraw-0f172a?style=for-the-badge&logo=linux&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="USB HID" src="https://img.shields.io/badge/USB-HID-7c3aed?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge">
  <img alt="Release" src="https://img.shields.io/github/v/release/TaZ1kS/1stplayer-rt-lcd?style=for-the-badge&label=release&color=22c55e">
</p>

<p align="center">
  <a href="#швидкий-старт">Швидкий старт</a> ·
  <a href="#автовизначення-hidraw">Автовизначення</a> ·
  <a href="#systemd-сервіс">systemd</a> ·
  <a href="#скрипти">Скрипти</a> ·
  <a href="#протокол-кадру">Протокол</a> ·
  <a href="#карта-сегментів">Карта сегментів</a> ·
  <a href="README.en.md">English</a>
</p>

---

> [!NOTE]
> Це неофіційний community-проєкт. Він не пов'язаний з 1st Player і не містить вендорського коду чи бінарників. Використовуйте на власний розсуд.

## Коротко

| | |
|---|---|
| **Корпус** | 1st Player RT5 / RT7 / RT9 з вбудованим 6-розрядним 7-сегментним LCD |
| **Інтерфейс** | USB HID, 64-байтні output-репорти, `/dev/hidraw*` |
| **ОС** | Linux: `hidraw`, `sysfs`, `hwmon` |
| **Залежності** | лише стандартна бібліотека Python 3.8+ |
| **Тестовий пристрій** | `5131:2007`, на тестовій машині — `/dev/hidraw3` |
| **Автовизначення** | symlink `/dev/1stplayer-rt-lcd` → пошук за USB ID `5131:2007` |

> [!NOTE]
> На тестовій машині `lsusb` підписує цей пристрій як `MSR MSR-101U Mini HID magnetic card reader` — це лише збіг VID/PID у базі `usb.ids`. Орієнтуйся на `hidraw`-вузол, який з'являється після підключення корпусу, і на 64-байтні HID-репорти.

Дисплей фізично має шість 7-сегментних цифр (три під CPU, три під GPU), дві 10-сегментні смужки та службові підписи `CPU`, `GPU`, `USAGE`, `%`, `°C`. Вендорський софт для Windows вміє циклічно показувати різні метрики; ці скрипти зосереджені на найкориснішому режимі — температура та завантаження CPU/GPU у реальному часі.

## Що вміє

| Скрипт | Що робить | Оновлення |
|---|---|---|
| [`lcd.py`](scripts/lcd.py) | Жива телеметрія: температура CPU/GPU у цифрах, завантаження — у смужках | 1 раз на секунду |
| [`lcd_sym.py`](scripts/lcd_sym.py) | Бігучий рядок на шести цифрах; латиниця, кирилиця, цифри | 0.25 с на крок |
| [`unlock.py`](scripts/unlock.py) | Стрес-тест панелі: усі сегменти блимають із заданою частотою | 1–200 Гц вручну |

## Швидкий старт

```bash
git clone https://github.com/TaZ1kS/1stplayer-rt-lcd.git
cd 1stplayer-rt-lcd

# Встановити udev-правило + systemd-сервіс (рекомендовано)
sudo ./install.sh

# Перевірити, що сервіс живий
systemctl status 1stplayer-rt-lcd.service
journalctl -u 1stplayer-rt-lcd.service -f
```

Скрипт встановлення копіює код у `/opt/1stplayer-rt-lcd`, створює стабільний symlink `/dev/1stplayer-rt-lcd` через udev і запускає телеметрію у фоні. В інтерактивному терміналі він спершу показує меню стилю анімації панелі (паралельний, послідовний або без анімації) і зберігає вибір у `/etc/1stplayer-rt-lcd.conf`. Після першого встановлення перепідключи USB-кабель дисплея, якщо symlink ще не з'явився.

Хочеш запускати вручну, без сервісу:

```bash
sudo ./install.sh --no-service
python3 scripts/lcd.py                 # автовизначення пристрою
python3 scripts/lcd.py /dev/hidraw5    # явний hidraw-вузол
```

Скрипти самі знаходять дисплей: спочатку стабільний `/dev/1stplayer-rt-lcd`, потім `hidraw`-вузол із USB ID `5131:2007`. Явний шлях у аргументі має найвищий пріоритет. Якщо збігу немає або їх кілька, скрипт покаже список доступних `hidraw`-пристроїв і завершиться — випадковий пристрій не використовується.

Якщо у системі кілька `hidraw`-пристроїв, спершу знай потрібний:

```bash
ls -l /dev/hidraw* /dev/1stplayer-rt-lcd
```

Скрипти також можна запускати через `make`:

```bash
make monitor              # python3 scripts/lcd.py /dev/1stplayer-rt-lcd
make marquee              # python3 scripts/lcd_sym.py /dev/1stplayer-rt-lcd
make stress               # python3 scripts/unlock.py /dev/1stplayer-rt-lcd
make monitor DEV=/dev/hidraw5
```

> [!TIP]
> Без udev-правила можна тимчасово запускати з `sudo`, наприклад `sudo python3 scripts/lcd.py /dev/hidraw3`. Але постійне правило з `uaccess` зручніше й безпечніше, а systemd-сервіс автоматично перезапускає телеметрію після збоїв.

## Скрипти

### `lcd.py` — телеметрія CPU/GPU

```bash
python3 scripts/lcd.py
python3 scripts/lcd.py /dev/hidraw5
```

Для systemd є режим очікування: `python3 scripts/lcd.py --wait /dev/1stplayer-rt-lcd`. Він чекає до 120 секунд, поки вузол з'явиться; саме цей режим використовує unit-файл. Стиль анімації можна задати прапорцем `--anim parallel|sequence|off` (див. нижче).

Скрипт сам знаходить сенсори:

| Метрика | Джерело |
|---|---|
| Температура CPU | `hwmon` з іменами `coretemp`, `k10temp`, `zenpower` або `cpu_thermal`, файл `temp1_input` |
| Завантаження CPU | `/proc/stat`, різниця `idle`/`total` між опитуваннями |
| Температура GPU | `hwmon` біля `/sys/class/drm/card*/device/`, файл `temp1_input` |
| Завантаження GPU | `/sys/class/drm/card*/device/gpu_busy_percent` (AMD) |

Температура виводиться трьома цифрами, завантаження — смужкою з 10 поділок (кожна поділка ≈ 10%). Якщо сенсор не знайдено або він віддає помилку, відповідне значення буде `0`.

Сенсори перевіряються повторно під час роботи. Якщо сервіс стартував раніше, ніж `amdgpu` зареєстрував `hwmon` або `gpu_busy_percent`, GPU-значення з'являться самі, без перезапуску сервісу. Так само скрипт відновлюється, якщо шлях до сенсора застарів після скидання GPU.

Приклад виводу:

```text
[*] Телеметрію запущено (/dev/1stplayer-rt-lcd). Натисни Ctrl+C для виходу.
    CPU Temp file: /sys/class/hwmon/hwmon4/temp1_input
    GPU Temp file: /sys/class/drm/card1/device/hwmon/hwmon5/temp1_input
    GPU Busy file: /sys/class/drm/card1/device/gpu_busy_percent
```

> [!NOTE]
> `gpu_busy_percent` — це інтерфейс драйвера `amdgpu`. Для NVIDIA завантаження GPU цим скриптом не зчитується; температура може працювати, якщо драйвер виставляє `temp1_input` у `hwmon`.

#### Анімація старту та зупинки

Під час запуску `lcd.py` показує коротке вітання. Стиль вибирається в меню `install.sh` і зберігається в `/etc/1stplayer-rt-lcd.conf`:

| Режим | Що відбувається |
|---|---|
| `parallel` (типово) | один спільний контур навколо всієї панелі заповнюється за годинниковою стрілкою: ліва верхня грань `CPU1` → верхні грані всіх шести цифр → дві праві грані `GPU3` → нижні грані у зворотному напрямку → ліва нижня грань `CPU1`; обидві смужки ростуть паралельно з контуром, наприкінці спалахують усі підписи й панель блимає один раз |
| `sequence` | цифри заповнюються по черзі зліва направо, після них паралельно ростуть обидві смужки |
| `off` | без анімації; панель очищується під час виходу |

Під час зупинки (`SIGTERM` від systemd або `Ctrl+C`) контур/цифри швидко згортаються у зворотному напрямку. Анімація зупинки має бюджет 0,4 с і ніколи не перевищує 0,5 с, тому `systemctl stop` і `systemctl restart` не гальмують.

Вибір можна змінити без перевстановлення: відредагуй `ANIMATION=` у `/etc/1stplayer-rt-lcd.conf` і перезапусти сервіс. Або передай режим напряму:

```bash
python3 scripts/lcd.py --anim parallel /dev/1stplayer-rt-lcd
python3 scripts/lcd.py --animation sequence
python3 scripts/lcd.py --no-anim
```

`--no-anim` — те саме, що `--anim off`. Якщо прапорець не вказано, скрипт читає `/etc/1stplayer-rt-lcd.conf`; якщо файлу немає — використовується `parallel`.

Меню під час встановлення можна пропустити:

```bash
sudo ./install.sh --animation sequence   # задати режим без TUI
sudo ./install.sh --no-tui               # узяти поточний режим або parallel
```

Анімація чіпає лише біти 40–52, службові байти 24–39 залишаються нулями.

### `lcd_sym.py` — бігучий рядок

```bash
python3 scripts/lcd_sym.py
```

Далі вводь текст і натискай Enter. Порожній рядок ігнорується, `q` — вихід. Вікно показує 6 символів, текст прокручується з кроком 0.25 с; на початку й наприкінці додається по 6 пробілів, щоб рядок плавно в'їжджав і виїжджав.

```text
Введи текст: hello
```

Підтримувані символи (регістр не важливий — скрипт приводить текст до нижнього):

<details>
<summary>Показати алфавіт</summary>

- цифри `0–9`, пробіл, `-`, `_`;
- латиниця: `a b c d e f g h i j l n o p r s t u y z`;
- кирилиця: `а б в г д е є з и і ї к л м н о п р с т у ч ш ь`.

Символи, яких немає у шрифті (`v`, `w`, `x`, `q`, `k` тощо), показуються як пробіл. Шрифт легко розширити у словнику `FONT` усередині `lcd_sym.py`.

</details>

### `unlock.py` — тест усіх сегментів

```bash
python3 scripts/unlock.py
```

Скрипт блимає всіма сегментами: кадр «все увімкнено» / «все вимкнено». Під час роботи можна ввести число — цільову частоту в герцах (наприклад `2`, `10`, `60`, `120`). У рядку стану показується задана частота й фактичний FPS. `q` або `Ctrl+C` — вихід; перед виходом дисплей очищається.

> [!WARNING]
> Режим «все увімкнено» виставляє `0xFF` у байти 24–53, включно зі службовими бітами. Через це екран може блимати, гаснути або поводитися нестандартно — для стрес-тесту це очікувано. Не використовуйте цей режим як постійний.

## Автовизначення hidraw

Порядок вибору пристрою:

1. **Явний аргумент** — `python3 scripts/lcd.py /dev/hidraw5` завжди має найвищий пріоритет.
2. **Стабільний symlink** `/dev/1stplayer-rt-lcd`, який створює udev-правило.
3. **Пошук за USB ID** — скрипт читає `HID_ID` з `/sys/class/hidraw/hidraw*/device/uevent` і шукає `0003:00005131:00002007`.

Якщо знайдено рівно один збіг, використовується він. Якщо збігів немає або їх кілька, скрипт завершується зі списком доступних `hidraw`-пристроїв і підказкою. Це зроблено навмисно: краще не запуститися, ніж надіслати 64-байтні кадри клавіатурі, миші чи іншому HID-пристрою.

Перевірити ID вручну:

```bash
udevadm info -q property -n /dev/hidraw3 | grep -E 'ID_VENDOR_ID|ID_MODEL_ID'
cat /sys/class/hidraw/hidraw3/device/uevent | grep HID_ID
```

Якщо у твоєї ревізії інший VID/PID, зміни `USB_VID`/`USB_PID` у трьох скриптах або просто передавай шлях явно. Для udev-правила — `idVendor`/`idProduct` у `udev/99-1stplayer-rt-lcd.rules`.

## systemd-сервіс

Сервіс тримає `scripts/lcd.py` запущеним у фоні, перезапускає його після збоїв і стартує разом із системою. Замість конкретного `/dev/hidrawN` використовується стабільний symlink `/dev/1stplayer-rt-lcd`, який створює udev-правило.

### Встановлення

```bash
sudo ./install.sh
```

Що робить інсталятор:

1. копіює скрипти й документацію в `/opt/1stplayer-rt-lcd`;
2. встановлює `/etc/udev/rules.d/99-1stplayer-rt-lcd.rules` з symlink і `uaccess`;
3. встановлює unit `1stplayer-rt-lcd.service`;
4. записує вибраний стиль анімації в `/etc/1stplayer-rt-lcd.conf`;
5. вмикає автозапуск і запускає сервіс.

В інтерактивному терміналі інсталятор показує меню анімації (`parallel`, `sequence`, `off`). Для скриптів і автоматизації є `--animation MODE` і `--no-tui`; без вибору використовується поточний режим із конфігурації або `parallel`.

Сервіс стартує разом із `multi-user.target` і не прив'язаний до `.device`-юніта symlink. `lcd.py --wait` сам чекає на появу `/dev/1stplayer-rt-lcd` до 120 секунд, тому пізня ініціалізація USB-дисплея не затримує завантаження на 90 секунд і не залишає панель порожньою. Якщо пристрій не з'явився за цей час, сервіс завершується з помилкою і повторює спробу — `Restart=always` та `StartLimitIntervalSec=0` не дають systemd здатися.

Перевірка:

```bash
systemctl status 1stplayer-rt-lcd.service
journalctl -u 1stplayer-rt-lcd.service -f
ls -l /dev/1stplayer-rt-lcd
```

Керування:

```bash
sudo systemctl restart 1stplayer-rt-lcd.service
sudo systemctl stop 1stplayer-rt-lcd.service
sudo systemctl disable --now 1stplayer-rt-lcd.service
```

Те саме через `make`:

| Команда | Дія |
|---|---|
| `make install` | встановити сервіс і udev-правило |
| `make status` | показати статус сервісу |
| `make logs` | стежити за журналом |
| `make uninstall` | видалити сервіс |

### Без сервісу

```bash
sudo ./install.sh --no-service   # файли + udev, без unit-файлу
python3 /opt/1stplayer-rt-lcd/scripts/lcd.py /dev/1stplayer-rt-lcd
```

### User-сервіс

Якщо системний сервіс не потрібен, телеметрію можна запускати в сесії користувача. Спершу встанови файли без системного unit-файлу, потім увімкни user-сервіс:

```bash
sudo ./install.sh --no-service
make install-user-service
systemctl --user status 1stplayer-rt-lcd.service
journalctl --user -u 1stplayer-rt-lcd.service -f
```

User-сервіс стартує після входу в графічну сесію, а не при завантаженні системи.

### Оновлення

```bash
git pull
sudo ./install.sh          # перевстановить файли й перезапустить сервіс
```

Якщо змінилися тільки скрипти, достатньо:

```bash
sudo systemctl restart 1stplayer-rt-lcd.service
```

### Видалення

```bash
sudo ./uninstall.sh
```

Видаляє `/opt/1stplayer-rt-lcd`, unit-файл, udev-правило і `/etc/1stplayer-rt-lcd.conf`. User-сервіс прибирається окремо:

```bash
systemctl --user disable --now 1stplayer-rt-lcd.service
rm -f ~/.config/systemd/user/1stplayer-rt-lcd.service
systemctl --user daemon-reload
```

> [!NOTE]
> Якщо `/dev/1stplayer-rt-lcd` не з'явився, перевір VID/PID у udev-правилі, виконай `sudo udevadm control --reload-rules && sudo udevadm trigger` і перепідключи кабель дисплея. Скрипти вміють знаходити пристрій за USB ID і без symlink, але сервіс явно використовує `/dev/1stplayer-rt-lcd`, щоб не залежати від порядку `hidrawN`.
>
> Якщо після перезавантаження сервіс довго не запускається, перевір `systemctl cat 1stplayer-rt-lcd.service`: у версіях до v1.1.1 там були `After=`/`Wants=` для `dev-1stplayer\x2drt\x2dlcd.device`. Якщо symlink-юніт не активувався, systemd чекав 90 секунд таймауту. Оновися через `git pull && sudo ./install.sh`.

## Протокол кадру

Один кадр — це 64 байти, які записуються у `hidraw`-вузол одним `write()`. Дисплей не надсилає підтверджень; достатньо надіслати наступний кадр.

| Байт | Значення | Призначення |
|---:|---|---|
| 0 | `seq` | Лічильник: старт `0x61`, далі `+1 & 0xFF` |
| 1 | `0x00` | Фіксований заголовок |
| 2 | `0x02` | Фіксований заголовок |
| 3–23 | `0x00` | Зарезервовано |
| 24–39 | `0x00`* | Службові/статичні іконки |
| 40–52 | бітмапа | Цифри, смужки, підписи |
| 53–63 | `0x00` | Зарезервовано |

\* У вендорських кадрах тут є базовий стан іконок; `lcd.py` і `lcd_sym.py` пишуть нулі, а `unlock.py` — `0xFF`.

Біти нумеруються з нуля: `0x01` — біт 0, `0x80` — біт 7. Наприклад, щоб увімкнути сегмент `A` першої цифри CPU, треба виставити біт 0 у байті 40:

```python
buf = bytearray(64)
buf[0] = 0x61
buf[1] = 0x00
buf[2] = 0x02
buf[40] |= 1 << 0          # CPU1, сегмент A
open("/dev/1stplayer-rt-lcd", "wb").write(buf)
```

Порожній кадр — це `61 00 02` і 61 нуль. Кадр «все увімкнено» — `61 00 02`, 21 нуль, 30 байт `FF` (байти 24–53) і 10 нулів.

Повний розбір байтів, службових бітів і прикладів кадрів — у [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Карта сегментів

<p align="center">
  <img src="assets/panel-map.svg" alt="Panel layout: six 7-segment digits and two 10-segment bars" width="100%">
</p>

Кожна цифра — сім сегментів `A B C D E F G`. Адреса записана як `байт.біт`.

| Цифра | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **CPU1** | 40.0 | 42.0 | 52.0 | 50.0 | 48.0 | 44.0 | 46.0 |
| **CPU2** | 52.1 | 44.1 | 42.1 | 46.1 | 40.1 | 50.1 | 48.1 |
| **CPU3** | 42.2 | 50.2 | 44.2 | 52.2 | 48.2 | 40.2 | 46.2 |
| **GPU1** | 50.3 | 40.3 | 46.3 | 48.3 | 44.3 | 52.3 | 42.3 |
| **GPU2** | 44.4 | 42.4 | 52.4 | 48.4 | 50.4 | 40.4 | 46.4 |
| **GPU3** | 48.5 | 50.5 | 42.5 | 44.5 | 40.5 | 52.5 | 46.5 |

> У `CPU2` сегменти `D` і `G` розділені: `D = 46.1`, `G = 46.2`. Це важливо, якщо збираєте власну карту.

Смужки завантаження (зліва направо, 1 → 10):

| Смужка | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **CPU** | 46.6 | 48.6 | 50.6 | 52.6 | 41.0 | 45.0 | 43.0 | 42.6 | 44.6 | 40.6 |
| **GPU** | 49.0 | 51.0 | 40.7 | 42.7 | 44.7 | 47.0 | 52.7 | 50.7 | 48.7 | 46.7 |

Службові підписи:

| Підпис | Адреса |
|---|---|
| `CPU` | 41.2 |
| `GPU` | 51.2 |
| `CPU %` | 41.1 |
| `GPU %` | 51.1 |
| `CPU °C` | 45.1 |
| `GPU °C` | 47.1 |
| `CPU USAGE` | 43.2 |
| `GPU USAGE` | 47.2 |

Повна таблиця «байт → біт → функція» — у [`docs/SEGMENT_MAP.md`](docs/SEGMENT_MAP.md).

## Як це працює

```text
/proc/stat ─────────────────┐
hwmon/*/temp1_input ────────┼──► lcd.py ─────┐
drm/*/gpu_busy_percent ─────┘                │
                                             ├──► 64-byte HID report ──► /dev/hidrawN ──► LCD
stdin (текст) ──► lcd_sym.py ────────────────┤
stdin (Гц) ─────► unlock.py ─────────────────┘
```

Усередині — звичайний `open(dev_path, "wb")` і `write()` 64-байтного `bytearray`. Ніяких `libusb` і сторонніх Python-пакетів. systemd-сервіс лише тримає процес `lcd.py` живим і перезапускає його після збоїв.

## Сумісність

| Компонент | Статус |
|---|---|
| Linux + `hidraw` | ✅ |
| Windows | ❌ — використовуйте офіційний [1ST PC Monitoring](https://1stplayer.com/download/) |
| Intel CPU (температура) | ✅ `coretemp` |
| AMD CPU (температура) | ✅ `k10temp` / `zenpower` |
| AMD GPU (температура + завантаження) | ✅ `amdgpu` |
| NVIDIA GPU (завантаження) | ❌ `gpu_busy_percent` не використовується |
| NVIDIA GPU (температура) | ⚠️ якщо драйвер виставляє `temp1_input` у `hwmon` |
| Інші корпуси з таким LCD | ⚠️ карта сегментів може відрізнятися |

## Безпека

- Скрипти пишуть у **вибраний** `hidraw`-вузол. Переконайся, що це дисплей, а не клавіатура, миша чи кардридер. Особливо це стосується `unlock.py`, який надсилає `0xFF` у байти 24–53.
- Не запускай `unlock.py` на випадкових `/dev/hidraw*` — спочатку перевір `lsusb`, `udevadm info` і `ls -l /dev/hidraw*`.
- `unlock.py` — це стрес-тест, а не повсякденний режим. Короткочасне блимання та можливі артефакти — нормальна поведінка.
- Проєкт не має офіційної підтримки 1st Player. Якщо щось піде не так — це на твій ризик.

## Roadmap

- [x] Телеметрія CPU/GPU
- [x] Бігучий рядок
- [x] Тест усіх сегментів
- [x] Анімація старту та зупинки панелі
- [x] Єдиний контур навколо всієї панелі + смужки
- [x] Вибір стилю анімації в TUI інсталятора
- [x] Конфігураційний файл і прапорці CLI
- [x] systemd-сервіс (системний і user)
- [x] Автовизначення `hidraw` за VID/PID
- [ ] Пакунок для AUR

## Contributing

Якщо у твоєму RT5/RT7/RT9 інша карта сегментів або інший USB ID — відкрий issue. Додай, будь ласка:

- модель корпусу та фото панелі;
- `lsusb` і `udevadm info -q property -n /dev/hidrawN`;
- `uname -r` та дистрибутив;
- що саме не збігається (який сегмент замість якого світиться).

PR-и з новими картами, шрифтами та режимами вітаються.

## Ліцензія

[MIT](LICENSE) © 2026 TaZ1kS

Історія змін — у [`CHANGELOG.md`](CHANGELOG.md).

<p align="center">
  <sub>Зроблено з ☕ та USB-сниффером. Якщо проєкт допоміг — постав зірку ⭐</sub>
</p>
