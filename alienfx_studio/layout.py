"""Tabela de LEDs do teclado ABNT2 do Alienware m16 R2 (0d62:d2b1).

IDs e nomes = metadados do Alienware Command Center (FXMetadata/0x1102_AdvKB,
92 LEDs). Retangulos (x, y, largura, altura) extraidos do desenho oficial do AWCC
para o teclado brasileiro (UK_BPortuguese_1102_AdvKB_ModelUserControl.xaml,
"maskLedNNN_Top"), em unidades do canvas original (~1005 x 359).

86 teclas existem fisicamente no ABNT2. Os outros 6 IDs do AWCC (JP1..JP6 exceto
JP6, UK1) pertencem aos teclados japones/ingles; ficam numa faixa "LEDs extras".
A barra de espaco e o LED 107 no AWCC, mas o alienrgb confirmou visualmente o
LED 106 acendendo a barra inteira neste notebook -> a tecla Espaco controla os dois.
"""
from __future__ import annotations

# id: (rotulo curto, nome completo, nome AWCC, retangulo)
_K = {
    0: ("Esc", "Esc", "ESC", (0.1, 0.0, 52.2, 31.0)),
    1: ("F1", "F1", "F1", (64.1, 0.0, 52.2, 31.0)),
    2: ("F2", "F2", "F2", (127.5, 0.0, 52.2, 31.0)),
    3: ("F3", "F3", "F3", (191.0, 0.0, 52.2, 31.0)),
    4: ("F4", "F4", "F4", (254.2, 0.0, 52.2, 31.0)),
    5: ("F5", "F5", "F5", (317.6, 0.0, 52.2, 31.0)),
    6: ("F6", "F6", "F6", (380.7, 0.0, 52.2, 31.0)),
    7: ("F7", "F7", "F7", (445.1, 0.0, 52.2, 31.0)),
    8: ("F8", "F8", "F8", (508.6, 0.0, 52.2, 31.0)),
    9: ("F9", "F9", "F9", (572.2, 0.0, 52.2, 31.0)),
    10: ("F10", "F10", "F10", (636.2, 0.0, 52.2, 31.0)),
    11: ("F11", "F11", "F11", (699.5, 0.0, 52.2, 31.0)),
    12: ("F12", "F12", "F12", (762.6, 0.0, 52.2, 31.0)),
    13: ("Home", "Home", "Home", (826.0, 0.0, 52.2, 31.0)),
    14: ("End", "End", "End", (889.7, 0.0, 52.2, 31.0)),
    15: ("Del", "Delete", "Delete", (953.1, 0.0, 52.2, 31.0)),
    20: ("'", "Apóstrofo / aspas", "`", (0.1, 44.5, 52.7, 52.7)),
    21: ("1", "1", "1", (63.9, 44.5, 52.7, 52.7)),
    22: ("2", "2", "2", (127.2, 44.5, 52.7, 52.7)),
    23: ("3", "3", "3", (190.5, 44.5, 52.7, 52.7)),
    24: ("4", "4", "4", (254.0, 44.5, 52.7, 52.7)),
    25: ("5", "5", "5", (318.1, 44.5, 52.7, 52.7)),
    26: ("6", "6", "6", (381.4, 44.5, 52.7, 52.7)),
    27: ("7", "7", "7", (444.7, 44.5, 52.7, 52.7)),
    28: ("8", "8", "8", (508.1, 44.5, 52.7, 52.7)),
    29: ("9", "9", "9", (571.7, 44.5, 52.7, 52.7)),
    30: ("0", "0", "0", (635.7, 44.5, 52.7, 52.7)),
    31: ("-", "Hífen", "-", (698.2, 44.5, 52.7, 52.7)),
    32: ("=", "Igual", "=", (762.3, 44.5, 52.7, 52.7)),
    35: ("⌫", "Backspace", "Backspace", (825.8, 44.5, 116.1, 52.7)),
    19: ("Mic", "Mudo do microfone", "Microphone Mute", (952.8, 44.5, 52.7, 52.7)),
    40: ("Tab", "Tab", "Tab", (0.1, 110.0, 84.0, 52.7)),
    42: ("Q", "Q", "Q", (95.7, 110.0, 52.6, 52.7)),
    43: ("W", "W", "W", (158.0, 110.0, 52.6, 52.7)),
    44: ("E", "E", "E", (222.1, 110.0, 52.6, 52.7)),
    45: ("R", "R", "R", (286.3, 110.0, 52.6, 52.7)),
    46: ("T", "T", "T", (349.6, 110.0, 52.6, 52.7)),
    47: ("Y", "Y", "Y", (413.7, 110.0, 52.6, 52.7)),
    48: ("U", "U", "U", (477.0, 110.0, 52.6, 52.7)),
    49: ("I", "I", "I", (540.2, 110.0, 52.6, 52.7)),
    50: ("O", "O", "O", (603.7, 110.0, 52.6, 52.7)),
    51: ("P", "P", "P", (667.2, 110.0, 52.6, 52.7)),
    52: ("´", "Acento agudo", "[", (729.8, 110.0, 52.6, 52.7)),
    53: ("[", "Colchete [", "]", (793.4, 110.0, 52.6, 52.7)),
    55: ("Enter", "Enter", "\\", (857.6, 110.0, 83.9, 117.1)),
    16: ("Mudo", "Mudo do alto-falante", "Speaker Mute", (953.1, 110.0, 52.0, 52.7)),
    61: ("Caps", "Caps Lock", "Caps Lock", (0.1, 175.0, 100.2, 52.7)),
    62: ("A", "A", "A", (111.9, 175.0, 52.6, 52.7)),
    63: ("S", "S", "S", (174.1, 175.0, 52.6, 52.7)),
    64: ("D", "D", "D", (238.2, 175.0, 52.6, 52.7)),
    65: ("F", "F", "F", (301.5, 175.0, 52.6, 52.7)),
    66: ("G", "G", "G", (364.7, 175.0, 52.6, 52.7)),
    67: ("H", "H", "H", (428.8, 175.0, 52.6, 52.7)),
    68: ("J", "J", "J", (492.1, 175.0, 52.6, 52.7)),
    69: ("K", "K", "K", (555.3, 175.0, 52.6, 52.7)),
    70: ("L", "L", "L", (618.9, 175.0, 52.6, 52.7)),
    71: ("Ç", "Ç", ";", (682.3, 175.0, 52.6, 52.7)),
    72: ("~", "Til", "'", (745.9, 175.0, 52.6, 52.7)),
    74: ("]", "Colchete ]", "Enter", (809.7, 175.0, 52.6, 52.7)),
    18: ("Vol+", "Volume +", "Volume Up", (953.1, 175.0, 52.0, 52.7)),
    81: ("Shift", "Shift esquerdo", "Left Shift", (0.1, 240.5, 67.7, 52.7)),
    82: ("\\", "Barra invertida", "UK2", (79.2, 240.5, 52.6, 52.7)),
    83: ("Z", "Z", "Z", (143.3, 240.5, 52.6, 52.7)),
    84: ("X", "X", "X", (206.6, 240.5, 52.6, 52.7)),
    85: ("C", "C", "C", (270.6, 240.5, 52.6, 52.7)),
    86: ("V", "V", "V", (333.9, 240.5, 52.6, 52.7)),
    87: ("B", "B", "B", (397.1, 240.5, 52.6, 52.7)),
    88: ("N", "N", "N", (460.2, 240.5, 52.6, 52.7)),
    89: ("M", "M", "M", (524.5, 240.5, 52.6, 52.7)),
    90: (",", "Vírgula", ",", (586.5, 240.5, 52.6, 52.7)),
    91: (".", "Ponto", ".", (651.3, 240.5, 52.6, 52.7)),
    92: (";", "Ponto e vírgula", "/", (714.7, 240.5, 52.6, 52.7)),
    94: ("Shift", "Shift direito", "Right Shift", (778.2, 240.5, 99.7, 52.7)),
    114: ("↑", "Seta para cima (PgUp)", "Page Up", (889.5, 240.5, 52.0, 52.7)),
    17: ("Vol−", "Volume −", "Volume Down", (953.1, 240.5, 52.0, 52.7)),
    100: ("Ctrl", "Ctrl esquerdo", "Left Ctrl", (0.0, 306.0, 69.4, 52.7)),
    101: ("Fn", "Fn", "Fn", (79.1, 306.0, 52.6, 52.7)),
    103: ("Win", "Windows / Super", "Left Windows", (143.2, 306.0, 52.6, 52.7)),
    104: ("Alt", "Alt", "Left Alt", (206.4, 306.0, 52.6, 52.7)),
    107: ("Espaço", "Barra de espaço", "JP6", (270.3, 306.0, 305.8, 52.7)),
    111: ("AltGr", "Alt Gr", "Rigth Alt", (587.7, 306.0, 52.6, 52.7)),
    109: ("Menu", "Tecla à direita do AltGr", "Right Windows", (651.3, 306.0, 52.6, 52.7)),
    112: ("Ctrl", "Ctrl direito", "Rigth Ctrl", (715.3, 306.0, 99.7, 52.7)),
    133: ("←", "Seta para esquerda", "Left Arrow", (826.2, 306.0, 52.0, 52.7)),
    134: ("↓", "Seta para baixo (PgDn)", "Page Down", (889.5, 306.0, 52.0, 52.7)),
    135: ("→", "Seta para direita", "Right Arrow", (953.1, 306.0, 52.0, 52.7)),
}

