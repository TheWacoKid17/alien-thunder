"""Packet encoders (no I/O) for the Alienware m16 R2 lighting controllers.

Keyboard 0d62:d2b1 -> AlienFX "API v5": 64-byte feature reports, report id 0xcc.
Chassis AW-ELC 187c:0551 -> AlienFX "API v4": 33-byte output reports, no report id.

The constants come from the MIT-licensed T-Troll/alienfx-tools SDK
(AlienFX-SDK/AlienFX_SDK/alienfx-controls.h and AlienFX_SDK.cpp, commit 52713b2) and
were checked byte for byte against alienrgb (see tests/test_protocol.py).

Only volatile lighting commands live here. These are left out on purpose:
  - v4 control 2 with id 0xffff/0x61 (finish-and-save), 6 (set default), 7 (set startup)
  - any 0xff command (flash erase), firmware, EC, fans.
The one exception is the power button profile (control 0x22), the same packet alienrgb
sends and AWCC uses; see elc_power_packets().
"""
from __future__ import annotations

from .i18n import N_

Rgb = tuple[int, int, int]

# --------------------------------------------------------------------------- v5
KB_LEN = 64
KB_REPORT_ID = 0xCC
KB_RECORDS_PER_FRAME = 15
KB_WAITUPDATE = 0x80


def _kb(prefix) -> bytes:
    buf = bytearray(KB_LEN)
    buf[: len(prefix)] = bytes(prefix)
    return bytes(buf)


KB_RESET = _kb([0xCC, 0x94])
KB_STATUS = _kb([0xCC, 0x93])
KB_LOOP = _kb([0xCC, 0x8C, 0x13])
KB_UPDATE = _kb([0xCC, 0x8B, 0x01, 0xFF])


def clamp8(v) -> int:
    return max(0, min(255, int(round(v))))


def kb_color_frames(colors: dict[int, Rgb]) -> list[bytes]:
    """Frames `cc 8c 02 00 [id+1 r g b]*15`, ids in ascending order."""
    recs = sorted((int(i), c) for i, c in colors.items())
    frames = []
    for i in range(0, len(recs), KB_RECORDS_PER_FRAME):
        payload = [0xCC, 0x8C, 0x02, 0x00]
        for led, (r, g, b) in recs[i : i + KB_RECORDS_PER_FRAME]:
            if not 0 <= led < 255:
                raise ValueError(f"invalid LED id: {led}")
            payload += [led + 1, clamp8(r), clamp8(g), clamp8(b)]
        frames.append(_kb(payload))
    return frames


def kb_static_packets(colors: dict[int, Rgb]) -> list[bytes]:
    """Packets sent AFTER reset+status: color frames, loop, update."""
    if not colors:
        return []
    return kb_color_frames(colors) + [KB_LOOP, KB_UPDATE]


# Global hardware effects (COMMV5_setEffect = cc 80 02 07 00 00 01 01 01)
#   [2]=type [3]=tempo [9]=color mode - 1 [10..12]=RGB1 [13..15]=RGB2
# Types as in alienfx-tools (ProfilesDialog.cpp ge_types5/ge_names5).
KB_HW_EFFECTS = {
    "breathing": (2, N_("Breathing")),
    "side_wave": (3, N_("Side wave")),
    "double_wave": (4, N_("Double wave")),
    "pulse": (8, N_("Pulse")),
    "morph": (9, N_("Morph (mixed pulse)")),
    "bounce": (10, N_("Bounce (scanner)")),
    "laser": (11, N_("Laser")),
    "rainbow": (14, N_("Rainbow")),
}
KB_COLOR_MODES = {1: N_("One color"), 2: N_("Two colors"), 3: N_("Rainbow")}


def kb_effect_packet(effect: str, tempo: int, color_mode: int, c1: Rgb, c2: Rgb) -> bytes:
    etype = KB_HW_EFFECTS[effect][0]
    if color_mode not in KB_COLOR_MODES:
        raise ValueError("color mode must be 1, 2 or 3")
    buf = bytearray(_kb([0xCC, 0x80, 0x02, 0x07, 0x00, 0x00, 0x01, 0x01, 0x01]))
    buf[2] = etype
    buf[3] = clamp8(tempo)
    buf[9] = color_mode - 1
    buf[10:13] = bytes(clamp8(x) for x in c1)
    buf[13:16] = bytes(clamp8(x) for x in c2)
    return bytes(buf)


