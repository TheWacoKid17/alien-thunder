"""LED table for the Alienware m16 R2 keyboard, 0d62:d2b1.

LOCAL PATCH: labels and shapes changed from ABNT2 to the US (ANSI) layout; LED IDs
are unchanged. Undo with: git checkout alien_thunder/layout.py alien_thunder/gui.py tests/test_protocol.py

Original description (ABNT2):

IDs and names come from the Alienware Command Center metadata (FXMetadata/0x1102_AdvKB,
92 LEDs). The rectangles (x, y, width, height) come from AWCC's own drawing of the
Brazilian keyboard (UK_BPortuguese_1102_AdvKB_ModelUserControl.xaml, "maskLedNNN_Top"),
in the original canvas units (~1005 x 359).

86 keys physically exist on the ABNT2 layout. The other 6 AWCC IDs (JP1..JP5, UK1)
belong to the Japanese and UK keyboards and sit in an "extra LEDs" strip. AWCC calls
the space bar LED 107, but alienrgb showed LED 106 lighting the whole bar on this
laptop, so the Space key drives both.
"""
from __future__ import annotations

from .i18n import N_

# id: (short label, full name, AWCC name, rectangle)
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
    20: ("`", "Backtick / tilde", "`", (0.1, 44.5, 52.7, 52.7)),
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
    31: ("-", "Hyphen", "-", (698.2, 44.5, 52.7, 52.7)),
    32: ("=", "Equals", "=", (762.3, 44.5, 52.7, 52.7)),
    35: ("⌫", "Backspace", "Backspace", (825.8, 44.5, 116.1, 52.7)),
    19: ("Mic", "Microphone mute", "Microphone Mute", (952.8, 44.5, 52.7, 52.7)),
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
    52: ("[", "Bracket [", "[", (729.8, 110.0, 52.6, 52.7)),
    53: ("]", "Bracket ]", "]", (793.4, 110.0, 52.6, 52.7)),
    55: ("\\", "Backslash", "\\", (857.6, 110.0, 83.9, 52.7)),
    16: ("Mute", "Speaker mute", "Speaker Mute", (953.1, 110.0, 52.0, 52.7)),
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
    71: (";", "Semicolon", ";", (682.3, 175.0, 52.6, 52.7)),
    72: ("'", "Apostrophe / quote", "'", (745.9, 175.0, 52.6, 52.7)),
    74: ("Enter", "Enter", "Enter", (809.7, 175.0, 131.8, 52.7)),
    18: ("Vol+", "Volume +", "Volume Up", (953.1, 175.0, 52.0, 52.7)),
    81: ("Shift", "Left Shift", "Left Shift", (0.1, 240.5, 131.7, 52.7)),
    83: ("Z", "Z", "Z", (143.3, 240.5, 52.6, 52.7)),
    84: ("X", "X", "X", (206.6, 240.5, 52.6, 52.7)),
    85: ("C", "C", "C", (270.6, 240.5, 52.6, 52.7)),
    86: ("V", "V", "V", (333.9, 240.5, 52.6, 52.7)),
    87: ("B", "B", "B", (397.1, 240.5, 52.6, 52.7)),
    88: ("N", "N", "N", (460.2, 240.5, 52.6, 52.7)),
    89: ("M", "M", "M", (524.5, 240.5, 52.6, 52.7)),
    90: (",", "Comma", ",", (586.5, 240.5, 52.6, 52.7)),
    91: (".", "Period", ".", (651.3, 240.5, 52.6, 52.7)),
    92: ("/", "Slash", "/", (714.7, 240.5, 52.6, 52.7)),
    94: ("Shift", "Right Shift", "Right Shift", (778.2, 240.5, 99.7, 52.7)),
    114: ("↑", "Up arrow (PgUp)", "Page Up", (889.5, 240.5, 52.0, 52.7)),
    17: ("Vol−", "Volume −", "Volume Down", (953.1, 240.5, 52.0, 52.7)),
    100: ("Ctrl", "Left Ctrl", "Left Ctrl", (0.0, 306.0, 69.4, 52.7)),
    101: ("Fn", "Fn", "Fn", (79.1, 306.0, 52.6, 52.7)),
    103: ("Win", "Windows / Super", "Left Windows", (143.2, 306.0, 52.6, 52.7)),
    104: ("Alt", "Alt", "Left Alt", (206.4, 306.0, 52.6, 52.7)),
    107: ("Space", "Space bar", "JP6", (270.3, 306.0, 305.8, 52.7)),
    111: ("AltGr", "Alt Gr", "Rigth Alt", (587.7, 306.0, 52.6, 52.7)),
    109: ("Menu", "Key right of AltGr", "Right Windows", (651.3, 306.0, 52.6, 52.7)),
    112: ("Ctrl", "Right Ctrl", "Rigth Ctrl", (715.3, 306.0, 99.7, 52.7)),
    133: ("←", "Left arrow", "Left Arrow", (826.2, 306.0, 52.0, 52.7)),
    134: ("↓", "Down arrow (PgDn)", "Page Down", (889.5, 306.0, 52.0, 52.7)),
    135: ("→", "Right arrow", "Right Arrow", (953.1, 306.0, 52.0, 52.7)),
}

