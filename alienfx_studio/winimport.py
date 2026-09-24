"""Importa predefinicoes do Alienware Command Center (particao Windows, somente leitura).

O FXRepository.db e COPIADO para um diretorio temporario antes de ser lido; nada
e escrito em /mnt/windows. Usado apenas sob demanda (botao "Importar do Windows").
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import sqlite3
import tempfile

from . import layout, profiles

DB_GLOB = "/mnt/windows/Users/*/AppData/Local/Alienware/Alienware Command Center/FX/FXRepository.db"

KB_DEVICE = "0x1102_AdvKB0xD2B1"
ELC_DEVICE = "0x11020x0551"

# Animation.ID do AWCC -> efeito de hardware do teclado (aproximacao)
KB_ANIM = {7: ("respiracao", 1), 8: ("morph", 3), 16: ("arco_iris", 3), 17: ("ricochete", 1)}


def argb_hex(v: int) -> str:
    return "#%06x" % (int(v) & 0xFFFFFF)


def find_dbs() -> list[str]:
    """Todos os FXRepository.db (um por usuario do Windows), maiores primeiro."""
    return sorted(glob.glob(DB_GLOB), key=lambda p: -os.path.getsize(p))


def _user_of(db: str) -> str:
    parts = db.split("/")
    return parts[parts.index("Users") + 1] if "Users" in parts else "?"


def _copy_db(src: str) -> tuple[str, str]:
    tmp = tempfile.mkdtemp(prefix="alienfx-awcc-")
    dst = os.path.join(tmp, "FXRepository.db")
    shutil.copy2(src, dst)
    for ext in ("-wal", "-shm"):
        if os.path.exists(src + ext):
            shutil.copy2(src + ext, dst + ext)
    return tmp, dst


def _kb_part(data: dict, prof: dict):
    st = data.get("Static") or {}
    anim = st.get("Animation") or {}
    for seq in anim.get("Sequence") or []:
        acts = seq.get("Actions") or []
        if not acts or not acts[0].get("Color"):
            continue
        color = argb_hex(acts[0]["Color"][0])
        for led in seq.get("LEDs") or []:
            prof["teclado"][str(int(led))] = color
    aid = anim.get("ID")
    pre = st.get("PredefinedAnimations") or []
    if not anim.get("Sequence") and pre:
        aid = pre[0].get("ID")
        cols = pre[0].get("Colors") or []
        if aid in (4, 19) and cols:  # "Color" / "Static Default Blue": todas as teclas
            for led in layout.AWCC_IDS:
                prof["teclado"][str(led)] = argb_hex(cols[0])
        elif aid in KB_ANIM:
            eff, mode = KB_ANIM[aid]
            e = prof["efeito_teclado"]
            e.update(modo="hardware", efeito=eff, modo_cor=mode)
            if cols:
                e["cor1"] = argb_hex(cols[0])
            if len(cols) > 1:
                e["cor2"] = argb_hex(cols[1])


def _elc_part(data: dict, prof: dict):
    st = data.get("Static") or {}
    zones = {0: "touchpad", 2: "logo"}
    for seq in (st.get("Animation") or {}).get("Sequence") or []:
        acts = seq.get("Actions") or []
        if not acts or not acts[0].get("Color"):
            continue
        for led in seq.get("LEDs") or []:
            if led in zones:
                z = prof["chassi"][zones[led]]
                z["cor"] = argb_hex(acts[0]["Color"][0])
                z["efeito"] = "estatico"
                if acts[0].get("Effect") == 2:
                    z["efeito"] = "pulso"
                elif acts[0].get("Effect") == 1 and len(acts) > 1:
                    z["efeito"] = "morph"
                    z["cor2"] = argb_hex(acts[1]["Color"][0])
    for p in st.get("PredefinedAnimations") or []:
        pid, cols = p.get("ID"), p.get("Colors") or []
        if not cols:
            continue
        if pid == 7:  # Breathing
            for led in p.get("LEDs") or []:
                if led in zones:
                    prof["chassi"][zones[led]].update(efeito="respiracao", cor=argb_hex(cols[0]))
        elif pid == 1:  # Morph
            for led in p.get("LEDs") or []:
                if led in zones:
                    prof["chassi"][zones[led]].update(efeito="morph", cor=argb_hex(cols[0]),
                                                      cor2=argb_hex(cols[1] if len(cols) > 1 else 0))
        elif pid == 92:  # AC - Fully Charge
            prof["chassi"]["energia"]["ac"] = argb_hex(cols[0])
        elif pid == 95:  # DC - Working
            prof["chassi"]["energia"]["bateria"] = argb_hex(cols[0])


def list_presets(db_paths: list[str] | None = None) -> list[dict]:
    """[{id, nome, jogo, usuario, resumo, perfil}] das predefinicoes de iluminacao do AWCC."""
    dbs = db_paths or find_dbs()
    if not dbs:
        raise FileNotFoundError("FXRepository.db do AWCC não encontrado em /mnt/windows")
    result = []
    for src in dbs:
        result += _presets_from(src)
    return result


def _presets_from(src: str) -> list[dict]:
    user = _user_of(src)
    tmp, db = _copy_db(src)
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute("""
            SELECT p.PresetId, p.Name, g.Name, di.DeviceId, d.DataJson
              FROM PresetDetailInfo d
              JOIN GamePresets p ON p.PresetId = d.PresetId
              JOIN DeviceInfo di ON di.DeviceInstanceId = d.DeviceInstanceId
              LEFT JOIN GameInfoFX g ON g.GameID = p.GameID
             WHERE d.CapabilityId = 1
             ORDER BY p.PresetId""").fetchall()
        con.close()
    except sqlite3.Error:
        rows = []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out: dict[int, dict] = {}
    for pid, name, game, dev, dj in rows:
        try:
            data = json.loads(dj)
        except (TypeError, ValueError):
            continue
        item = out.get(pid)
        if item is None:
            prof = json.loads(json.dumps(profiles.DEFAULT_PROFILE))
            prof["nome"] = name or game or f"Predefinição {pid}"
            item = out[pid] = {"id": f"{user}:{pid}", "nome": prof["nome"], "jogo": game or "",
                               "usuario": user, "perfil": prof}
        if dev == KB_DEVICE:
            _kb_part(data, item["perfil"])
        elif dev == ELC_DEVICE:
            _elc_part(data, item["perfil"])
    result = []
    for item in out.values():
        item["perfil"] = profiles.normalize(item["perfil"])
        eff = item["perfil"]["efeito_teclado"]
        ch = item["perfil"]["chassi"]
        item["resumo"] = (f"{len(item['perfil']['teclado'])} teclas"
                          + (f", efeito {eff['efeito']}" if eff["modo"] != "estatico" else "")
                          + f", touchpad {ch['touchpad']['efeito']}, logo {ch['logo']['efeito']}"
                          + f" (usuário Windows: {item['usuario']})")
        result.append(item)
    return result