# SetGlobalEffects(0, ...) in the SDK: back to per-key colors.
KB_EFFECT_OFF = _kb([0xCC, 0x80, 0x01, 0xFE, 0x00, 0x00, 0x01, 0x01, 0x01])

# --------------------------------------------------------------------------- v4
ELC_LEN = 33
ZONE_TOUCHPAD = 0
ZONE_LOGO = 2
ZONE_POWER = 4
CHASSIS_ZONES = (ZONE_TOUCHPAD, ZONE_LOGO)


def _elc(prefix) -> bytes:
    buf = bytearray(ELC_LEN)
    if len(prefix) > ELC_LEN:
        raise ValueError("v4 packet longer than 33 bytes")
    buf[: len(prefix)] = bytes(prefix)
    return bytes(buf)


# COMMV4_control: [3] 1=start 3=finish-and-play 4=remove 5=play ; [4..5] id
ELC_REMOVE = _elc([0x03, 0x21, 0x00, 0x04, 0xFF, 0xFF])
ELC_START = _elc([0x03, 0x21, 0x00, 0x01, 0xFF, 0xFF])
ELC_FINISH_PLAY = _elc([0x03, 0x21, 0x00, 0x03, 0xFF, 0xFF])
ELC_PLAY = _elc([0x03, 0x21, 0x00, 0x05, 0xFF, 0xFF])
ELC_QUERY_FIRMWARE = _elc([0x03, 0x20, 0x00])
ELC_READY = 0x21
ELC_BUSY = 0x22

# action types (Afx_action.type) and opcodes (v4OpCodes)
A_COLOR, A_PULSE, A_MORPH, A_BREATH, A_SPECTRUM, A_RAINBOW, A_POWER = range(7)
V4_OPCODES = (0xD0, 0xDC, 0xCF, 0xDC, 0x82, 0xAC, 0xE8)


def v4_action_record(atype: int, time: int, tempo: int, color: Rgb) -> bytes:
    """The 8-byte record from SetV4Action()."""
    code = atype if atype < A_BREATH else A_MORPH
    r, g, b = (clamp8(x) for x in color)
    return bytes([code, clamp8(time), V4_OPCODES[atype], 0x00,
                  0xFA if atype == A_COLOR else clamp8(tempo), r, g, b])


def v4_action_packets(zone: int, actions: list[tuple[int, int, int, Rgb]]) -> list[bytes]:
    """COMMV4_colorSel (loop) + COMMV4_colorSet with up to 3 records per packet."""
    out = [_elc([0x03, 0x23, 0x01, 0x00, 0x01, zone])]
    for i in range(0, len(actions), 3):
        payload = [0x03, 0x24]
        for a in actions[i : i + 3]:
            payload += list(v4_action_record(*a))
        out.append(_elc(payload))
    return out


def v4_set_one_color(color: Rgb, zones: list[int]) -> bytes:
    """COMMV4_setOneColor: 03 27 r g b 00 n ids..."""
    r, g, b = (clamp8(x) for x in color)
    return _elc([0x03, 0x27, r, g, b, 0x00, len(zones), *zones])


# Chassis effects (per zone). tempo: 0..255, the transition "speed".
CHASSIS_EFFECTS = {
    "static": N_("Static"),
    "pulse": N_("Pulse"),
    "breathing": N_("Breathing"),
    "morph": N_("Morph (2 colors)"),
    "spectrum": N_("Spectrum (color cycle)"),
    "off": N_("Off"),
}
SPECTRUM = [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)]
PHASE_TIME = 0x07  # default COMMV4_colorSet[4]


def chassis_actions(effect: str, c1: Rgb, c2: Rgb, tempo: int) -> list[tuple[int, int, int, Rgb]]:
    if effect == "pulse":
        return [(A_PULSE, PHASE_TIME, tempo, c1)]
    if effect == "breathing":
        return [(A_MORPH, PHASE_TIME, tempo, c1), (A_MORPH, PHASE_TIME, tempo, (0, 0, 0))]
    if effect == "morph":
        return [(A_MORPH, PHASE_TIME, tempo, c1), (A_MORPH, PHASE_TIME, tempo, c2)]
    if effect == "spectrum":
        return [(A_MORPH, PHASE_TIME, tempo, c) for c in SPECTRUM]
    raise ValueError(effect)


