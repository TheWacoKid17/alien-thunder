"""hidraw transport, in user space, no sudo.

Keyboard 0d62:d2b1: 64-byte HIDIOCSFEATURE/HIDIOCGFEATURE, the same as the proven
alienfx-perfil script.
AW-ELC 187c:0551: a 33-byte output report written to hidraw. The HID descriptor has no
report id, so the buffer starts with a 0x00 the kernel strips, and usbhid sends the 33
bytes over interrupt OUT endpoint 0x01. Those are the same bytes alienrgb sends through
libusb, without detaching the kernel driver.
"""
from __future__ import annotations

import fcntl
import glob
import os
import shutil
import subprocess
import time
from contextlib import contextmanager

from . import paths, protocol
from .i18n import gettext as _

# ALIEN_THUNDER_DRYRUN=1: nothing reaches the hardware (tests, screenshots).
DRYRUN = bool(os.environ.get("ALIEN_THUNDER_DRYRUN"))
DRYRUN_LOG: list[bytes] = []

KB_HID_ID = "00000D62:0000D2B1"
ELC_HID_ID = "0000187C:00000551"


class DeviceError(Exception):
    pass


def _ioc(nr: int, size: int) -> int:
    return (3 << 30) | (size << 16) | (ord("H") << 8) | nr


HIDIOCSFEATURE = lambda n: _ioc(0x06, n)  # noqa: E731
HIDIOCGFEATURE = lambda n: _ioc(0x07, n)  # noqa: E731
HIDIOCGINPUT = lambda n: _ioc(0x0A, n)  # noqa: E731


def find_hidraw(hid_id: str, need_desc: bytes | None = None) -> str | None:
    for h in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(h + "/device/uevent") as f:
                if hid_id not in f.read().upper():
                    continue
            if need_desc is not None:
                with open(h + "/device/report_descriptor", "rb") as f:
                    if need_desc not in f.read():
                        continue
        except OSError:
            continue
        return "/dev/" + os.path.basename(h)
    return None


def find_keyboard() -> str | None:
    return find_hidraw(KB_HID_ID, b"\x85\xcc")


def find_chassis() -> str | None:
    return find_hidraw(ELC_HID_ID)


