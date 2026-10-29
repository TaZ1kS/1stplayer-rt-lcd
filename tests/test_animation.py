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


def lit_segments(frame, mod):
    return {
        (name, seg)
        for name in mod.DIGIT_ORDER
        for seg in range(len(mod.SEGMENT_MAP[name]))
        if has_bit(frame, mod.SEGMENT_MAP[name][seg])
    }


def test_parallel(mod):
    frames, startup_count = run_animation(mod, "parallel")
    startup = frames[:startup_count]
    shutdown = frames[startup_count:]
    path = [tuple(item) for item in mod.PERIMETER_PATH]

    # One shared outline: tops of all digits, two right edges of GPU3,
    # bottoms of all digits, and two left edges of CPU1. No inner G.
    assert len(path) == 16
    assert sum(1 for _, seg in path if seg == 0) == 6
    assert sum(1 for _, seg in path if seg == 3) == 6
    assert {name for name, seg in path if seg in (1, 2)} == {"GPU3"}
    assert {name for name, seg in path if seg in (4, 5)} == {"CPU1"}
    assert all(seg != 6 for _, seg in path)

    # Each fill frame adds exactly one segment of the shared outline; both
    # bars grow in parallel with the outline and never light inner segments.
    fill = startup[: len(path)]
    for step, frame in enumerate(fill, 1):
        assert lit_segments(frame, mod) == set(path[:step]), step
        bars = 10 * step // len(path)
        for bar in (mod.BAR_CPU, mod.BAR_GPU):
            assert all(has_bit(frame, addr) for addr in bar[:bars]), step
            assert not any(has_bit(frame, addr) for addr in bar[bars:]), step

    # The flash after the outline lights every digit, including G.
    assert lit_segments(startup[len(path)], mod) == {
        (name, seg)
        for name in mod.DIGIT_ORDER
        for seg in range(len(mod.SEGMENT_MAP[name]))
    }

    check_frames(frames)
    check_full_frame(startup, "parallel startup")
    check_full_frame(shutdown, "parallel shutdown")
    assert startup[-1][3:] == bytes(61), "startup did not end on a blank frame"
    assert shutdown[-1][3:] == bytes(61), "shutdown did not clear the panel"
    print("parallel outline animation: OK")


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


def test_shutdown_budget(mod):
    real_monotonic = mod.time.monotonic
    real_sleep = mod.time.sleep
    try:
        # Simulate a slow hidraw node: every write blocks for a while.
        for write_time in (0.05, 0.075, 0.10, 0.15, 0.20):
            clock = [0.0]
            mod.time.monotonic = lambda clock=clock: clock[0]
            mod.time.sleep = lambda seconds, clock=clock: clock.__setitem__(
                0, clock[0] + seconds
            )
            with tempfile.TemporaryDirectory() as tmp:
                out = pathlib.Path(tmp) / "lcd.bin"
                out.write_bytes(b"")
                for mode in ("parallel", "sequence"):
                    clock[0] = 0.0
                    monitor = mod.SystemTelemetryLCD(str(out), animation=mode)
                    write_frame = monitor._write_frame
                    writes = [0]

                    def slow_write(
                        frame,
                        write_frame=write_frame,
                        clock=clock,
                        write_time=write_time,
                        writes=writes,
                    ):
                        ok = write_frame(frame)
                        clock[0] += write_time
                        writes[0] += 1
                        return ok

                    monitor._write_frame = slow_write
                    monitor.play_shutdown_animation()
                    assert writes[0] > 1, f"{mode}: no shutdown animation"
                    assert clock[0] <= 0.5, (
                        f"{mode} at {write_time:.3f}s/write: "
                        f"{clock[0]:.3f}s"
                    )
    finally:
        mod.time.monotonic = real_monotonic
        mod.time.sleep = real_sleep
    print("shutdown timing: OK")


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
    test_shutdown_budget(mod)
    mod.time.sleep = lambda _seconds: None
    test_parallel(mod)
    test_sequence(mod)
    test_off(mod)
    test_cli(mod)


if __name__ == "__main__":
    main()
