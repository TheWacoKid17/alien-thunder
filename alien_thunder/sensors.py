"""CPU and GPU temperature, fan speed and memory use, for the panel widget and the overlay.

The GPU temperature comes from the Alienware embedded controller (alienware_wmi), not
from nvidia-smi: asking the NVIDIA driver wakes the discrete GPU from runtime suspend,
and polling it every two seconds would keep it awake on battery.
"""
from __future__ import annotations

import glob
import json
import os

from . import paths

SENSORS_FILE = os.path.join(paths.RUNTIME, "alien-thunder", "sensors.json")


def _read(path: str) -> int | None:
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _hwmon(name: str) -> str | None:
    for d in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            with open(os.path.join(d, "name")) as f:
                if f.read().strip() == name:
                    return d
        except OSError:
            pass
    return None


def _labelled(hwmon: str | None, kind: str, label: str) -> str | None:
    if hwmon is None:
        return None
    for lab in glob.glob(os.path.join(hwmon, f"{kind}*_label")):
        try:
            with open(lab) as f:
                if f.read().strip() == label:
                    return lab[: -len("_label")] + "_input"
        except OSError:
            pass
    return None


class Sensors:
    """Finds the sysfs files once; hwmon numbers change between boots, labels don't."""

    def __init__(self):
        self.rescan()

    def rescan(self):
        aw = _hwmon("alienware_wmi")
        core = _hwmon("coretemp")
        self.files = {
            # The package sensor is the one the CPU throttles on; the EC reading lags behind it.
            "cpu_temp": _labelled(core, "temp", "Package id 0") or _labelled(aw, "temp", "CPU"),
            "gpu_temp": _labelled(aw, "temp", "GPU"),
            "cpu_fan": _labelled(aw, "fan", "CPU Fan"),
            "gpu_fan": _labelled(aw, "fan", "GPU Fan"),
        }

    def read(self) -> dict:
        out = {}
        for key, path in self.files.items():
            v = _read(path) if path else None
            out[key] = None if v is None else (round(v / 1000) if key.endswith("_temp") else v)
        out["ram"] = memory_percent()
        return out


def memory_percent() -> int | None:
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                key, value = line.split(":", 1)
                info[key] = int(value.split()[0])
    except (OSError, ValueError):
        return None
    if not info.get("MemTotal") or "MemAvailable" not in info:
        return None
    return round(100 * (1 - info["MemAvailable"] / info["MemTotal"]))


def publish(values: dict) -> None:
    os.makedirs(os.path.dirname(SENSORS_FILE), exist_ok=True)
    tmp = SENSORS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(values, f)
    os.replace(tmp, SENSORS_FILE)
