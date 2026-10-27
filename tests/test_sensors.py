#!/usr/bin/env python3
"""Regression test: GPU sensors that appear after the service has started."""
import importlib.util
import pathlib
import tempfile


def load_lcd():
    spec = importlib.util.spec_from_file_location("lcd", "scripts/lcd.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeGlob:
    """Maps the sysfs globs used by lcd.py to a temporary fake sysfs."""

    def __init__(self, root, ready):
        self.root = root
        self.ready = ready
        self.cpu_dir = root / "hwmon3"
        self.cpu = self.cpu_dir / "temp1_input"
        self.gpu_dir = root / "card10" / "device" / "hwmon" / "hwmon4"
        self.gpu_temp = self.gpu_dir / "temp1_input"
        self.gpu_busy = root / "card10" / "device" / "gpu_busy_percent"

    def glob(self, pattern):
        if pattern == "/sys/class/hwmon/hwmon*":
            paths = [str(self.cpu_dir)]
            if self.ready:
                paths.append(str(self.gpu_dir))
            return paths
        if pattern == "/sys/class/hwmon/hwmon*/temp1_input":
            paths = [str(self.cpu)]
            if self.ready:
                paths.append(str(self.gpu_temp))
            return paths
        if pattern == "/sys/class/drm/card*/device/hwmon/hwmon*/temp1_input":
            return [str(self.gpu_temp)] if self.ready else []
        if pattern == "/sys/class/drm/card*/device/gpu_busy_percent":
            return [str(self.gpu_busy)] if self.ready else []
        return []


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        cpu_dir = root / "hwmon3"
        cpu_dir.mkdir()
        (cpu_dir / "name").write_text("coretemp\n")
        (cpu_dir / "temp1_input").write_text("33000\n")

        gpu_dir = root / "card10" / "device" / "hwmon" / "hwmon4"
        gpu_dir.mkdir(parents=True)
        (gpu_dir / "name").write_text("amdgpu\n")
        (gpu_dir / "temp1_input").write_text("47000\n")

        gpu_busy = root / "card10" / "device" / "gpu_busy_percent"
        gpu_busy.write_text("17\n")

        mod = load_lcd()
        fake = FakeGlob(root, ready=False)
        mod.glob = fake

        out = root / "lcd.bin"
        out.write_bytes(b"")
        monitor = mod.SystemTelemetryLCD(str(out))
        assert monitor.cpu_temp_file == str(cpu_dir / "temp1_input")
        assert monitor.gpu_temp_file is None
        assert monitor.gpu_busy_file is None

        # amdgpu finishes probing after the service has already started
        fake.ready = True
        monitor.refresh_sensors()
        assert monitor.gpu_temp_file == str(gpu_dir / "temp1_input")
        assert monitor.gpu_busy_file == str(gpu_busy)
        assert monitor.get_gpu_temp() == 47
        assert monitor.get_gpu_usage() == 17

        # a stale path from a GPU reset is dropped and found again
        monitor.gpu_temp_file = "/sys/class/drm/card99/device/hwmon/hwmon99/temp1_input"
        monitor.gpu_busy_file = "/sys/class/drm/card99/device/gpu_busy_percent"
        assert monitor.get_gpu_temp() == 0 and monitor.gpu_temp_file is None
        assert monitor.get_gpu_usage() == 0 and monitor.gpu_busy_file is None
        monitor.refresh_sensors()
        assert monitor.gpu_temp_file and monitor.gpu_busy_file

        monitor.update_display(cpu_temp=33, cpu_usage=10, gpu_temp=47, gpu_usage=17)
        assert out.stat().st_size == 64
        print("late GPU sensors: OK")


if __name__ == "__main__":
    main()
