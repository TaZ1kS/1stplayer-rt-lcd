PYTHON ?= python3
DEV ?= /dev/1stplayer-rt-lcd

.PHONY: help monitor marquee stress install install-udev install-user-service uninstall status logs check

help:
	@printf '%s\n' \
	  '1st Player RT LCD' \
	  '' \
	  '  make monitor              CPU/GPU telemetry in the foreground' \
	  '  make marquee              scrolling text' \
	  '  make stress               all-segments stress test' \
	  '  make install              install systemd service to /opt (sudo)' \
	  '  make install-udev         install only the udev rule (sudo)' \
	  '  make install-user-service install a user systemd service' \
	  '  make uninstall            remove the systemd service (sudo)' \
	  '  make status               show service status' \
	  '  make logs                 follow service logs' \
	  '  make check                compile the scripts' \
	  '' \
	  'Override the device with DEV=/dev/hidrawN.'

monitor:
	$(PYTHON) scripts/lcd.py $(DEV)

marquee:
	$(PYTHON) scripts/lcd_sym.py $(DEV)

stress:
	$(PYTHON) scripts/unlock.py $(DEV)

install:
	sudo ./install.sh

install-udev:
	sudo install -m 644 udev/99-1stplayer-rt-lcd.rules /etc/udev/rules.d/
	sudo udevadm control --reload-rules
	sudo udevadm trigger

install-user-service:
	install -Dm644 systemd/1stplayer-rt-lcd.user.service $(HOME)/.config/systemd/user/1stplayer-rt-lcd.service
	systemctl --user daemon-reload
	systemctl --user enable --now 1stplayer-rt-lcd.service

uninstall:
	sudo ./uninstall.sh

status:
	systemctl status 1stplayer-rt-lcd.service --no-pager

logs:
	journalctl -u 1stplayer-rt-lcd.service -f

check:
	$(PYTHON) -m py_compile scripts/lcd.py scripts/lcd_sym.py scripts/unlock.py