def elc_zone_packets(zones: dict[int, dict]) -> list[bytes]:
    """The whole volatile sequence: remove, start, colors/effects, finish-and-play.

    zones: {zone: {"effect": str, "color": Rgb, "color2": Rgb, "tempo": int}}
    Static zones sharing a color go out in a single setOneColor, as alienrgb does
    (ordered by color, then ascending ids).
    """
    if not zones:
        return []
    steps = [ELC_REMOVE, ELC_START]
    static: dict[Rgb, list[int]] = {}
    effects = []
    for z in sorted(zones):
        spec = zones[z]
        eff = spec.get("effect", "static")
        if eff == "off":
            static.setdefault((0, 0, 0), []).append(z)
        elif eff == "static":
            static.setdefault(tuple(spec["color"]), []).append(z)
        else:
            effects.append((z, spec))
    for color in sorted(static):
        steps.append(v4_set_one_color(color, static[color]))
    for z, spec in effects:
        steps += v4_action_packets(z, chassis_actions(spec["effect"], spec["color"],
                                                      spec.get("color2", (0, 0, 0)),
                                                      spec.get("tempo", 0x64)))
    steps.append(ELC_FINISH_PLAY)
    return steps


# Power button profile: 6 states (SetPowerAction in the SDK).
POWER_STATES = (0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60)  # ac_sleep ac_on charging bat_sleep bat_on bat_critical


def power_state_actions(state: int, ac: Rgb, bat: Rgb) -> list[tuple[int, int, int, Rgb]]:
    """SetPowerAction() ported: the original action is [AC(power), BAT(power)] plus extras."""
    P = lambda c: (A_POWER, 0x03, 0x64, c)  # noqa: E731
    base = [P(ac), P(bat)]
    zero = P((0, 0, 0))
    if state == 0x5B:  # AC, asleep
        return base + [P(ac), zero]
    if state == 0x5C:  # AC, on
        return [(A_COLOR, 0x03, 0x64, ac), P(bat), P(ac)]
    if state == 0x5D:  # charging
        return base + [P(ac), P(bat)]
    if state == 0x5E:  # battery, asleep
        return base + [P(bat), zero]
    if state == 0x5F:  # battery, on
        return [(A_COLOR, 0x03, 0x64, ac), P(bat), P(bat)]
    if state == 0x60:  # battery critical
        return [(A_PULSE, 0x03, 0x64, ac), P(bat), P(bat)]
    raise ValueError(state)


def elc_power_packets(ac: Rgb, bat: Rgb) -> list[bytes]:
    """34 packets, identical to `alienrgb power-profile` when ac == bat.

    Uses control 0x22 (power state animations) with op 2, which the SDK calls
    "finish and save": the controller itself stores how the button behaves while the
    system sleeps or is off. That's why the daemon only sends this when the colors
    CHANGE, never in a loop, on resume or for a preview.
    """
    steps = []
    for st in POWER_STATES:
        steps.append(_elc([0x03, 0x22, 0x00, 0x04, 0x00, st]))
        steps.append(_elc([0x03, 0x22, 0x00, 0x01, 0x00, st]))
        steps += v4_action_packets(ZONE_POWER, power_state_actions(st, ac, bat))
        steps.append(_elc([0x03, 0x22, 0x00, 0x02, 0x00, st]))
    steps.append(ELC_PLAY)
    return steps


FORBIDDEN_V4 = {
    # (byte1, byte3) pairs that must never leave this module
    (0x21, 0x02), (0x21, 0x06), (0x21, 0x07),
}


def assert_safe_elc(pkt: bytes) -> None:
    if len(pkt) != ELC_LEN or pkt[0] != 0x03:
        raise ValueError("malformed v4 packet")
    if pkt[1] == 0xFF or (pkt[1], pkt[3]) in FORBIDDEN_V4:
        raise ValueError(f"forbidden v4 packet: {pkt[:6].hex()}")
    if pkt[1] not in (0x20, 0x21, 0x22, 0x23, 0x24, 0x27):
        raise ValueError(f"v4 command not on the allow list: {pkt[1]:#x}")


def assert_safe_kb(pkt: bytes) -> None:
    if len(pkt) != KB_LEN or pkt[0] != KB_REPORT_ID:
        raise ValueError("malformed v5 packet")
    if pkt[1] not in (0x80, 0x8B, 0x8C, 0x93, 0x94):
        raise ValueError(f"v5 command not on the allow list: {pkt[1]:#x}")
