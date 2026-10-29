#!/usr/bin/env python3
"""Startup/shutdown animation: circular fill, one blink, blank panel."""
import importlib.util
import pathlib
import tempfile


def load_lcd():
    spec = importlib.util.spec_from_file_location("lcd", "scripts/lcd.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load_lcd()

    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "lcd.bin"
        out.write_bytes(b"")
        monitor = mod.SystemTelemetryLCD(str(out))

        frames = []
        write_frame = monitor._write_frame

        def capture(frame):
            ok = write_frame(frame)
            frames.append(bytes(frame))
            return ok

        monitor._write_frame = capture
        mod.time.sleep = lambda _seconds: None

        monitor.play_startup_animation()
        startup_count = len(frames)
        assert startup_count > 0, "startup animation wrote no frames"

        # The first frame lights only segment A of CPU1.
        assert frames[0][40] == 0x01
        assert not any(frames[0][41:53])

        # Only the segment bitmap is touched: no service bits (24-39) or tail.
        assert all(not any(frame[3:40]) and not any(frame[53:]) for frame in frames)

        # A full-panel frame exists: all digits are 8 and both bars are full.
        assert any(
            all(frame[b] == 0xFF for b in (40, 42, 44, 46, 48, 50, 52))
            for frame in frames
        ), "no all-segments frame"

        # Startup ends with a blank panel so telemetry starts from a clean frame.
        assert frames[-1][3:] == bytes(61)

        monitor.play_shutdown_animation()
        shutdown = frames[startup_count:]
        assert shutdown, "shutdown animation wrote no frames"
        assert any(
            all(frame[b] == 0xFF for b in (40, 42, 44, 46, 48, 50, 52))
            for frame in shutdown
        ), "shutdown animation never lights the whole panel"
        assert shutdown[-1][3:] == bytes(61), "shutdown did not clear the panel"

        # The sequence counter advances by one for every frame.
        seq = [frame[0] for frame in frames]
        assert all((b - a) & 0xFF == 1 for a, b in zip(seq, seq[1:]))

        print("startup/shutdown animation: OK")


if __name__ == "__main__":
    main()