# AWCC IDs with no physical key on ABNT2 (they belong to JP/UK keyboards): the extras strip.
_EXTRA = {
    33: ("JP1", "LED JP1 (¥ on the Japanese keyboard)", "JP1"),
    54: ("JP2", "LED JP2 (ろ on the Japanese keyboard)", "JP2"),
    59: ("JP3", "LED JP3 (Japanese keyboard)", "JP3"),
    73: ("UK1", "LED UK1 (# on the UK keyboard)", "UK1"),
    82: ("UK2", "LED UK2 (\\ next to Z on UK/ABNT2 keyboards)", "UK2"),
    105: ("JP4", "LED JP4 (無変換 on the Japanese keyboard)", "JP4"),
    110: ("JP5", "LED JP5 (変換 on the Japanese keyboard)", "JP5"),
}

CANVAS_W = 1005.2
KEYS_H = 358.7
EXTRA_Y = 378.0
EXTRA_H = 30.0
CANVAS_H = EXTRA_Y + EXTRA_H

# Extra LEDs lit together with a key (main id -> extra ids)
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
AWCC_IDS = sorted(KEY_BY_ID)  # the 92 AWCC IDs
ALL_LEDS = sorted({led for k in KEYS for led in k.leds})  # 92 + 106
assert len(AWCC_IDS) == 92, len(AWCC_IDS)


def key_of_led(led: int) -> int | None:
    for k in KEYS:
        if led in k.leds:
            return k.id
    return None


def rel_x(led: int) -> float:
    """Horizontal position of the LED, 0..1, for the wave effects."""
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


_letters = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 62, 63, 64, 65, 66, 67, 68, 69, 70,
            83, 84, 85, 86, 87, 88, 89]

# Keyed by the English name; the GUI shows the translation.
GROUPS: dict[str, list[int]] = {
    N_("All"): [k.id for k in KEYS if not k.extra],
    N_("Letters"): _letters,
    N_("Numbers"): list(range(21, 31)),
    N_("F1–F12"): list(range(1, 13)),
    N_("Arrows"): [114, 133, 134, 135],
    N_("WASD"): [43, 62, 63, 64],
    N_("Modifiers"): [61, 81, 94, 100, 101, 103, 104, 109, 111, 112],
    N_("Media/volume"): [16, 17, 18, 19],
    N_("Editing block"): [13, 14, 15, 35, 40, 74],
    N_("Symbols"): [20, 31, 32, 52, 53, 55, 71, 72, 90, 91, 92],
    N_("Function row (Esc…Del)"): list(range(0, 16)),
}
