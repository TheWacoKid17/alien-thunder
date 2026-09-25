"""Imports Alienware Command Center presets from the Windows partition, read only.

FXRepository.db is COPIED to a temporary directory before it's read; nothing is
written to /mnt/windows. Only runs when asked (the "Import from Windows" button).
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import sqlite3
import tempfile

from . import layout, profiles
from .i18n import gettext as _

DB_GLOB = "/mnt/windows/Users/*/AppData/Local/Alienware/Alienware Command Center/FX/FXRepository.db"

KB_DEVICE = "0x1102_AdvKB0xD2B1"
ELC_DEVICE = "0x11020x0551"

# AWCC Animation.ID -> the closest effect that keeps the colors
KB_ANIM = {7: "breathing", 8: "pulse", 16: "wave", 17: "wave"}


def argb_hex(v: int) -> str:
    return "#%06x" % (int(v) & 0xFFFFFF)


def find_dbs() -> list[str]:
    """Every FXRepository.db (one per Windows user), largest first."""
    return sorted(glob.glob(DB_GLOB), key=lambda p: -os.path.getsize(p))


def _user_of(db: str) -> str:
    parts = db.split("/")
    return parts[parts.index("Users") + 1] if "Users" in parts else "?"


def _copy_db(src: str) -> tuple[str, str]:
    tmp = tempfile.mkdtemp(prefix="alien-thunder-awcc-")
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
            prof["keyboard"][str(int(led))] = color
    aid = anim.get("ID")
    pre = st.get("PredefinedAnimations") or []
    if not anim.get("Sequence") and pre:
        aid = pre[0].get("ID")
        cols = pre[0].get("Colors") or []
        if aid in (4, 19) and cols:  # "Color" / "Static Default Blue": every key
            for led in layout.AWCC_IDS:
                prof["keyboard"][str(led)] = argb_hex(cols[0])
        elif aid in KB_ANIM:
            prof["keyboard_effect"]["effect"] = KB_ANIM[aid]
            if cols:  # the preset's color, on every key, is what the effect animates
                for led in layout.AWCC_IDS:
                    prof["keyboard"][str(led)] = argb_hex(cols[0])


def _elc_part(data: dict, prof: dict):
    st = data.get("Static") or {}
    zones = {0: "touchpad", 2: "logo"}
    for seq in (st.get("Animation") or {}).get("Sequence") or []:
        acts = seq.get("Actions") or []
        if not acts or not acts[0].get("Color"):
            continue
        for led in seq.get("LEDs") or []:
            if led in zones:
                z = prof["chassis"][zones[led]]
                z["color"] = argb_hex(acts[0]["Color"][0])
                z["effect"] = "static"
                if acts[0].get("Effect") == 2:
                    z["effect"] = "pulse"
                elif acts[0].get("Effect") == 1 and len(acts) > 1:
                    z["effect"] = "breathing"
    for p in st.get("PredefinedAnimations") or []:
        pid, cols = p.get("ID"), p.get("Colors") or []
        if not cols:
            continue
        if pid == 7:  # Breathing
            for led in p.get("LEDs") or []:
                if led in zones:
                    prof["chassis"][zones[led]].update(effect="breathing", color=argb_hex(cols[0]))
        elif pid == 1:  # Morph
            for led in p.get("LEDs") or []:
                if led in zones:
                    prof["chassis"][zones[led]].update(effect="breathing", color=argb_hex(cols[0]))
        elif pid == 92:  # AC - Fully Charge
            prof["chassis"]["power"]["ac"] = argb_hex(cols[0])
        elif pid == 95:  # DC - Working
            prof["chassis"]["power"]["battery"] = argb_hex(cols[0])


def list_presets(db_paths: list[str] | None = None) -> list[dict]:
    """[{id, name, game, user, summary, profile}] for each AWCC lighting preset."""
    dbs = db_paths or find_dbs()
    if not dbs:
        raise FileNotFoundError(_("AWCC's FXRepository.db wasn't found under /mnt/windows"))
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
            prof["name"] = name or game or _("Preset %d") % pid
            item = out[pid] = {"id": f"{user}:{pid}", "name": prof["name"], "game": game or "",
                               "user": user, "profile": prof}
        if dev == KB_DEVICE:
            _kb_part(data, item["profile"])
        elif dev == ELC_DEVICE:
            _elc_part(data, item["profile"])
    result = []
    for item in out.values():
        item["profile"] = profiles.normalize(item["profile"])
        eff = item["profile"]["keyboard_effect"]
        ch = item["profile"]["chassis"]
        item["summary"] = (_("%d keys") % len(item["profile"]["keyboard"])
                           + (_(", effect %s") % eff["effect"] if eff["effect"] != "static" else "")
                           + _(", touchpad %s, logo %s") % (ch["touchpad"]["effect"], ch["logo"]["effect"])
                           + _(" (Windows user: %s)") % item["user"])
        result.append(item)
    return result
