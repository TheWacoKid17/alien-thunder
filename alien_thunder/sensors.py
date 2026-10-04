"""CPU and GPU temperature, fan speed and memory use, for the panel widget and the overlay.

The GPU temperature comes from the Alienware embedded controller (alienware_wmi), not
from nvidia-smi: asking the NVIDIA driver wakes the discrete GPU from runtime suspend,
and polling it every two seconds would keep it awake on battery.
"""
from __future__ import annotations

import ctypes
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


def _nvidia_gpu() -> str | None:
    """The discrete NVIDIA GPU's sysfs directory, if there is one."""
    for d in sorted(glob.glob("/sys/bus/pci/devices/*")):
        try:
            with open(os.path.join(d, "vendor")) as f:
                vendor = f.read().strip()
            with open(os.path.join(d, "class")) as f:
                cls = f.read().strip()
        except OSError:
            continue
        if vendor == "0x10de" and cls[:6] in ("0x0300", "0x0302"):
            return d
    return None


class _NvmlMemory(ctypes.Structure):
    _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong), ("used", ctypes.c_ulonglong)]


def gpu_memory_percent(gpu: str | None) -> int | None:
    """VRAM in use, only while the GPU is already awake.

    Asking the NVIDIA driver resumes a GPU in runtime suspend, so a sleeping GPU is
    left alone and reads as unknown. NVML is shut down again right after each read,
    because an open handle would keep the GPU from going back to sleep.
    """
    if gpu is None:
        return None
    # LOCAL PATCH: querying NVML every 2 s keeps an awake GPU from ever going back to
    # sleep (each call resets its idle timer), which costs battery. Off unless opted in
    # with ALIEN_THUNDER_VRAM=1 in the service environment.
    if os.environ.get("ALIEN_THUNDER_VRAM") != "1":
        return None
    try:
        with open(os.path.join(gpu, "power", "runtime_status")) as f:
            if f.read().strip() != "active":
                return None
        nv = ctypes.CDLL("libnvidia-ml.so.1")
    except OSError:
        return None
    if nv.nvmlInit_v2() != 0:
        return None
    try:
        handle = ctypes.c_void_p()
        mem = _NvmlMemory()
        if nv.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) != 0:
            return None
        if nv.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(mem)) != 0 or not mem.total:
            return None
        return round(100 * mem.used / mem.total)
    finally:
        nv.nvmlShutdown()


class Sensors:
    """Finds the sysfs files once; hwmon numbers change between boots, labels don't."""

    def __init__(self):
        self._cpu_prev: tuple[int, int] | None = None
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
        self.gpu = _nvidia_gpu()

    def read(self) -> dict:
        out = {}
        for key, path in self.files.items():
            v = _read(path) if path else None
            out[key] = None if v is None else (round(v / 1000) if key.endswith("_temp") else v)
        out["cpu_load"] = self._cpu_load()
        mem = _meminfo()
        if mem:
            total, available = mem
            out["ram"] = round(100 * (1 - available / total))
            out["ram_gb"] = round((total - available) / 2**20, 1)
            out["ram_total_gb"] = round(total / 2**20)
        else:
            out["ram"] = out["ram_gb"] = out["ram_total_gb"] = None
        out["gpu_mem"] = gpu_memory_percent(self.gpu)
        return out

    def _cpu_load(self) -> int | None:
        """Share of the time since the last read that the CPUs weren't idle."""
        try:
            with open("/proc/stat") as f:
                fields = [int(x) for x in f.readline().split()[1:]]
        except (OSError, ValueError):
            return None
        idle = fields[3] + fields[4]  # idle + iowait
        total = sum(fields[:8])  # guest time is already counted in user
        prev, self._cpu_prev = self._cpu_prev, (idle, total)
        if prev is None or total <= prev[1]:
            return None
        return round(100 * (1 - (idle - prev[0]) / (total - prev[1])))


def _meminfo() -> tuple[int, int] | None:
    """(MemTotal, MemAvailable) in KiB."""
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
    return info["MemTotal"], info["MemAvailable"]



def publish(values: dict) -> None:
    os.makedirs(os.path.dirname(SENSORS_FILE), exist_ok=True)
    tmp = SENSORS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(values, f)
    os.replace(tmp, SENSORS_FILE)