# IDs do AWCC sem tecla fisica no ABNT2 (sao de teclados JP/UK) -> faixa de extras.
_EXTRA = {
    33: ("JP1", "LED JP1 (¥ do teclado japonês)", "JP1"),
    54: ("JP2", "LED JP2 (ろ do teclado japonês)", "JP2"),
    59: ("JP3", "LED JP3 (teclado japonês)", "JP3"),
    73: ("UK1", "LED UK1 (# do teclado inglês)", "UK1"),
    105: ("JP4", "LED JP4 (無変換 do teclado japonês)", "JP4"),
    110: ("JP5", "LED JP5 (変換 do teclado japonês)", "JP5"),
}

CANVAS_W = 1005.2
KEYS_H = 358.7
EXTRA_Y = 378.0
EXTRA_H = 30.0
CANVAS_H = EXTRA_Y + EXTRA_H

# LED adicional acionado junto com a tecla (id principal -> ids extras)
LINKED = {107: (106,)}


class Key:
    __slots__ = ("id", "label", "name", "awcc", "rect", "extra", "leds")

    def __init__(self, id_, label, name, awcc, rect, extra=False):
        self.id = id_
        self.label = label
        self.name = name
        self.awcc = awcc
        self.rect = rect
        self.extra = extra
        self.leds = (id_,) + LINKED.get(id_, ())

    @property
    def center(self):
        x, y, w, h = self.rect
        return x + w / 2, y + h / 2


