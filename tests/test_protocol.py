"""Testes dos codificadores contra pacotes comprovados (alienfx-perfil e alienrgb).

Rode com:  python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from alienfx_studio import effects, layout, profiles, protocol  # noqa: E402
from alienfx_studio.profiles import hex_to_rgb  # noqa: E402


def golden(name):
    with open(os.path.join(HERE, "golden", name), encoding="utf-8") as f:
        return json.load(f)


def plan_hex(g, length):
    """Extrai os payloads de um plano --dry-run --json do alienrgb."""
    out = []
    for s in g["plan"]["steps"]:
        if s.get("payload_hex") and s["transfer"] != "hid_feature_read_intent":
            h = s["payload_hex"].replace(" ", "")
            assert len(h) == 2 * length, (s["name"], len(h))
            out.append((s["name"], h))
    return out


class KeyboardV5(unittest.TestCase):
    def test_devops_identico_ao_alienfx_perfil(self):
        g = golden("devops_alienfx_perfil.json")
        prof = profiles.from_legacy(g["perfil"])
        colors = {int(k): hex_to_rgb(v) for k, v in prof["teclado"].items()}
        mine = [protocol.KB_RESET.hex(), protocol.KB_STATUS.hex()]
        mine += [p.hex() for p in protocol.kb_static_packets(colors)]
        self.assertEqual(mine, g["pacotes"])

    def test_todas_identico_ao_alienrgb(self):
        g = golden("kb_all.json")
        steps = plan_hex(g, 64)
        colors = {a["logical_id"]: (a["color"]["r"], a["color"]["g"], a["color"]["b"])
                  for a in g["plan"]["assignments"]}
        mine = [protocol.KB_RESET, protocol.KB_STATUS] + protocol.kb_static_packets(colors)
        self.assertEqual([p.hex() for p in mine], [h for _, h in steps])

    def test_efeito_global(self):
        p = protocol.kb_effect_packet("respiracao", 5, 2, (1, 2, 3), (4, 5, 6))
        self.assertEqual(p[:16].hex(), "cc80020500000101010101020304050" "6")
        self.assertEqual(p[16:], bytes(48))
        self.assertEqual(protocol.KB_EFFECT_OFF[:9].hex(), "cc8001fe0000010101")
        for name in protocol.KB_HW_EFFECTS:
            protocol.assert_safe_kb(protocol.kb_effect_packet(name, 5, 1, (0, 0, 0), (0, 0, 0)))


class ChassisV4(unittest.TestCase):
    def test_touchpad_estatico(self):
        steps = plan_hex(golden("touchpad_ff2900.json"), 33)
        mine = protocol.elc_zone_packets({0: {"efeito": "estatico", "cor": (0xff, 0x29, 0)}})
        self.assertEqual([p.hex() for p in mine], [h for _, h in steps])

    def test_touchpad_e_logo_mesma_cor(self):
        steps = plan_hex(golden("tp_back.json"), 33)
        c = (0x0a, 0x0b, 0x0c)
        mine = protocol.elc_zone_packets({0: {"efeito": "estatico", "cor": c},
                                          2: {"efeito": "estatico", "cor": c}})
        self.assertEqual([p.hex() for p in mine], [h for _, h in steps])

    def test_energia_igual_ao_alienrgb(self):
        for fn, c in (("power_ff2900.json", (0xff, 0x29, 0)), ("power_12ab34.json", (0x12, 0xab, 0x34))):
            steps = plan_hex(golden(fn), 33)
            mine = protocol.elc_power_packets(c, c)
            self.assertEqual(len(mine), 34)
            self.assertEqual([p.hex() for p in mine], [h for _, h in steps], fn)

    def test_energia_ac_bateria_separadas(self):
        ac, bat = (1, 2, 3), (9, 8, 7)
        pk = protocol.elc_power_packets(ac, bat)
        self.assertEqual(len(pk), 34)
        # estado 0x5c (AC ligado): 1o registro = cor AC tipo "color"
        i = [n for n, p in enumerate(pk) if p[:6].hex() == "032200010" "05c"][0]
        rec = pk[i + 2]
        self.assertEqual(rec[2:10].hex(), "0003d000fa010203")
        # estado 0x5f (bateria ligado): ultimos registros com a cor da bateria
        i = [n for n, p in enumerate(pk) if p[:6].hex() == "032200010" "05f"][0]
        self.assertEqual(pk[i + 2][10:18].hex(), "0203e80064090807")

    def test_efeitos_chassi(self):
        z = {0: {"efeito": "pulso", "cor": (1, 2, 3), "tempo": 100},
             2: {"efeito": "espectro", "cor": (0, 0, 0), "tempo": 50}}
        pk = protocol.elc_zone_packets(z)
        self.assertEqual(pk[0], protocol.ELC_REMOVE)
        self.assertEqual(pk[1], protocol.ELC_START)
        self.assertEqual(pk[2][:6].hex(), "032301000100")
        self.assertEqual(pk[3][:10].hex(), "03240107dc0064010203")
        self.assertEqual(pk[4][:6].hex(), "032301000102")
        self.assertEqual(len(pk), 2 + 2 + 3 + 1)  # espectro: 6 registros = 2 pacotes
        self.assertEqual(pk[-1], protocol.ELC_FINISH_PLAY)

    def test_seguranca(self):
        all_pk = protocol.elc_power_packets((1, 1, 1), (2, 2, 2))
        for eff in protocol.CHASSIS_EFFECTS:
            all_pk += protocol.elc_zone_packets({0: {"efeito": eff, "cor": (1, 2, 3), "cor2": (4, 5, 6), "tempo": 9}})
        for p in all_pk:
            protocol.assert_safe_elc(p)
            self.assertNotEqual(p[1], 0xFF)
            if p[1] == 0x21:  # controle geral: nunca save/default/startup
                self.assertIn(p[3], (1, 3, 4, 5))
        for bad in ([0x03, 0xFF], [0x03, 0x21, 0x00, 0x02, 0xFF, 0xFF], [0x03, 0x21, 0x00, 0x06],
                    [0x03, 0x21, 0x00, 0x07]):
            with self.assertRaises(ValueError):
                protocol.assert_safe_elc(protocol._elc(bad))
        with self.assertRaises(ValueError):
            protocol.assert_safe_kb(protocol._kb([0xCC, 0x95]))


class Layout(unittest.TestCase):
    AWCC = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28,
            29, 30, 31, 32, 33, 35, 19, 40, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 16,
            59, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 18, 81, 82, 83, 84, 85, 86, 87,
            88, 89, 90, 91, 92, 94, 114, 17, 100, 101, 103, 104, 105, 110, 107, 111, 112, 109, 133,
            134, 135}

    def test_92_ids_do_awcc(self):
        self.assertEqual(set(layout.AWCC_IDS), self.AWCC)
        self.assertEqual(len([k for k in layout.KEYS if not k.extra]), 86)
        self.assertIn(106, layout.KEY_BY_ID[107].leds)

    def test_grupos_validos(self):
        for name, ids in layout.GROUPS.items():
            for i in ids:
                self.assertIn(i, layout.KEY_BY_ID, name)


class Perfis(unittest.TestCase):
    def test_migracao_legado(self):
        g = golden("devops_alienfx_perfil.json")
        p = profiles.from_legacy(g["perfil"])
        self.assertEqual(p["nome"], "Devops")
        self.assertEqual(len(p["teclado"]), 92)
        self.assertEqual(p["chassi"]["touchpad"]["cor"], "#ff2900")
        self.assertEqual(p["chassi"]["energia"], {"ac": "#ff2900", "bateria": "#ff2900"})
        self.assertEqual(profiles.normalize(p), p)

    def test_efeitos_software(self):
        base = {0: (255, 0, 0), 107: (0, 255, 0)}
        for name in effects.SW_EFFECTS:
            fx = effects.SoftwareEffect(name, base, {"velocidade": 1.0, "cor1_rgb": (0, 0, 255)}, 1.0)
            for t in (0.0, 0.3, 1.7, 10.0):
                fr = fx.frame(t)
                self.assertTrue(set(layout.AWCC_IDS) <= set(fr))
                for c in fr.values():
                    self.assertTrue(all(0 <= x <= 255 for x in c))
                protocol.kb_static_packets(fr)


if __name__ == "__main__":
    unittest.main()
