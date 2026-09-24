"""Linha de comando do AlienFX Studio."""
from __future__ import annotations

import argparse
import json
import sys

from . import engine, hw, profiles

USO = """alienfx-studio                    abre a interface gráfica
alienfx-studio list               lista os perfis (* = ativo)
alienfx-studio set <perfil>       torna o perfil ativo (persistente) e aplica
alienfx-studio apply [perfil]     aplica agora (padrão: o ativo); não muda o ativo
alienfx-studio status             estado do serviço e dos dispositivos
alienfx-studio power [perfil]     grava agora as cores do botão de energia
alienfx-studio import-windows [--list | --id N ...]
                                  importa predefinições do AWCC (/mnt/windows)
alienfx-studio daemon             serviço (usado pelo systemd --user)"""


def _apply_direct(slug: str, is_active: bool) -> int:
    prof = profiles.load(slug)
    cfg = profiles.load_config()
    eng = engine.Engine(log=lambda m: print(m))
    try:
        eng.apply(prof, power=is_active, force=True, backend=cfg["chassi_backend"])
    except hw.DeviceError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    finally:
        eng.close()
    if prof["efeito_teclado"]["modo"] == "software":
        print("aviso: efeito de software precisa do serviço (systemctl --user start alienfx-studio)")
    return 0


def cmd_list(_a) -> int:
    act = profiles.active_slug()
    for slug, name in profiles.list_profiles():
        print(f"{'*' if slug == act else ' '} {slug:24s} {name}")
    return 0


def cmd_set(a) -> int:
    slug = profiles.find(a.perfil)
    profiles.set_active(slug)
    print(f"perfil ativo: {slug}")
    if engine.daemon_running():
        ok = engine.daemon_call("Reload")
        print("aplicado pelo serviço" if ok else "serviço tentará de novo (veja 'status')")
        return 0 if ok else 1
    return _apply_direct(slug, True)


def cmd_apply(a) -> int:
    act = profiles.active_slug()
    slug = profiles.find(a.perfil) if a.perfil else act
    if not slug:
        print("nenhum perfil ativo", file=sys.stderr)
        return 1
    if engine.daemon_running():
        ok = engine.daemon_call("ApplyProfile", "" if slug == act else slug)
        print(f"aplicado: {slug}" if ok else "falha; o serviço tentará de novo (veja 'status')")
        return 0 if ok else 1
    return _apply_direct(slug, slug == act)


def cmd_status(_a) -> int:
    info = engine.env_info()
    print(f"teclado (0d62:d2b1): {info['teclado'] or 'não encontrado'}")
    print(f"chassi  (187c:0551): {info['chassi'] or 'não encontrado'}")
    print(f"perfil ativo: {profiles.active_slug()}")
    if engine.daemon_running():
        st = json.loads(str(engine.daemon_call("Status")))
        print("serviço: rodando (pid %s)" % st["pid"])
        for k in ("aplicando", "override", "efeito_software", "ultimo_erro"):
            print(f"  {k}: {st.get(k)}")
    else:
        print("serviço: parado")
    return 0


def cmd_power(a) -> int:
    slug = profiles.find(a.perfil) if a.perfil else profiles.active_slug()
    if engine.daemon_running():
        return 0 if engine.daemon_call("WritePower", slug) else 1
    eng = engine.Engine()
    try:
        eng.write_power_now(profiles.load(slug), profiles.load_config()["chassi_backend"])
    except hw.DeviceError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_import(a) -> int:
    from . import winimport
    items = winimport.list_presets()
    if a.list or not a.id:
        for it in items:
            print(f"{it['id']:14s} {it['nome'][:34]:34s} {it['resumo']}")
        return 0
    for it in items:
        if it["id"] in a.id:
            slug = profiles.create(it["nome"] + " (Windows)", it["perfil"])
            print(f"importado: {slug}")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("gui", "--gui"):
        from . import gui
        return gui.main()
    if argv[0] == "daemon":
        from . import daemon
        return daemon.main()
    p = argparse.ArgumentParser(prog="alienfx-studio", usage=USO)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("set")
    s.add_argument("perfil")
    s = sub.add_parser("apply")
    s.add_argument("perfil", nargs="?")
    sub.add_parser("status")
    s = sub.add_parser("power")
    s.add_argument("perfil", nargs="?")
    s = sub.add_parser("import-windows")
    s.add_argument("--list", action="store_true")
    s.add_argument("--id", nargs="*", help="ids como mostrados por --list (usuario:numero)")
    a = p.parse_args(argv)
    for msg in profiles.ensure_initialized():
        print(msg)
    try:
        return {"list": cmd_list, "set": cmd_set, "apply": cmd_apply, "status": cmd_status,
                "power": cmd_power, "import-windows": cmd_import}[a.cmd](a)
    except profiles.ProfileError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
