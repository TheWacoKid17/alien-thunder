"""Codificadores puros (sem E/S) dos protocolos de iluminacao do Alienware m16 R2.

Teclado 0d62:d2b1 -> AlienFX "API v5": feature reports de 64 bytes com report id 0xcc.
Chassi AW-ELC 187c:0551 -> AlienFX "API v4": output reports de 33 bytes (sem report id).

As constantes foram traduzidas do SDK MIT T-Troll/alienfx-tools
(AlienFX-SDK/AlienFX_SDK/alienfx-controls.h e AlienFX_SDK.cpp, commit 52713b2) e
conferidas byte a byte com o alienrgb (testes em tests/test_protocol.py).

Somente comandos volateis de iluminacao estao aqui. Propositalmente NAO existem:
  - v4 control 2 com id 0xffff/0x61 (finish-and-save), 6 (set default), 7 (set startup)
  - qualquer comando 0xff (apagar flash), firmware, EC, ventoinhas.
A unica excecao e o perfil do botao de energia (control 0x22), que e o mesmo pacote
que o alienrgb envia e que o AWCC usa; ver elc_power_packets().
"""
from __future__ import annotations

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
    """Quadros `cc 8c 02 00 [id+1 r g b]*15`, ids em ordem crescente."""
    recs = sorted((int(i), c) for i, c in colors.items())
    frames = []
    for i in range(0, len(recs), KB_RECORDS_PER_FRAME):
        payload = [0xCC, 0x8C, 0x02, 0x00]
        for led, (r, g, b) in recs[i : i + KB_RECORDS_PER_FRAME]:
            if not 0 <= led < 255:
                raise ValueError(f"id de LED invalido: {led}")
            payload += [led + 1, clamp8(r), clamp8(g), clamp8(b)]
        frames.append(_kb(payload))
    return frames


def kb_static_packets(colors: dict[int, Rgb]) -> list[bytes]:
    """Pacotes enviados APOS reset+status: quadros de cor, loop, update."""
    if not colors:
        return []
    return kb_color_frames(colors) + [KB_LOOP, KB_UPDATE]


# Efeitos globais de hardware (COMMV5_setEffect = cc 80 02 07 00 00 01 01 01)
#   [2]=tipo [3]=tempo [9]=modo de cor-1 [10..12]=RGB1 [13..15]=RGB2
# Tipos segundo alienfx-tools (ProfilesDialog.cpp ge_types5/ge_names5).
KB_HW_EFFECTS = {
    "respiracao": (2, "Respiração"),
    "onda_lateral": (3, "Onda lateral"),
    "onda_dupla": (4, "Onda dupla"),
    "pulso": (8, "Pulso"),
    "morph": (9, "Morph (pulso misto)"),
    "ricochete": (10, "Ricochete (scanner)"),
    "laser": (11, "Laser"),
    "arco_iris": (14, "Arco-íris"),
}
KB_COLOR_MODES = {1: "Uma cor", 2: "Duas cores", 3: "Arco-íris"}


def kb_effect_packet(effect: str, tempo: int, color_mode: int, c1: Rgb, c2: Rgb) -> bytes:
    etype = KB_HW_EFFECTS[effect][0]
    if color_mode not in KB_COLOR_MODES:
        raise ValueError("modo de cor deve ser 1, 2 ou 3")
    buf = bytearray(_kb([0xCC, 0x80, 0x02, 0x07, 0x00, 0x00, 0x01, 0x01, 0x01]))
    buf[2] = etype
    buf[3] = clamp8(tempo)
    buf[9] = color_mode - 1
    buf[10:13] = bytes(clamp8(x) for x in c1)
    buf[13:16] = bytes(clamp8(x) for x in c2)
    return bytes(buf)


# SetGlobalEffects(0, ...) no SDK: volta ao modo por tecla.
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
        raise ValueError("pacote v4 maior que 33 bytes")
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

# tipos de acao (Afx_action.type) e opcodes (v4OpCodes)
A_COLOR, A_PULSE, A_MORPH, A_BREATH, A_SPECTRUM, A_RAINBOW, A_POWER = range(7)
V4_OPCODES = (0xD0, 0xDC, 0xCF, 0xDC, 0x82, 0xAC, 0xE8)


def v4_action_record(atype: int, time: int, tempo: int, color: Rgb) -> bytes:
    """Registro de 8 bytes de SetV4Action()."""
    code = atype if atype < A_BREATH else A_MORPH
    r, g, b = (clamp8(x) for x in color)
    return bytes([code, clamp8(time), V4_OPCODES[atype], 0x00,
                  0xFA if atype == A_COLOR else clamp8(tempo), r, g, b])


def v4_action_packets(zone: int, actions: list[tuple[int, int, int, Rgb]]) -> list[bytes]:
    """COMMV4_colorSel (loop) + COMMV4_colorSet com ate 3 registros por pacote."""
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


# Efeitos de chassi (por zona). tempo: 0..255 ("velocidade" da transicao).
CHASSIS_EFFECTS = {
    "estatico": "Estático",
    "pulso": "Pulso",
    "respiracao": "Respiração",
    "morph": "Morph (2 cores)",
    "espectro": "Espectro (ciclo de cores)",
    "apagado": "Apagado",
}
SPECTRUM = [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)]
PHASE_TIME = 0x07  # valor padrao de COMMV4_colorSet[4]


