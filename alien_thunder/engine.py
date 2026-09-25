"""Sends profiles to the hardware; used by the daemon, the CLI, and the GUI when the daemon is off."""
from __future__ import annotations

import json
import os
import time

from . import effects, gmode, hw, paths, profiles, protocol
from .profiles import hex_to_rgb

ZONES = {"touchpad": protocol.ZONE_TOUCHPAD, "logo": protocol.ZONE_LOGO}
ALIENRGB_TARGET = {"touchpad": "touchpad", "logo": "back"}


def _scale(c, f):
    return tuple(max(0, min(255, int(round(x * f)))) for x in c)


def keyboard_colors(profile: dict) -> dict[int, tuple[int, int, int]]:
    f = profile["brightness"] / 100.0
    return {int(k): _scale(hex_to_rgb(v), f) for k, v in profile["keyboard"].items()}


def chassis_zones(profile: dict) -> dict[int, dict]:
    f = profile["brightness"] / 100.0
    out = {}
    for name, zid in ZONES.items():
        z = profile["chassis"][name]
        out[zid] = {"effect": z["effect"], "color": _scale(hex_to_rgb(z["color"]), f),
                    "color2": _scale(hex_to_rgb(z["color2"]), f), "tempo": z["tempo"]}
    return out


def kb_effect_packet(profile: dict) -> bytes:
    e = profile["keyboard_effect"]
    f = profile["brightness"] / 100.0
    return protocol.kb_effect_packet(e["effect"], e["tempo"], e["color_mode"],
                                     _scale(hex_to_rgb(e["color1"]), f), _scale(hex_to_rgb(e["color2"]), f))


def make_sw_effect(profile: dict) -> effects.SoftwareEffect:
    e = profile["keyboard_effect"]
    params = dict(e)
    params["color1_rgb"] = hex_to_rgb(e["color1"])
    return effects.SoftwareEffect(e["effect"], keyboard_colors(profile), params, profile["brightness"] / 100.0)


