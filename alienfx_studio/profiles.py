"""Perfis (JSON em ~/.config/alienfx-studio/profiles) e configuracao global."""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import unicodedata

from . import paths

DEFAULT_COLOR = "#ff2900"

DEFAULT_PROFILE = {
    "versao": 1,
    "nome": "Novo perfil",
    "brilho": 100,
    "teclado": {},
    "efeito_teclado": {
        "modo": "estatico",  # estatico | hardware | software
        "efeito": "respiracao",
        "cor1": "#ff0000",
        "cor2": "#0000ff",
        "modo_cor": 1,
        "tempo": 5,
        "velocidade": 1.0,
    },
    "chassi": {
        "touchpad": {"efeito": "estatico", "cor": DEFAULT_COLOR, "cor2": "#000000", "tempo": 100},
        "logo": {"efeito": "estatico", "cor": DEFAULT_COLOR, "cor2": "#000000", "tempo": 100},
        "energia": {"ac": DEFAULT_COLOR, "bateria": DEFAULT_COLOR},
    },
}

DEFAULT_CONFIG = {
    "versao": 1,
    "perfil_ativo": None,
    "cores_recentes": [],
    "grupos": {},
    "fps": 15,
    "chassi_backend": "hidraw",  # hidraw | alienrgb (so cores estaticas)
}

HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


class ProfileError(Exception):
    pass


# ------------------------------------------------------------------ util
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    if not isinstance(h, str) or not HEX_RE.match(h):
        raise ProfileError(f"cor invalida: {h!r}")
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(c) -> str:
    return "#%02x%02x%02x" % tuple(int(x) for x in c)


def norm_hex(h: str) -> str:
    return rgb_to_hex(hex_to_rgb(h))


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:48] or "perfil"


def _atomic_write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v
    return dst


# ------------------------------------------------------------------ perfil
def normalize(p: dict) -> dict:
    """Valida e completa um perfil com os valores padrao."""
    if not isinstance(p, dict):
        raise ProfileError("perfil deve ser um objeto JSON")
    out = _merge(copy.deepcopy(DEFAULT_PROFILE), {k: v for k, v in p.items() if k != "teclado"})
    kb = {}
    for k, v in (p.get("teclado") or {}).items():
        if isinstance(v, dict):  # formato antigo do alienfx-perfil
            v = v.get("cor")
        led = int(k)
        if not 0 <= led < 255:
            raise ProfileError(f"id de LED invalido: {k}")
        kb[str(led)] = norm_hex(v)
    out["teclado"] = dict(sorted(kb.items(), key=lambda kv: int(kv[0])))
    out["brilho"] = max(0, min(100, int(out.get("brilho", 100))))
    e = out["efeito_teclado"]
    if e["modo"] not in ("estatico", "hardware", "software"):
        e["modo"] = "estatico"
    e["cor1"], e["cor2"] = norm_hex(e["cor1"]), norm_hex(e["cor2"])
    e["modo_cor"] = int(e["modo_cor"]) if int(e["modo_cor"]) in (1, 2, 3) else 1
    e["tempo"] = max(0, min(255, int(e["tempo"])))
    e["velocidade"] = max(0.1, min(5.0, float(e["velocidade"])))
    for z in ("touchpad", "logo"):
        zz = out["chassi"][z]
        zz["cor"], zz["cor2"] = norm_hex(zz["cor"]), norm_hex(zz["cor2"])
        zz["tempo"] = max(0, min(255, int(zz["tempo"])))
    en = out["chassi"]["energia"]
    en["ac"], en["bateria"] = norm_hex(en["ac"]), norm_hex(en["bateria"])
    out["nome"] = str(out.get("nome") or "Sem nome")
    return out


def profile_path(slug: str) -> str:
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise ProfileError(f"nome de arquivo de perfil invalido: {slug!r}")
    return os.path.join(paths.PROFILES_DIR, slug + ".json")


def list_profiles() -> list[tuple[str, str]]:
    """[(slug, nome)] em ordem alfabetica de nome."""
    out = []
    if os.path.isdir(paths.PROFILES_DIR):
        for fn in os.listdir(paths.PROFILES_DIR):
            if fn.endswith(".json") and not fn.startswith("."):
                slug = fn[:-5]
                try:
                    with open(os.path.join(paths.PROFILES_DIR, fn), encoding="utf-8") as f:
                        name = json.load(f).get("nome") or slug
                except (OSError, ValueError):
                    name = slug + " (ilegível)"
                out.append((slug, name))
    return sorted(out, key=lambda x: x[1].lower())


def load(slug: str) -> dict:
    try:
        with open(profile_path(slug), encoding="utf-8") as f:
            return normalize(json.load(f))
    except FileNotFoundError:
        raise ProfileError(f"perfil não encontrado: {slug}") from None
    except ValueError as e:
        raise ProfileError(f"perfil {slug} inválido: {e}") from None