@contextmanager
def hw_lock(timeout: float = 10.0):
    """A lock across processes (daemon, GUI without daemon, CLI) so packets don't interleave."""
    os.makedirs(os.path.dirname(paths.LOCK_FILE), exist_ok=True)
    fd = os.open(paths.LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        end = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > end:
                    raise DeviceError(_("another process is using the LEDs (lock busy)"))
                time.sleep(0.02)
        yield
    finally:
        os.close(fd)


class _Hidraw:
    finder = staticmethod(lambda: None)
    what = "device"

    def __init__(self):
        self.fd = None
        self.path = None

    def open(self):
        if self.fd is not None:
            return
        if DRYRUN:
            self.fd, self.path = -1, "dryrun"
            return
        path = self.finder()
        if not path:
            raise DeviceError(_("%s not found") % self.what)
        try:
            self.fd = os.open(path, os.O_RDWR)
        except OSError as e:
            raise DeviceError(_("%s: no access to %s: %s") % (self.what, path, e.strerror)) from None
        self.path = path

    def close(self):
        if self.fd is not None and self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd = None

    def present(self) -> bool:
        return self.finder() is not None


class KeyboardV5(_Hidraw):
    finder = staticmethod(find_keyboard)
    what = "keyboard 0d62:d2b1 (report 0xcc)"

    def __init__(self):
        super().__init__()
        self.last_status = b""

    def _send(self, pkt: bytes):
        protocol.assert_safe_kb(pkt)
        if self.fd == -1:
            DRYRUN_LOG.append(pkt)
            return
        buf = bytearray(pkt)
        try:
            fcntl.ioctl(self.fd, HIDIOCSFEATURE(protocol.KB_LEN), buf)
        except OSError as e:
            self.close()
            raise DeviceError(_("keyboard: send failed (%s)") % e.strerror) from None

    def _status(self) -> bytes:
        if self.fd == -1:
            return b"\xcc\x93\x17\x01\x16\x00"
        buf = bytearray(protocol.KB_LEN)
        buf[0] = protocol.KB_REPORT_ID
        try:
            n = fcntl.ioctl(self.fd, HIDIOCGFEATURE(protocol.KB_LEN), buf)
        except OSError as e:
            self.close()
            raise DeviceError(_("keyboard: status read failed (%s)") % e.strerror) from None
        return bytes(buf[: n if isinstance(n, int) and n > 0 else 6])

    def begin(self, retries: int = 10):
        """reset + status, waiting for WAITUPDATE to clear, as alienfx-perfil did."""
        self.open()
        for _attempt in range(retries):
            self._send(protocol.KB_RESET)
            time.sleep(0.02)
            self._send(protocol.KB_STATUS)
            st = self._status()
            self.last_status = st
            if st[:2] != b"\xcc\x93":
                raise DeviceError(_("keyboard: unexpected reply %s") % st.hex())
            if st[2] != protocol.KB_WAITUPDATE:
                return st
            time.sleep(0.5)
        raise DeviceError(_("keyboard busy (WAITUPDATE)"))

    def static(self, colors: dict[int, tuple[int, int, int]], retries: int = 10):
        pkts = protocol.kb_static_packets(colors)
        if not pkts:
            return
        self.begin(retries)
        for p in pkts:
            self._send(p)

    def hw_effect(self, pkt: bytes):
        self.begin()
        self._send(pkt)
        self._send(protocol.KB_UPDATE)

    def effect_off(self):
        self.hw_effect(protocol.KB_EFFECT_OFF)


class ChassisV4(_Hidraw):
    finder = staticmethod(find_chassis)
    what = "AW-ELC controller 187c:0551"

    def _write(self, pkt: bytes):
        protocol.assert_safe_elc(pkt)
        if self.fd == -1:
            DRYRUN_LOG.append(pkt)
            return
        try:
            n = os.write(self.fd, b"\x00" + pkt)
        except OSError as e:
            self.close()
            raise DeviceError(_("chassis: send failed (%s)") % e.strerror) from None
        if n != protocol.ELC_LEN + 1:
            raise DeviceError(_("chassis: short write (%d)") % n)

    def status(self) -> bytes:
        if self.fd == -1:
            return b"\x83\x21\xff" + bytes(30)
        buf = bytearray(protocol.ELC_LEN + 1)
        try:
            fcntl.ioctl(self.fd, HIDIOCGINPUT(len(buf)), buf)
        except OSError as e:
            raise DeviceError(_("chassis: status read failed (%s)") % e.strerror) from None
        return bytes(buf[1:])

    def wait_ready(self, timeout: float = 2.0) -> bytes:
        end = time.monotonic() + timeout
        st = self.status()
        while st[1:2] == bytes([protocol.ELC_BUSY]) and time.monotonic() < end:
            time.sleep(0.02)
            st = self.status()
        return st

    def send(self, packets: list[bytes]):
        if not packets:
            return
        self.open()
        for p in packets:
            self._write(p)

    def firmware(self) -> str:
        self.open()
        self._write(protocol.ELC_QUERY_FIRMWARE)
        time.sleep(0.03)
        st = self.status()
        if st[:2] != b"\x83\x20":
            raise DeviceError(_("chassis: unexpected reply %s") % st[:8].hex())
        return f"{st[3]}.{st[4]}.{st[5]}"


class AlienrgbChassis:
    """Compatibility mode: drives the alienrgb binary (static colors only)."""

    def __init__(self):
        self.exe = None

    def _exe(self):
        for c in (paths.ALIENRGB_BIN, shutil.which("alienrgb")):
            if c and os.access(c, os.X_OK):
                return c
        raise DeviceError(_("alienrgb not found (~/.local/src/alienrgb/target/release/alienrgb)"))

    def set_zone(self, target: str, hexcolor: str):
        if DRYRUN:
            return
        r = subprocess.run([self._exe(), "set", "--device", "chassis", "--target", target,
                            "--color", hexcolor.lstrip("#"), "--apply", "--experimental",
                            "--confirm-live-write"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise DeviceError(f"alienrgb {target}: {r.stderr.strip()[:200]}")

    def power(self, hexcolor: str):
        if DRYRUN:
            return
        r = subprocess.run([self._exe(), "power-profile", "--color", hexcolor.lstrip("#"),
                            "--apply", "--experimental", "--confirm-power-profile-write"],
                           capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            raise DeviceError(f"alienrgb power: {r.stderr.strip()[:200]}")

    def close(self):
        pass