class State:
    """The little that has to survive a restart (~/.local/state/alien-thunder/state.json)."""

    def __init__(self):
        self.data = {"power_written": None, "keyboard_hw_effect": False}
        try:
            with open(paths.STATE_FILE, encoding="utf-8") as f:
                self.data.update(json.load(f))
        except (OSError, ValueError):
            self._from_v1()

    def _from_v1(self):
        # Carrying the power colors over matters: without them the next start would
        # write the power button again, and that one goes to the controller's flash.
        try:
            with open(paths.OLD_STATE_FILE, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            return
        pw = old.get("energia_gravada")
        self.data["power_written"] = {"ac": pw["ac"], "battery": pw["bateria"]} if pw else None
        self.data["keyboard_hw_effect"] = bool(old.get("teclado_efeito_hw"))
        self.save()
        os.unlink(paths.OLD_STATE_FILE)

    def save(self):
        profiles._atomic_write(paths.STATE_FILE, self.data)


class Engine:
    def __init__(self, log=print):
        self.log = log
        self.kb = hw.KeyboardV5()
        self.ch = hw.ChassisV4()
        self.alienrgb = hw.AlienrgbChassis()
        self.state = State()
        self.last_kb = None
        self.last_ch = None
        self.sw: effects.SoftwareEffect | None = None
        self.sw_t0 = 0.0
        self.gmode = False
        self.f1: tuple[int, int, int] | None = None

    def _overlay(self, colors: dict) -> dict:
        if self.f1 is None:
            return colors
        return {**colors, gmode.F1_LED: self.f1}

    # ------------------------------------------------------------ partes
    def invalidate(self):
        self.last_kb = self.last_ch = None
        self.kb.close()
        self.ch.close()

    def _apply_keyboard(self, profile: dict):
        e = profile["keyboard_effect"]
        mode = e["mode"]
        with hw.hw_lock():
            if mode == "hardware":
                self.sw = None
                self.kb.hw_effect(kb_effect_packet(profile))
                if not self.state.data["keyboard_hw_effect"]:
                    self.state.data["keyboard_hw_effect"] = True
                    self.state.save()
                self.log(f"keyboard: hardware effect '{e['effect']}'")
                return
            if self.state.data["keyboard_hw_effect"]:
                self.kb.effect_off()
                self.state.data["keyboard_hw_effect"] = False
                self.state.save()
                self.log("keyboard: hardware effect off")
            if mode == "software":
                self.sw = make_sw_effect(profile)
                self.sw_t0 = time.monotonic()
                self.kb.static(self._overlay(self.sw.frame(0.0)))
                self.log(f"keyboard: software effect '{e['effect']}'")
            else:
                self.sw = None
                colors = self._overlay(keyboard_colors(profile))
                self.kb.static(colors)
                self.log(f"keyboard: {len(colors)} LEDs set")

    def _apply_chassis(self, profile: dict, backend: str):
        zones = chassis_zones(profile)
        if backend == "alienrgb":
            for name, zid in ZONES.items():
                z = zones[zid]
                if z["effect"] not in ("static", "off"):
                    self.log(f"{name}: alienrgb can't do the '{z['effect']}' effect; using a fixed color")
                color = (0, 0, 0) if z["effect"] == "off" else z["color"]
                self.alienrgb.set_zone(ALIENRGB_TARGET[name], profiles.rgb_to_hex(color))
            self.log("chassis: set through alienrgb")
            return
        with hw.hw_lock():
            self.ch.send(protocol.elc_zone_packets(zones))
            self.ch.wait_ready()
        self.log("chassis: touchpad and logo set")

    def _apply_power(self, profile: dict, backend: str, force: bool):
        pw = profile["chassis"]["power"]
        want = {"ac": pw["ac"], "battery": pw["battery"]}
        if not force and self.state.data.get("power_written") == want:
            return
        if backend == "alienrgb" and pw["ac"] == pw["battery"]:
            self.alienrgb.power(pw["ac"])
        else:
            with hw.hw_lock():
                self.ch.send(protocol.elc_power_packets(hex_to_rgb(pw["ac"]), hex_to_rgb(pw["battery"])))
                self.ch.wait_ready()
        self.state.data["power_written"] = want
        self.state.save()
        self.log(f"power button written: AC {pw['ac']} / battery {pw['battery']}")

    # ------------------------------------------------------------ publico
    def apply(self, profile: dict, *, power: bool = False, force: bool = False,
              backend: str = "hidraw") -> None:
        """Sends keyboard and chassis, skipping parts that match the last send unless force.

        power=True only for the ACTIVE profile: writes the power button when its colors
        changed since the last write. A failure in one part doesn't stop the others; at
        the end a DeviceError sums them up, and the daemon tries again.
        """
        profile = profiles.normalize(profile)
        errors = []
        # G-Mode paints F1 white over the profile; a hardware effect animates the whole keyboard and ignores it.
        self.f1 = _scale(gmode.WHITE, profile["brightness"] / 100.0) if self.gmode else None
        kb_key = json.dumps([profile["keyboard"], profile["keyboard_effect"], profile["brightness"], self.gmode],
                            sort_keys=True)
        if force or kb_key != self.last_kb:
            try:
                self.last_kb = None
                self._apply_keyboard(profile)
                self.last_kb = kb_key
            except hw.DeviceError as e:
                errors.append(str(e))
        ch_key = json.dumps([profile["chassis"]["touchpad"], profile["chassis"]["logo"],
                             profile["brightness"], backend], sort_keys=True)
        if force or ch_key != self.last_ch:
            try:
                self.last_ch = None
                self._apply_chassis(profile, backend)
                self.last_ch = ch_key
            except hw.DeviceError as e:
                errors.append(str(e))
        if power:
            try:
                self._apply_power(profile, backend, force=False)
            except hw.DeviceError as e:
                errors.append(str(e))
        if errors:
            raise hw.DeviceError("; ".join(errors))

    def write_power_now(self, profile: dict, backend: str = "hidraw"):
        self._apply_power(profiles.normalize(profile), backend, force=True)

    def sw_tick(self):
        """Sends one frame of the software effect; the daemon's timer calls this."""
        if self.sw is None:
            return
        frame = self._overlay(self.sw.frame(time.monotonic() - self.sw_t0))
        with hw.hw_lock(timeout=0.5):
            self.kb.static(frame, retries=2)

    def close(self):
        self.kb.close()
        self.ch.close()


def daemon_running() -> bool:
    if hw.DRYRUN:
        return False
    try:
        import dbus
        return dbus.SessionBus().name_has_owner(paths.DBUS_NAME)
    except Exception:
        return False


def daemon_call(method: str, *args, timeout: float = 20.0):
    import dbus
    obj = dbus.SessionBus().get_object(paths.DBUS_NAME, paths.DBUS_PATH)
    return getattr(obj, method)(*args, dbus_interface=paths.DBUS_IFACE, timeout=timeout)


def env_info() -> dict:
    return {"keyboard": hw.find_keyboard(), "chassis": hw.find_chassis(),
            "alienrgb": os.access(paths.ALIENRGB_BIN, os.X_OK)}