def save(slug: str, profile: dict) -> None:
    _atomic_write(profile_path(slug), normalize(profile))


def unique_slug(name: str) -> str:
    base = slugify(name)
    slug, n = base, 2
    while os.path.exists(profile_path(slug)):
        slug = f"{base}-{n}"
        n += 1
    return slug


def create(name: str, base: dict | None = None) -> str:
    p = normalize(copy.deepcopy(base) if base else DEFAULT_PROFILE)
    p["nome"] = name
    slug = unique_slug(name)
    save(slug, p)
    return slug


def duplicate(slug: str, new_name: str | None = None) -> str:
    p = load(slug)
    return create(new_name or (p["nome"] + " (cópia)"), p)


def rename(slug: str, new_name: str) -> str:
    p = load(slug)
    p["nome"] = new_name
    new_slug = slugify(new_name)
    if new_slug != slug:
        new_slug = unique_slug(new_name)
        save(new_slug, p)
        cfg = load_config()
        if cfg.get("perfil_ativo") == slug:
            cfg["perfil_ativo"] = new_slug
            save_config(cfg)
        os.unlink(profile_path(slug))
        return new_slug
    save(slug, p)
    return slug


def delete(slug: str) -> None:
    cfg = load_config()
    if cfg.get("perfil_ativo") == slug:
        raise ProfileError("não é possível excluir o perfil ativo; ative outro antes")
    os.unlink(profile_path(slug))


def find(name_or_slug: str) -> str:
    """Aceita slug ou nome (sem diferenciar maiusculas)."""
    profs = list_profiles()
    for slug, name in profs:
        if name_or_slug == slug:
            return slug
    for slug, name in profs:
        if name_or_slug.lower() in (name.lower(), slugify(name)):
            return slug
    raise ProfileError(f"perfil não encontrado: {name_or_slug}")


# ------------------------------------------------------------------ config
def load_config() -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(paths.CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (FileNotFoundError, ValueError):
        pass
    cfg["fps"] = max(1, min(20, int(cfg.get("fps", 15))))
    if cfg.get("chassi_backend") not in ("hidraw", "alienrgb"):
        cfg["chassi_backend"] = "hidraw"
    return cfg


def save_config(cfg: dict) -> None:
    _atomic_write(paths.CONFIG_FILE, cfg)


def active_slug() -> str | None:
    slug = load_config().get("perfil_ativo")
    if slug and os.path.exists(profile_path(slug)):
        return slug
    return None


def set_active(slug: str) -> None:
    load(slug)  # valida
    cfg = load_config()
    cfg["perfil_ativo"] = slug
    save_config(cfg)


# ------------------------------------------------------------------ migracao
def from_legacy(data: dict) -> dict:
    """Converte ~/.config/alienrgb/perfil.json (alienfx-perfil) para o formato novo."""
    p = copy.deepcopy(DEFAULT_PROFILE)
    p["nome"] = re.sub(r"\s*\(importado.*\)$", "", data.get("nome") or "Importado") or "Importado"
    p["teclado"] = {str(int(k)): norm_hex(v["cor"] if isinstance(v, dict) else v)
                    for k, v in (data.get("teclado") or {}).items()}
    ch = data.get("chassi") or {}
    if "touchpad" in ch:
        p["chassi"]["touchpad"]["cor"] = norm_hex(ch["touchpad"])
    if "back" in ch:
        p["chassi"]["logo"]["cor"] = norm_hex(ch["back"])
    if "power" in ch:
        p["chassi"]["energia"] = {"ac": norm_hex(ch["power"]), "bateria": norm_hex(ch["power"])}
    return normalize(p)


def ensure_initialized() -> list[str]:
    """Na primeira execucao importa o perfil legado e o torna ativo."""
    msgs = []
    os.makedirs(paths.PROFILES_DIR, exist_ok=True)
    if os.path.exists(paths.CONFIG_FILE) and list_profiles():
        return msgs
    cfg = load_config()
    slug = None
    if os.path.exists(paths.LEGACY_PROFILE):
        try:
            with open(paths.LEGACY_PROFILE, encoding="utf-8") as f:
                legacy = from_legacy(json.load(f))
            slug = create(legacy["nome"], legacy)
            msgs.append(f"perfil importado de {paths.LEGACY_PROFILE}: {legacy['nome']} ({slug})")
        except (OSError, ValueError, ProfileError) as e:
            msgs.append(f"falha ao importar perfil legado: {e}")
    if slug is None:
        existing = list_profiles()
        slug = existing[0][0] if existing else create("Padrão")
    if not cfg.get("perfil_ativo"):
        cfg["perfil_ativo"] = slug
    save_config(cfg)
    return msgs
