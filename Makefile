PYTHON ?= python3
DEV ?= /dev/hidraw3

.PHONY: help monitor marquee stress install-udev check

help:
	@printf '%s\n' \
	  '1st Player RT LCD' \
	  '' \
	  '  make monitor        CPU/GPU telemetry' \
	  '  make marquee        scrolling text' \
	  '  make stress         all-segments stress test' \
	  '  make install-udev   install the hidraw udev rule' \
	  '  make check          compile the scripts' \
	  '' \
	  'Override the device with DEV=/dev/hidrawN.'

monitor:
	$(PYTHON) scripts/lcd.py $(DEV)

marquee:
	$(PYTHON) scripts/lcd_sym.py $(DEV)

stress:
	$(PYTHON) scripts/unlock.py $(DEV)

install-udev:
	sudo install -m 644 udev/99-1stplayer-rt-lcd.rules /etc/udev/rules.d/
	sudo udevadm control --reload-rules
	sudo udevadm trigger

check:
	$(PYTHON) -m py_compile scripts/lcd.py scripts/lcd_sym.py scripts/unlock.py
