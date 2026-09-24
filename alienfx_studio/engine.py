"""Aplica perfis no hardware (usado pelo daemon, pela CLI e pela GUI sem daemon)."""
from __future__ import annotations

import json
import os
import time

from . import effects, hw, paths, profiles, protocol
from .profiles import hex_to_rgb

ZONES = {"touchpad": protocol.ZONE_TOUCHPAD, "logo": protocol.ZONE_LOGO}
ALIENRGB_TARGET = {"touchpad": "touchpad", "logo": "back"}


def _scale(c, f):
    return tuple(max(0, min(255, int(round(x * f)))) for x in c)


def keyboard_colors(profile: dict) -> dict[int, tuple[int, int, int]]:
    f = profile["brilho"] / 100.0
    return {int(k): _scale(hex_to_rgb(v), f) for k, v in profile["teclado"].items()}


def chassis_zones(profile: dict) -> dict[int, dict]:
    f = profile["brilho"] / 100.0
    out = {}
    for name, zid in ZONES.items():
        z = profile["chassi"][name]
        out[zid] = {"efeito": z["efeito"], "cor": _scale(hex_to_rgb(z["cor"]), f),
                    "cor2": _scale(hex_to_rgb(z["cor2"]), f), "tempo": z["tempo"]}
    return out


def kb_effect_packet(profile: dict) -> bytes:
    e = profile["efeito_teclado"]
    f = profile["brilho"] / 100.0
    return protocol.kb_effect_packet(e["efeito"], e["tempo"], e["modo_cor"],
                                     _scale(hex_to_rgb(e["cor1"]), f), _scale(hex_to_rgb(e["cor2"]), f))


def make_sw_effect(profile: dict) -> effects.SoftwareEffect:
    e = profile["efeito_teclado"]
    params = dict(e)
    params["cor1_rgb"] = hex_to_rgb(e["cor1"])
    return effects.SoftwareEffect(e["efeito"], keyboard_colors(profile), params, profile["brilho"] / 100.0)


class State:
    """Estado persistente minimo (~/.local/state/alienfx-studio/estado.json)."""

    def __init__(self):
        self.data = {"energia_gravada": None, "teclado_efeito_hw": False}
        try:
            with open(paths.STATE_FILE, encoding="utf-8") as f:
                self.data.update(json.load(f))
        except (OSError, ValueError):
            pass

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

    # ------------------------------------------------------------ partes
    def invalidate(self):
        self.last_kb = self.last_ch = None
        self.kb.close()
        self.ch.close()

    def _apply_keyboard(self, profile: dict):
        e = profile["efeito_teclado"]
        mode = e["modo"]
        with hw.hw_lock():
            if mode == "hardware":
                self.sw = None
                self.kb.hw_effect(kb_effect_packet(profile))
                if not self.state.data["teclado_efeito_hw"]:
                    self.state.data["teclado_efeito_hw"] = True
                    self.state.save()
                self.log(f"teclado: efeito de hardware '{e['efeito']}'")
                return
            if self.state.data["teclado_efeito_hw"]:
                self.kb.effect_off()
                self.state.data["teclado_efeito_hw"] = False
                self.state.save()
                self.log("teclado: efeito de hardware desligado")
            if mode == "software":
                self.sw = make_sw_effect(profile)
                self.sw_t0 = time.monotonic()
                self.kb.static(self.sw.frame(0.0))
                self.log(f"teclado: efeito de software '{e['efeito']}'")
            else:
                self.sw = None
                colors = keyboard_colors(profile)
                self.kb.static(colors)
                self.log(f"teclado: {len(colors)} LEDs aplicados")

    def _apply_chassis(self, profile: dict, backend: str):
        zones = chassis_zones(profile)
        if backend == "alienrgb":
            for name, zid in ZONES.items():
                z = zones[zid]
                if z["efeito"] not in ("estatico", "apagado"):
                    self.log(f"{name}: efeito '{z['efeito']}' não suportado pelo modo alienrgb; usando cor fixa")
                color = (0, 0, 0) if z["efeito"] == "apagado" else z["cor"]
                self.alienrgb.set_zone(ALIENRGB_TARGET[name], profiles.rgb_to_hex(color))
            self.log("chassi: aplicado via alienrgb")
            return
        with hw.hw_lock():
            self.ch.send(protocol.elc_zone_packets(zones))
            self.ch.wait_ready()
        self.log("chassi: touchpad/logo aplicados")

    def _apply_power(self, profile: dict, backend: str, force: bool):
        en = profile["chassi"]["energia"]
        want = {"ac": en["ac"], "bateria": en["bateria"]}
        if not force and self.state.data.get("energia_gravada") == want:
            return
        if backend == "alienrgb" and en["ac"] == en["bateria"]:
            self.alienrgb.power(en["ac"])
        else:
            with hw.hw_lock():
                self.ch.send(protocol.elc_power_packets(hex_to_rgb(en["ac"]), hex_to_rgb(en["bateria"])))
                self.ch.wait_ready()
        self.state.data["energia_gravada"] = want
        self.state.save()
        self.log(f"botão de energia gravado: AC {en['ac']} / bateria {en['bateria']}")

    # ------------------------------------------------------------ publico
    def apply(self, profile: dict, *, power: bool = False, force: bool = False,
              backend: str = "hidraw") -> None:
        """Aplica teclado e chassi (pula partes iguais ao ultimo envio, salvo force).

        power=True so para o perfil ATIVO: grava o botao de energia se as cores
        mudaram desde a ultima gravacao. Erros de uma parte nao impedem as outras;
        no fim levanta DeviceError com o resumo (o daemon tenta de novo).
        """
        profile = profiles.normalize(profile)
        errors = []
        kb_key = json.dumps([profile["teclado"], profile["efeito_teclado"], profile["brilho"]], sort_keys=True)
        if force or kb_key != self.last_kb:
            try:
                self.last_kb = None
                self._apply_keyboard(profile)
                self.last_kb = kb_key
            except hw.DeviceError as e:
                errors.append(str(e))
        ch_key = json.dumps([profile["chassi"]["touchpad"], profile["chassi"]["logo"],
                             profile["brilho"], backend], sort_keys=True)
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
        """Envia um quadro do efeito de software (chamado pelo timer do daemon)."""
        if self.sw is None:
            return
        frame = self.sw.frame(time.monotonic() - self.sw_t0)
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
    return {"teclado": hw.find_keyboard(), "chassi": hw.find_chassis(),
            "alienrgb": os.access(paths.ALIENRGB_BIN, os.X_OK)}
