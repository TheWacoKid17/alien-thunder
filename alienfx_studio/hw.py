"""Transporte hidraw (espaco de usuario, sem sudo).

Teclado 0d62:d2b1: HIDIOCSFEATURE/HIDIOCGFEATURE de 64 bytes (identico ao
alienfx-perfil comprovado).
AW-ELC 187c:0551: write() de output report de 33 bytes no hidraw. O descritor HID
nao tem report id, entao o buffer leva um 0x00 na frente que o kernel remove, e o
usbhid envia os 33 bytes pelo endpoint interrupt OUT 0x01 -- os mesmos bytes que
o alienrgb envia via libusb, sem precisar desanexar o driver do kernel.
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

# ALIENFX_STUDIO_DRYRUN=1: nada e enviado ao hardware (testes / capturas de tela).
DRYRUN = bool(os.environ.get("ALIENFX_STUDIO_DRYRUN"))
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
    """Lock entre processos (daemon, GUI sem daemon, CLI) para nao intercalar pacotes."""
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
                    raise DeviceError("outro processo está usando os LEDs (lock ocupado)")
                time.sleep(0.02)
        yield
    finally:
        os.close(fd)


class _Hidraw:
    finder = staticmethod(lambda: None)
    what = "dispositivo"

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
            raise DeviceError(f"{self.what} não encontrado")
        try:
            self.fd = os.open(path, os.O_RDWR)
        except OSError as e:
            raise DeviceError(f"{self.what}: sem acesso a {path}: {e.strerror}") from None
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
    what = "teclado 0d62:d2b1 (report 0xcc)"

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
            raise DeviceError(f"teclado: falha ao enviar ({e.strerror})") from None

    def _status(self) -> bytes:
        if self.fd == -1:
            return b"\xcc\x93\x17\x01\x16\x00"
        buf = bytearray(protocol.KB_LEN)
        buf[0] = protocol.KB_REPORT_ID
        try:
            n = fcntl.ioctl(self.fd, HIDIOCGFEATURE(protocol.KB_LEN), buf)
        except OSError as e:
            self.close()
            raise DeviceError(f"teclado: falha ao ler status ({e.strerror})") from None
        return bytes(buf[: n if isinstance(n, int) and n > 0 else 6])

    def begin(self, retries: int = 10):
        """reset + status, esperando sair de WAITUPDATE (como o alienfx-perfil)."""
        self.open()
        for _ in range(retries):
            self._send(protocol.KB_RESET)
            time.sleep(0.02)
            self._send(protocol.KB_STATUS)
            st = self._status()
            self.last_status = st
            if st[:2] != b"\xcc\x93":
                raise DeviceError(f"teclado: resposta inesperada {st.hex()}")
            if st[2] != protocol.KB_WAITUPDATE:
                return st
            time.sleep(0.5)
        raise DeviceError("teclado ocupado (WAITUPDATE)")

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
    what = "controlador AW-ELC 187c:0551"

    def _write(self, pkt: bytes):
        protocol.assert_safe_elc(pkt)
        if self.fd == -1:
            DRYRUN_LOG.append(pkt)
            return
        try:
            n = os.write(self.fd, b"\x00" + pkt)
        except OSError as e:
            self.close()
            raise DeviceError(f"chassi: falha ao enviar ({e.strerror})") from None
        if n != protocol.ELC_LEN + 1:
            raise DeviceError(f"chassi: escrita curta ({n})")

    def status(self) -> bytes:
        if self.fd == -1:
            return b"\x83\x21\xff" + bytes(30)
        buf = bytearray(protocol.ELC_LEN + 1)
        try:
            fcntl.ioctl(self.fd, HIDIOCGINPUT(len(buf)), buf)
        except OSError as e:
            raise DeviceError(f"chassi: falha ao ler status ({e.strerror})") from None
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
            raise DeviceError(f"chassi: resposta inesperada {st[:8].hex()}")
        return f"{st[3]}.{st[4]}.{st[5]}"


class AlienrgbChassis:
    """Modo compativel: usa o binario alienrgb (so cores estaticas)."""

    def __init__(self):
        self.exe = None

    def _exe(self):
        for c in (paths.ALIENRGB_BIN, shutil.which("alienrgb")):
            if c and os.access(c, os.X_OK):
                return c
        raise DeviceError("alienrgb não encontrado (~/.local/src/alienrgb/target/release/alienrgb)")

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