def chassis_actions(effect: str, c1: Rgb, c2: Rgb, tempo: int) -> list[tuple[int, int, int, Rgb]]:
    if effect == "pulso":
        return [(A_PULSE, PHASE_TIME, tempo, c1)]
    if effect == "respiracao":
        return [(A_MORPH, PHASE_TIME, tempo, c1), (A_MORPH, PHASE_TIME, tempo, (0, 0, 0))]
    if effect == "morph":
        return [(A_MORPH, PHASE_TIME, tempo, c1), (A_MORPH, PHASE_TIME, tempo, c2)]
    if effect == "espectro":
        return [(A_MORPH, PHASE_TIME, tempo, c) for c in SPECTRUM]
    raise ValueError(effect)


def elc_zone_packets(zones: dict[int, dict]) -> list[bytes]:
    """Sequencia volatil completa: remove, start, cores/efeitos, finish-and-play.

    zones: {zona: {"efeito": str, "cor": Rgb, "cor2": Rgb, "tempo": int}}
    Zonas estaticas com a mesma cor sao agrupadas num unico setOneColor, como o
    alienrgb faz (ordem: por cor, ids crescentes).
    """
    if not zones:
        return []
    steps = [ELC_REMOVE, ELC_START]
    static: dict[Rgb, list[int]] = {}
    effects = []
    for z in sorted(zones):
        spec = zones[z]
        eff = spec.get("efeito", "estatico")
        if eff == "apagado":
            static.setdefault((0, 0, 0), []).append(z)
        elif eff == "estatico":
            static.setdefault(tuple(spec["cor"]), []).append(z)
        else:
            effects.append((z, spec))
    for color in sorted(static):
        steps.append(v4_set_one_color(color, static[color]))
    for z, spec in effects:
        steps += v4_action_packets(z, chassis_actions(spec["efeito"], spec["cor"],
                                                      spec.get("cor2", (0, 0, 0)),
                                                      spec.get("tempo", 0x64)))
    steps.append(ELC_FINISH_PLAY)
    return steps


# Perfil do botao de energia: 6 estados (SetPowerAction do SDK).
POWER_STATES = (0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60)  # ac_sleep ac_on charging bat_sleep bat_on bat_critical


def power_state_actions(state: int, ac: Rgb, bat: Rgb) -> list[tuple[int, int, int, Rgb]]:
    """Traducao de SetPowerAction(): acao original = [AC(power), BAT(power)] + extras."""
    P = lambda c: (A_POWER, 0x03, 0x64, c)  # noqa: E731
    base = [P(ac), P(bat)]
    zero = P((0, 0, 0))
    if state == 0x5B:  # AC dormindo
        return base + [P(ac), zero]
    if state == 0x5C:  # AC ligado
        return [(A_COLOR, 0x03, 0x64, ac), P(bat), P(ac)]
    if state == 0x5D:  # carregando
        return base + [P(ac), P(bat)]
    if state == 0x5E:  # bateria dormindo
        return base + [P(bat), zero]
    if state == 0x5F:  # bateria ligado
        return [(A_COLOR, 0x03, 0x64, ac), P(bat), P(bat)]
    if state == 0x60:  # bateria critica
        return [(A_PULSE, 0x03, 0x64, ac), P(bat), P(bat)]
    raise ValueError(state)


def elc_power_packets(ac: Rgb, bat: Rgb) -> list[bytes]:
    """34 pacotes identicos ao `alienrgb power-profile` quando ac == bat.

    Usa o controle 0x22 (animacoes dos estados de energia) com op 2, que o SDK chama
    de "finish and save": o proprio controlador guarda o comportamento do botao para
    quando o sistema dorme/esta desligado. Por isso o daemon so reenvia isto quando
    as cores MUDAM (ver engine.PowerLedger), nunca em loop, resume ou preview.
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
    # (byte1, byte3) combinacoes que nunca devem sair deste modulo
    (0x21, 0x02), (0x21, 0x06), (0x21, 0x07),
}


def assert_safe_elc(pkt: bytes) -> None:
    if len(pkt) != ELC_LEN or pkt[0] != 0x03:
        raise ValueError("pacote v4 malformado")
    if pkt[1] == 0xFF or (pkt[1], pkt[3]) in FORBIDDEN_V4:
        raise ValueError(f"pacote v4 proibido: {pkt[:6].hex()}")
    if pkt[1] not in (0x20, 0x21, 0x22, 0x23, 0x24, 0x27):
        raise ValueError(f"comando v4 fora da lista permitida: {pkt[1]:#x}")


def assert_safe_kb(pkt: bytes) -> None:
    if len(pkt) != KB_LEN or pkt[0] != KB_REPORT_ID:
        raise ValueError("pacote v5 malformado")
    if pkt[1] not in (0x80, 0x8B, 0x8C, 0x93, 0x94):
        raise ValueError(f"comando v5 fora da lista permitida: {pkt[1]:#x}")
