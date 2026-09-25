"""Floating readouts (CPU/GPU temperature, fan speed, memory) that stay above every window.

Each readout is its own wlr-layer-shell surface on the overlay layer, so it stays above
fullscreen games too, and its position is a margin from the top-left corner of the
screen it's on. Plain Wayland windows can't choose their own position; layer surfaces
can, which is what lets the positions survive a restart.

The daemon writes the sensor values; this process only draws them. Positions, which
readouts are shown and the lock live in ~/.config/alien-thunder/overlay.json, and the
panel widget changes them through `alien-thunder overlay ...`.
"""
from __future__ import annotations

import json
import os
import sys

from . import i18n, paths, profiles, sensors

_ = i18n.gettext

OVERLAY_FILE = os.path.join(paths.CONFIG_DIR, "overlay.json")
ITEMS = ("cpu_temp", "gpu_temp", "cpu_fan", "gpu_fan", "ram")


def default_config() -> dict:
    return {"locked": False,
            "items": {k: {"shown": True, "screen": "", "x": 24, "y": 80 + 64 * i} for i, k in enumerate(ITEMS)}}


def load_config() -> dict:
    cfg = default_config()
    try:
        with open(OVERLAY_FILE, encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return cfg
    cfg["locked"] = bool(saved.get("locked", False))
    for k in ITEMS:
        cfg["items"][k].update((saved.get("items") or {}).get(k) or {})
    return cfg


def save_config(cfg: dict) -> None:
    profiles._atomic_write(OVERLAY_FILE, cfg)


def labels() -> dict:
    return {"cpu_temp": _("CPU"), "gpu_temp": _("GPU"), "cpu_fan": _("CPU fan"),
            "gpu_fan": _("GPU fan"), "ram": _("RAM")}


def main() -> int:
    # Tiny tiles don't need the GPU, and staying off it keeps them out of a game's way.
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    from PySide6.QtCore import (Property, QFileSystemWatcher, QObject, QTimer, QUrl, Signal, Slot,
                                qInstallMessageHandler)
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine

    class Backend(QObject):
        valuesChanged = Signal()
        configChanged = Signal()

        def __init__(self):
            super().__init__()
            self._values = {}
            self._cfg = load_config()
            os.makedirs(paths.CONFIG_DIR, exist_ok=True)
            self.watcher = QFileSystemWatcher([paths.CONFIG_DIR], self)
            self.watcher.directoryChanged.connect(self._reload)
            self.timer = QTimer(self, interval=1000, timeout=self._poll)
            self.timer.start()
            self._poll()

        def _poll(self):
            try:
                with open(sensors.SENSORS_FILE, encoding="utf-8") as f:
                    values = json.load(f)
            except (OSError, ValueError):
                values = {}
            if values != self._values:
                self._values = values
                self.valuesChanged.emit()

        def _reload(self, *_a):
            # Our own saves land here too; they match what we hold, so nothing redraws.
            cfg = load_config()
            if cfg != self._cfg:
                self._cfg = cfg
                self.configChanged.emit()

        @Property("QVariantMap", notify=valuesChanged)
        def values(self):
            return self._values

        @Property("QVariantMap", notify=configChanged)
        def config(self):
            return self._cfg

        @Property("QVariantMap", constant=True)
        def labels(self):
            return labels()

        @Property("QStringList", constant=True)
        def items(self):
            return list(ITEMS)

        # Qt.application.screens hands QML descriptions of the screens, not QScreen objects,
        # so QML can't move a window to another screen by itself.
        @Slot(QObject, str)
        def putOnScreen(self, window, name):
            for scr in QGuiApplication.screens():
                if scr.name() == name:
                    window.setScreen(scr)
                    return

        @Slot(str, str, int, int)
        def place(self, item, screen, x, y):
            self._cfg["items"][item].update(screen=screen, x=x, y=y)
            save_config(self._cfg)

    # QML errors would otherwise go straight to the journal under a name nobody searches for.
    qInstallMessageHandler(lambda _type, _ctx, msg: print(msg, file=sys.stderr, flush=True))
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Alien Thunder")
    app.setDesktopFileName("alien-thunder")
    app.setQuitOnLastWindowClosed(False)
    icon = os.path.join(os.path.dirname(__file__), "icons", "alien-thunder.png")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"backend": backend})
    engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "overlay.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


def command(args: list[str]) -> int:
    """alien-thunder overlay [run|on|off|lock|unlock|show ITEM|hide ITEM|status]"""
    import subprocess
    unit = "alien-thunder-overlay.service"
    action = args[0] if args else "status"
    if action == "run":
        return main()
    if action in ("on", "off"):
        verb = "enable" if action == "on" else "disable"
        return subprocess.run(["systemctl", "--user", verb, "--now", unit]).returncode
    cfg = load_config()
    if action in ("lock", "unlock"):
        cfg["locked"] = action == "lock"
    elif action in ("show", "hide") and len(args) == 2 and args[1] in ITEMS:
        cfg["items"][args[1]]["shown"] = action == "show"
    elif action == "status":
        running = subprocess.run(["systemctl", "--user", "is-active", "-q", unit]).returncode == 0
        print(json.dumps({"running": running, **cfg}))
        return 0
    else:
        print(_("usage: alien-thunder overlay [run|on|off|lock|unlock|show ITEM|hide ITEM|status]"), file=sys.stderr)
        print(_("items: %s") % " ".join(ITEMS), file=sys.stderr)
        return 2
    save_config(cfg)
    return 0
