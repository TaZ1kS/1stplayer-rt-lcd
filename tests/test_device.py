#!/usr/bin/env python3
"""Device path safety: a vanished hidraw node must never become a regular file."""
import importlib.util
import pathlib
import tempfile


def load_lcd():
    spec = importlib.util.spec_from_file_location("lcd", "scripts/lcd.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def patch_device(mod, stable, matches):
    old = mod.STABLE_PATH, mod._hidraw_devices
    mod.STABLE_PATH = str(stable)
    mod._hidraw_devices = lambda: list(matches)
    return old


def restore_device(mod, old):
    mod.STABLE_PATH, mod._hidraw_devices = old


def test_stale_stable_path(mod):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        stable = tmp / "stable"
        stable.write_bytes(b"stale telemetry frame")
        hidraw = tmp / "hidraw99"
        hidraw.write_bytes(b"")
        old = patch_device(
            mod, stable, [(str(hidraw), (mod.USB_VID, mod.USB_PID))]
        )
        try:
            # The service passes the stable path explicitly; a regular file
            # there must still fall through to the USB ID scan.
            assert mod.find_lcd_device() == str(hidraw)
            assert mod.find_lcd_device(str(stable)) == str(hidraw)
            assert stable.read_bytes() == b"stale telemetry frame"
        finally:
            restore_device(mod, old)
    print("stale stable path is ignored: OK")


def test_write_does_not_create(mod):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        stable = tmp / "stable"
        missing = tmp / "missing"
        old = patch_device(mod, stable, [])
        try:
            monitor = mod.SystemTelemetryLCD(str(missing), animation="off")
            assert monitor._write_frame(monitor._compose()) is False
            assert not missing.exists(), "write must not create the device node"
            assert not stable.exists(), "write must not create the stable path"
        finally:
            restore_device(mod, old)
    print("missing device is not created: OK")


def test_recovery_after_reenumeration(mod):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        stable = tmp / "stable"
        stable.write_bytes(b"stale")
        hidraw = tmp / "hidraw42"
        hidraw.write_bytes(b"")
        old = patch_device(
            mod, stable, [(str(hidraw), (mod.USB_VID, mod.USB_PID))]
        )
        try:
            monitor = mod.SystemTelemetryLCD(
                str(tmp / "gone"), animation="off"
            )
            assert monitor._write_frame(monitor._compose()) is True
            assert monitor.dev_path == str(hidraw)
            assert hidraw.stat().st_size == 64
            assert stable.read_bytes() == b"stale"
        finally:
            restore_device(mod, old)
    print("device recovery after re-enumeration: OK")


def test_wait_rejects_stale_path(mod):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        stable = tmp / "stable"
        stable.write_bytes(b"stale")
        old = patch_device(mod, stable, [])
        try:
            try:
                mod.wait_for_lcd_device(str(stable), timeout=0)
            except SystemExit:
                pass
            else:
                raise AssertionError("wait must not accept a stale regular file")
            assert stable.is_file()
        finally:
            restore_device(mod, old)
    print("wait ignores stale stable path: OK")


def main():
    mod = load_lcd()
    test_stale_stable_path(mod)
    test_write_does_not_create(mod)
    test_recovery_after_reenumeration(mod)
    test_wait_rejects_stale_path(mod)


if __name__ == "__main__":
    main()
