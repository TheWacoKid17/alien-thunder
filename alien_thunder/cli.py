"""Alien Thunder's command line."""
from __future__ import annotations

import argparse
import json
import sys

from . import engine, gmode, hw, profiles
from .i18n import gettext as _


def usage() -> str:
    return _("""alien-thunder                    open the lighting editor
alien-thunder list               list the profiles (* = active)
alien-thunder set <profile>      make a profile the active one and apply it
alien-thunder apply [profile]    apply now (default: the active one) without changing it
alien-thunder status             service and device status
alien-thunder power [profile]    write the power button colors now
alien-thunder gmode [on|off|toggle]
                                 G-Mode, the same as Fn+F1; with no argument, show it
alien-thunder overlay [on|off|lock|unlock|show ITEM|hide ITEM|status]
                                 the floating readouts
alien-thunder import-windows [--list | --id N ...]
                                 import AWCC presets from /mnt/windows
alien-thunder daemon             the service (started by systemd --user)""")


def _apply_direct(slug: str, is_active: bool) -> int:
    prof = profiles.load(slug)
    cfg = profiles.load_config()
    eng = engine.Engine(log=lambda m: print(m))
    try:
        eng.apply(prof, power=is_active, force=True, backend=cfg["chassis_backend"])
    except hw.DeviceError as e:
        print(_("error: %s") % e, file=sys.stderr)
        return 1
    finally:
        eng.close()
    if prof["keyboard_effect"]["mode"] == "software":
        print(_("note: software effects need the service (systemctl --user start alien-thunder)"))
    return 0


def cmd_list(_a) -> int:
    act = profiles.active_slug()
    for slug, name in profiles.list_profiles():
        print(f"{'*' if slug == act else ' '} {slug:24s} {name}")
    return 0


def cmd_set(a) -> int:
    slug = profiles.find(a.profile)
    profiles.set_active(slug)
    print(_("active profile: %s") % slug)
    if engine.daemon_running():
        ok = engine.daemon_call("Reload")
        print(_("applied by the service") if ok else _("the service will try again (see 'status')"))
        return 0 if ok else 1
    return _apply_direct(slug, True)


def cmd_apply(a) -> int:
    act = profiles.active_slug()
    slug = profiles.find(a.profile) if a.profile else act
    if not slug:
        print(_("no active profile"), file=sys.stderr)
        return 1
    if engine.daemon_running():
        ok = engine.daemon_call("ApplyProfile", "" if slug == act else slug)
        print(_("applied: %s") % slug if ok else _("failed; the service will try again (see 'status')"))
        return 0 if ok else 1
    return _apply_direct(slug, slug == act)


def cmd_status(_a) -> int:
    info = engine.env_info()
    missing = _("not found")
    print(_("keyboard (0d62:d2b1): %s") % (info["keyboard"] or missing))
    print(_("chassis  (187c:0551): %s") % (info["chassis"] or missing))
    print(_("active profile: %s") % profiles.active_slug())
    if engine.daemon_running():
        st = json.loads(str(engine.daemon_call("Status")))
        print(_("service: running (pid %s)") % st["pid"])
        for k in ("applying", "override", "software_effect", "gmode", "gmode_key", "last_error"):
            print(f"  {k}: {st.get(k)}")
    else:
        print(_("service: stopped"))
    return 0


def cmd_power(a) -> int:
    slug = profiles.find(a.profile) if a.profile else profiles.active_slug()
    if engine.daemon_running():
        return 0 if engine.daemon_call("WritePower", slug) else 1
    eng = engine.Engine()
    try:
        eng.write_power_now(profiles.load(slug), profiles.load_config()["chassis_backend"])
    except hw.DeviceError as e:
        print(_("error: %s") % e, file=sys.stderr)
        return 1
    return 0


def cmd_gmode(a) -> int:
    if a.action:
        if engine.daemon_running():
            on = bool(engine.daemon_call("ToggleGMode") if a.action == "toggle"
                      else engine.daemon_call("SetGMode", a.action == "on"))
        else:  # without the service the switch still works, but F1 keeps its color
            on = a.action == "on" or (a.action == "toggle" and not gmode.is_on())
            gmode.set_profile(gmode.PERFORMANCE if on else "balanced")
    else:
        on = gmode.is_on()
    state = _("on") if on else _("off")
    print(_("G-Mode: %s (power profile: %s)") % (state, gmode.active_profile()))
    return 0


def cmd_import(a) -> int:
    from . import winimport
    items = winimport.list_presets()
    if a.list or not a.id:
        for it in items:
            print(f"{it['id']:14s} {it['name'][:34]:34s} {it['summary']}")
        return 0
    for it in items:
        if it["id"] in a.id:
            slug = profiles.create(it["name"] + " (Windows)", it["profile"])
            print(_("imported: %s") % slug)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("gui", "--gui"):
        from . import gui
        return gui.main()
    if argv[0] == "daemon":
        from . import daemon
        return daemon.main()
    if argv[0] == "overlay":
        from . import overlay
        return overlay.command(argv[1:])
    p = argparse.ArgumentParser(prog="alien-thunder", usage=usage())
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("set")
    s.add_argument("profile")
    s = sub.add_parser("apply")
    s.add_argument("profile", nargs="?")
    sub.add_parser("status")
    s = sub.add_parser("power")
    s.add_argument("profile", nargs="?")
    s = sub.add_parser("gmode")
    s.add_argument("action", nargs="?", choices=("on", "off", "toggle"))
    s = sub.add_parser("import-windows")
    s.add_argument("--list", action="store_true")
    s.add_argument("--id", nargs="*", help=_("ids as shown by --list (user:number)"))
    a = p.parse_args(argv)
    for msg in profiles.ensure_initialized():
        print(msg)
    try:
        return {"list": cmd_list, "set": cmd_set, "apply": cmd_apply, "status": cmd_status,
                "power": cmd_power, "gmode": cmd_gmode, "import-windows": cmd_import}[a.cmd](a)
    except profiles.ProfileError as e:
        print(_("error: %s") % e, file=sys.stderr)
        return 1
