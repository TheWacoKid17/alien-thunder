"""Caminhos (tudo no home do usuario; nada em /usr/local nem em /mnt/windows)."""
import os

HOME = os.path.expanduser("~")
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
XDG_STATE = os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"

CONFIG_DIR = os.path.join(XDG_CONFIG, "alienfx-studio")
PROFILES_DIR = os.path.join(CONFIG_DIR, "profiles")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
STATE_DIR = os.path.join(XDG_STATE, "alienfx-studio")
STATE_FILE = os.path.join(STATE_DIR, "estado.json")
LOCK_FILE = os.path.join(RUNTIME, "alienfx-studio.lock")

LEGACY_PROFILE = os.path.join(XDG_CONFIG, "alienrgb", "perfil.json")
ALIENRGB_BIN = os.path.join(HOME, ".local", "src", "alienrgb", "target", "release", "alienrgb")

DBUS_NAME = "io.github.AlienFXStudio"
DBUS_PATH = "/io/github/AlienFXStudio"
DBUS_IFACE = "io.github.AlienFXStudio"
