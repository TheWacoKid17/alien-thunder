"""G-Mode: Fn+F1 turns turbo mode on and off, as AWCC does on Windows.

The kernel's alienware-wmi driver already turns G-Mode on (fans at full speed) when the
power profile goes to "performance"; all that's missing is someone handling the key. It
arrives as KEY_PERFORMANCE on the built-in keyboard, a code above xkb's limit, so no
Plasma shortcut can see it, and it's read straight from /dev/input (the input group).

The state lives in power-profiles-daemon: switching the profile from Plasma's applet
turns G-Mode on too, and F1 follows either way.
"""
from __future__ import annotations

import struct

KEYBOARD = "/dev/input/by-path/platform-i8042-serio-0-event-kbd"
EVENT = struct.Struct("llHHi")  # struct input_event on 64-bit
EV_KEY = 1
KEY_PERFORMANCE = 0x2BD

PERFORMANCE = "performance"
F1_LED = 1
WHITE = (255, 255, 255)

PP_NAME = "org.freedesktop.UPower.PowerProfiles"
PP_PATH = "/org/freedesktop/UPower/PowerProfiles"


def pressed(data: bytes) -> bool:
    """True if the evdev read holds a press of the key (not a release or a repeat)."""
    usable = len(data) - len(data) % EVENT.size
    for _s, _us, typ, code, value in EVENT.iter_unpack(data[:usable]):
        if typ == EV_KEY and code == KEY_PERFORMANCE and value == 1:
            return True
    return False


def _props(bus=None):
    import dbus
    bus = bus or dbus.SystemBus()
    return dbus.Interface(bus.get_object(PP_NAME, PP_PATH), "org.freedesktop.DBus.Properties")


def active_profile(bus=None) -> str | None:
    try:
        return str(_props(bus).Get(PP_NAME, "ActiveProfile"))
    except Exception:  # noqa: BLE001  no power-profiles-daemon
        return None


def set_profile(name: str, bus=None) -> None:
    import dbus
    _props(bus).Set(PP_NAME, "ActiveProfile", dbus.String(name))


def is_on(bus=None) -> bool:
    return active_profile(bus) == PERFORMANCE
