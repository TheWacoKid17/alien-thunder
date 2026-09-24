"""Servico de usuario: mantem o perfil ativo aplicado.

- aplica o perfil ativo ao iniciar (login), com novas tentativas e backoff;
- reaplica apos suspensao/hibernacao (login1 PrepareForSleep(false), barramento do sistema);
- reaplica quando config.json ou o arquivo do perfil ativo mudam (GFileMonitor/inotify);
- reaplica quando o teclado/AW-ELC reaparecem (uevent hidraw via GUdev + checagem a cada 20 s);
- roda efeitos de software (timer GLib, <= 20 fps) e para limpo em SIGTERM;
- expoe io.github.AlienFXStudio no barramento de sessao para GUI/CLI.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time

import dbus
import dbus.mainloop.glib
import dbus.service
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

try:
    gi.require_version("GUdev", "1.0")
    from gi.repository import GUdev  # noqa: E402
except (ValueError, ImportError):  # libgudev ausente: fica so o polling periodico
    GUdev = None

from . import engine as engine_mod  # noqa: E402
from . import hw, paths, profiles  # noqa: E402

BACKOFF = (1, 2, 3, 5, 8, 13, 20, 30)


def log(msg: str):
    print(msg, flush=True)


class Daemon(dbus.service.Object):
    def __init__(self, bus_name, loop: GLib.MainLoop):
        super().__init__(bus_name, paths.DBUS_PATH)
        self.loop = loop
        self.engine = engine_mod.Engine(log=log)
        self.cfg = profiles.load_config()
        self.override: dict | None = None  # {"tipo": "preview"|"perfil", "perfil": dict, "slug": str|None}
        self.retry_id = 0
        self.retry_n = 0
        self.debounce_id = 0
        self.sw_id = 0
        self.last_error = ""
        self.last_ok = 0.0
        self.sleeping = False
        self.devs = self._devs()
        self.monitors = []
        self.udev = None

    # ------------------------------------------------------------ util
    def _devs(self):
        return (hw.find_keyboard(), hw.find_chassis())

    def current(self) -> tuple[dict | None, bool]:
        """(perfil a aplicar, e_o_perfil_ativo)"""
        if self.override:
            return self.override["perfil"], False
        slug = profiles.active_slug()
        if not slug:
            return None, False
        try:
            return profiles.load(slug), True
        except profiles.ProfileError as e:
            self.last_error = str(e)
            log(f"erro: {e}")
            return None, False

    # ------------------------------------------------------------ aplicar
    def apply(self, force: bool = False, reason: str = "") -> bool:
        if self.sleeping:
            return False
        prof, is_active = self.current()
        if prof is None:
            self.stop_sw()
            return False
        if reason:
            log(f"aplicando '{prof['nome']}' ({reason})")
        try:
            self.engine.apply(prof, power=is_active, force=force, backend=self.cfg["chassi_backend"])
        except hw.DeviceError as e:
            self.last_error = str(e)
            log(f"falha: {e}")
            self.schedule_retry()
            self.update_sw()
            return False
        self.last_error = ""
        self.last_ok = time.time()
        self.retry_n = 0
        if self.retry_id:
            GLib.source_remove(self.retry_id)
            self.retry_id = 0
        self.update_sw()
        return True

    def schedule_retry(self):
        if self.retry_id:
            return
        delay = BACKOFF[min(self.retry_n, len(BACKOFF) - 1)]
        self.retry_n += 1
        log(f"nova tentativa em {delay}s")

        def _cb():
            self.retry_id = 0
            self.apply(force=False, reason="nova tentativa")
            return False

        self.retry_id = GLib.timeout_add_seconds(delay, _cb)

    def schedule_apply(self, force: bool, reason: str, delay_ms: int = 300):
        if self.debounce_id:
            GLib.source_remove(self.debounce_id)
        state = {"force": force}

        def _cb():
            self.debounce_id = 0
            self.apply(force=state["force"], reason=reason)
            return False

        self.debounce_id = GLib.timeout_add(delay_ms, _cb)

    # ------------------------------------------------------------ efeitos sw
    def update_sw(self):
        if self.engine.sw is not None and not self.sleeping:
            if not self.sw_id:
                interval = int(1000 / self.cfg["fps"])
                self.sw_id = GLib.timeout_add(interval, self._sw_tick)
        else:
            self.stop_sw()

    def stop_sw(self):
        if self.sw_id:
            GLib.source_remove(self.sw_id)
            self.sw_id = 0

    def _sw_tick(self):
        if self.engine.sw is None or self.sleeping:
            self.sw_id = 0
            return False
        try:
            self.engine.sw_tick()
        except hw.DeviceError as e:
            self.last_error = str(e)
            log(f"efeito de software pausado: {e}")
            self.sw_id = 0
            self.engine.invalidate()
            self.schedule_retry()
            return False
        return True

    # ------------------------------------------------------------ eventos
    def on_prepare_for_sleep(self, going_down):
        if going_down:
            log("suspendendo: pausando")
            self.sleeping = True
            self.stop_sw()
            self.engine.invalidate()
        else:
            log("retomando da suspensão")
            self.sleeping = False
            self.engine.invalidate()
            self.retry_n = 0
            self.schedule_apply(force=True, reason="retorno da suspensão", delay_ms=1500)

    @staticmethod
    def _event_name(gfile, other, event) -> str:
        # escrita atomica (tmp + rename): o nome final vem em "other"
        if event == Gio.FileMonitorEvent.RENAMED and other is not None:
            gfile = other
        return gfile.get_basename() or ""

    def on_config_dir_changed(self, _mon, gfile, other, event):
        if event not in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED,
                         Gio.FileMonitorEvent.MOVED_IN, Gio.FileMonitorEvent.RENAMED,
                         Gio.FileMonitorEvent.DELETED):
            return
        name = self._event_name(gfile, other, event)
        if name.startswith("."):
            return
        if name == "config.json":
            old = self.cfg
            self.cfg = profiles.load_config()
            if old.get("perfil_ativo") != self.cfg.get("perfil_ativo"):
                self.override = None
                self.schedule_apply(False, "perfil ativo alterado")
            elif old.get("fps") != self.cfg.get("fps") or old.get("chassi_backend") != self.cfg.get("chassi_backend"):
                self.stop_sw()
                self.schedule_apply(True, "configuração alterada")

    def on_profiles_changed(self, _mon, gfile, other, event):
        if event not in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED,
                         Gio.FileMonitorEvent.MOVED_IN, Gio.FileMonitorEvent.RENAMED):
            return
        name = self._event_name(gfile, other, event)
        if not name.endswith(".json") or name.startswith("."):
            return
        slug = name[:-5]
        watched = self.override.get("slug") if self.override else profiles.active_slug()
        if slug == watched:
            if self.override and self.override.get("slug"):
                try:
                    self.override["perfil"] = profiles.load(slug)
                except profiles.ProfileError:
                    return
            self.schedule_apply(False, "perfil editado")

    def on_uevent(self, _client, action, _device):
        # udev ja aplicou as ACLs (uaccess) quando o evento chega; da um folego mesmo assim
        if action in ("add", "remove", "bind", "change"):
            GLib.timeout_add(700, self._check_devs)

    def _check_devs(self):
        devs = self._devs()
        if devs != self.devs:
            gained = any(d and d != o for d, o in zip(devs, self.devs))
            self.devs = devs
            self.engine.invalidate()
            if gained:
                self.retry_n = 0
                self.schedule_apply(True, "dispositivo reconectado", delay_ms=800)
        return False

    def _periodic(self):
        # rede de seguranca barata caso algum evento de /dev se perca
        self._check_devs()
        return True

    def setup(self):
        system = dbus.SystemBus()
        system.add_signal_receiver(self.on_prepare_for_sleep, signal_name="PrepareForSleep",
                                   dbus_interface="org.freedesktop.login1.Manager",
                                   bus_name="org.freedesktop.login1", path="/org/freedesktop/login1")
        if GUdev is not None:
            self.udev = GUdev.Client.new(["hidraw"])
            self.udev.connect("uevent", self.on_uevent)
        for path, cb in ((paths.CONFIG_DIR, self.on_config_dir_changed),
                         (paths.PROFILES_DIR, self.on_profiles_changed)):
            mon = Gio.File.new_for_path(path).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            mon.connect("changed", cb)
            self.monitors.append(mon)
        GLib.timeout_add_seconds(20, self._periodic)
        for sig in (signal.SIGTERM, signal.SIGINT):
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, self.quit)
        GLib.idle_add(lambda: (self.apply(force=True, reason="início"), False)[1])

    def quit(self):
        log("encerrando")
        self.stop_sw()
        self.engine.close()
        self.loop.quit()
        return False

    # ------------------------------------------------------------ D-Bus
    @dbus.service.method(paths.DBUS_IFACE, in_signature="", out_signature="b")
    def Reload(self):
        self.cfg = profiles.load_config()
        self.override = None
        self.retry_n = 0
        return self.apply(force=True, reason="recarregar")

    @dbus.service.method(paths.DBUS_IFACE, in_signature="s", out_signature="b")
    def ApplyProfile(self, slug):
        self.cfg = profiles.load_config()
        slug = str(slug)
        if not slug or slug == profiles.active_slug():
            self.override = None
        else:
            self.override = {"tipo": "perfil", "slug": slug, "perfil": profiles.load(slug)}
        return self.apply(force=True, reason="pedido externo")

    @dbus.service.method(paths.DBUS_IFACE, in_signature="s", out_signature="b")
    def Preview(self, profile_json):
        prof = profiles.normalize(json.loads(str(profile_json)))
        self.override = {"tipo": "preview", "slug": None, "perfil": prof}
        return self.apply(force=False)

    @dbus.service.method(paths.DBUS_IFACE, in_signature="", out_signature="b")
    def EndPreview(self):
        if self.override is None:
            return True
        self.override = None
        return self.apply(force=False, reason="fim da prévia")

    @dbus.service.method(paths.DBUS_IFACE, in_signature="s", out_signature="b")
    def WritePower(self, slug):
        prof = profiles.load(str(slug)) if slug else profiles.load(profiles.active_slug())
        try:
            self.engine.write_power_now(prof, self.cfg["chassi_backend"])
        except hw.DeviceError as e:
            self.last_error = str(e)
            return False
        return True

    @dbus.service.method(paths.DBUS_IFACE, in_signature="", out_signature="s")
    def Status(self):
        prof, is_active = self.current()
        return json.dumps({
            "pid": os.getpid(),
            "perfil_ativo": profiles.active_slug(),
            "aplicando": prof["nome"] if prof else None,
            "override": self.override["tipo"] if self.override else None,
            "efeito_software": self.engine.sw.name if self.engine.sw else None,
            "fps": self.cfg["fps"],
            "teclado": self.devs[0],
            "chassi": self.devs[1],
            "ultimo_erro": self.last_error,
            "ultimo_sucesso": self.last_ok,
        }, ensure_ascii=False)


def main():
    for msg in profiles.ensure_initialized():
        log(msg)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    session = dbus.SessionBus()
    try:
        name = dbus.service.BusName(paths.DBUS_NAME, session, do_not_queue=True)
    except dbus.exceptions.NameExistsException:
        log("já existe um daemon do AlienFX Studio rodando")
        return 1
    d = Daemon(name, loop)
    d.bus_name_ref = name
    d.setup()
    log("alienfx-studio daemon iniciado")
    loop.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
