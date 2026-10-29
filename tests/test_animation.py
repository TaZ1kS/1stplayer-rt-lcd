#!/usr/bin/env python3
"""Animation modes: parallel/sequence fill, blink, shutdown and panel clear."""
import importlib.util
import pathlib
import tempfile


def load_lcd():
    spec = importlib.util.spec_from_file_location("lcd", "scripts/lcd.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def has_bit(frame, address):
    byte, bit = address
    return bool(frame[byte] & (1 << bit))


def capture(monitor):
    frames = []
    write_frame = monitor._write_frame

    def wrapper(frame):
        ok = write_frame(frame)
        frames.append(bytes(frame))
        return ok

    monitor._write_frame = wrapper
    return frames


def run_animation(mod, mode):
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "lcd.bin"
        out.write_bytes(b"")
        monitor = mod.SystemTelemetryLCD(str(out), animation=mode)
        frames = capture(monitor)
        monitor.play_startup_animation()
        startup_count = len(frames)
        monitor.play_shutdown_animation()
        return frames, startup_count


def check_frames(frames):
    assert all(len(frame) == 64 for frame in frames)
    # Only the segment bitmap is touched: no service bits (24-39) or tail.
    assert all(not any(frame[3:40]) and not any(frame[53:]) for frame in frames)
    # The sequence counter advances by one for every frame.
    seq = [frame[0] for frame in frames]
    assert all((b - a) & 0xFF == 1 for a, b in zip(seq, seq[1:]))


def check_full_frame(frames, label):
    assert any(
        all(frame[b] == 0xFF for b in (40, 42, 44, 46, 48, 50, 52))
        for frame in frames
    ), f"{label}: no all-segments frame"


def test_parallel(mod):
    frames, startup_count = run_animation(mod, "parallel")
    startup = frames[:startup_count]
    shutdown = frames[startup_count:]

    # Every digit and both bars start filling on the very first frame.
    for name in mod.DIGIT_ORDER:
        assert has_bit(startup[0], mod.SEGMENT_MAP[name][0]), name
    assert has_bit(startup[0], mod.BAR_CPU[0])
    assert has_bit(startup[0], mod.BAR_GPU[0])

    # Six ring segments are all on together; G is added on the next step.
    for name in mod.DIGIT_ORDER:
        assert has_bit(startup[5], mod.SEGMENT_MAP[name][5])
        assert not has_bit(startup[5], mod.SEGMENT_MAP[name][6])
        assert has_bit(startup[6], mod.SEGMENT_MAP[name][6])

    check_frames(frames)
    check_full_frame(startup, "parallel startup")
    check_full_frame(shutdown, "parallel shutdown")
    assert startup[-1][3:] == bytes(61), "startup did not end on a blank frame"
    assert shutdown[-1][3:] == bytes(61), "shutdown did not clear the panel"
    print("parallel animation: OK")


def test_sequence(mod):
    frames, startup_count = run_animation(mod, "sequence")
    startup = frames[:startup_count]
    shutdown = frames[startup_count:]

    # The old mode fills one digit at a time and starts bars only afterwards.
    assert has_bit(startup[0], mod.SEGMENT_MAP["CPU1"][0])
    assert not any(startup[0][41:53]), "first frame must only light CPU1 A"
    assert has_bit(startup[5], mod.SEGMENT_MAP["CPU1"][5])
    assert has_bit(startup[6], mod.SEGMENT_MAP["CPU1"][6])
    assert has_bit(startup[7], mod.SEGMENT_MAP["CPU2"][0])
    assert not has_bit(startup[7], mod.BAR_CPU[0])

    check_frames(frames)
    check_full_frame(startup, "sequence startup")
    check_full_frame(shutdown, "sequence shutdown")
    assert startup[-1][3:] == bytes(61), "startup did not end on a blank frame"
    assert shutdown[-1][3:] == bytes(61), "shutdown did not clear the panel"
    print("sequence animation: OK")


def test_off(mod):
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "lcd.bin"
        out.write_bytes(b"")
        monitor = mod.SystemTelemetryLCD(str(out), animation="off")
        frames = capture(monitor)
        monitor.play_startup_animation()
        assert frames == [], "off mode must not animate on startup"
        monitor.play_shutdown_animation()
        assert len(frames) == 1, "off mode must clear the panel once on exit"
        assert frames[0][3:] == bytes(61)
        print("off mode: OK")


def test_cli(mod):
    with tempfile.TemporaryDirectory() as tmp:
        config = pathlib.Path(tmp) / "1stplayer-rt-lcd.conf"
        config.write_text("# test\nANIMATION = sequence\n", encoding="utf-8")

        assert mod.parse_args([], str(config)) == (False, "sequence", None)
        assert mod.parse_args(["--wait", "/dev/hidraw9"], str(config)) == (
            True,
            "sequence",
            "/dev/hidraw9",
        )
        assert mod.parse_args(["--anim", "parallel"], str(config))[1] == "parallel"
        assert mod.parse_args(["--animation=off"], str(config))[1] == "off"
        assert mod.parse_args(["--no-anim"], str(config))[1] == "off"

        config.write_text("ANIMATION=broken\n", encoding="utf-8")
        assert mod.parse_args([], str(config))[1] == mod.DEFAULT_ANIMATION

        try:
            mod.parse_args(["--anim", "broken"], str(config))
        except SystemExit:
            pass
        else:
            raise AssertionError("invalid CLI animation must fail")

    print("animation CLI/config: OK")


def main():
    mod = load_lcd()
    mod.time.sleep = lambda _seconds: None
    test_parallel(mod)
    test_sequence(mod)
    test_off(mod)
    test_cli(mod)


if __name__ == "__main__":
    main()