def _build():
    keys = [Key(i, *v) for i, v in _K.items()]
    x = 0.0
    for i, (lab, name, awcc) in _EXTRA.items():
        keys.append(Key(i, lab, name, awcc, (x, EXTRA_Y, 60.0, EXTRA_H), extra=True))
        x += 68.0
    return keys


KEYS: list[Key] = _build()
KEY_BY_ID = {k.id: k for k in KEYS}
AWCC_IDS = sorted(KEY_BY_ID)  # os 92 IDs do AWCC
ALL_LEDS = sorted({led for k in KEYS for led in k.leds})  # 92 + 106
assert len(AWCC_IDS) == 92, len(AWCC_IDS)


def key_of_led(led: int) -> int | None:
    for k in KEYS:
        if led in k.leds:
            return k.id
    return None


def rel_x(led: int) -> float:
    """Posicao horizontal 0..1 do LED (para efeitos de onda)."""
    kid = key_of_led(led)
    if kid is None:
        return 0.5
    k = KEY_BY_ID[kid]
    if k.extra:
        return 0.5
    return k.center[0] / CANVAS_W


def rel_y(led: int) -> float:
    kid = key_of_led(led)
    if kid is None:
        return 0.5
    k = KEY_BY_ID[kid]
    return min(1.0, k.center[1] / KEYS_H)


_letters = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            83, 84, 85, 86, 87, 88, 89]

GROUPS: dict[str, list[int]] = {
    "Todas": [k.id for k in KEYS],
    "Letras": _letters,
    "Números": list(range(21, 31)),
    "F1–F12": list(range(1, 13)),
    "Setas": [114, 133, 134, 135],
    "WASD": [43, 62, 63, 64],
    "Modificadores": [61, 81, 94, 100, 101, 103, 104, 109, 111, 112],
    "Mídia/volume": [16, 17, 18, 19],
    "Bloco de edição": [13, 14, 15, 35, 40, 55],
    "Símbolos": [20, 31, 32, 52, 53, 72, 74, 82, 90, 91, 92],
    "Linha F (Esc…Del)": list(range(0, 16)),
    "LEDs extras (JP/UK)": list(_EXTRA),
}
