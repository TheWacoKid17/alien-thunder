#!/bin/sh
# Remove o AlienFX Studio (mantém ~/.config/alienfx-studio com os perfis).
set -eu
systemctl --user disable --now alienfx-studio.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/alienfx-studio.service" "$HOME/.local/bin/alienfx-studio" \
      "$HOME/.local/share/applications/alienfx-studio.desktop"
rm -rf "$HOME/.local/share/alienfx-studio"
systemctl --user daemon-reload
echo "removido. Para voltar ao método antigo: systemctl --user enable alienfx-perfil.service"
