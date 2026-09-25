#!/bin/bash
# Removes Alien Thunder. Keeps ~/.config/alien-thunder, where the profiles live.
set -euo pipefail
bin=${XDG_BIN_HOME:-$HOME/.local/bin}
data=${XDG_DATA_HOME:-$HOME/.local/share}
units=${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user

systemctl --user disable --now alien-thunder-overlay.service alien-thunder.service 2>/dev/null || true
rm -f "$units/alien-thunder.service" "$units/alien-thunder-overlay.service" "$bin/alien-thunder" \
      "$data/applications/alien-thunder.desktop"
rm -f "$data"/icons/hicolor/*/apps/alien-thunder.png
systemctl --user daemon-reload

if command -v qdbus6 >/dev/null; then
  qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
    for (const panel of panels())
      for (const w of panel.widgets())
        if (w.type == "alien-thunder") w.remove();' >/dev/null 2>&1 || true
fi
command -v kpackagetool6 >/dev/null && kpackagetool6 --type Plasma/Applet --remove alien-thunder >/dev/null 2>&1 || true

echo "Alien Thunder removed. Your profiles are still in ~/.config/alien-thunder."
