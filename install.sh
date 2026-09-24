#!/bin/sh
# Instalacao em espaco de usuario (sem sudo) do AlienFX Studio.
#   ./install.sh            instala/atualiza, habilita e (re)inicia o servico
#   ./install.sh --no-test  pula os testes
set -eu
SRC=$(dirname "$(readlink -f "$0")")
APP="$HOME/.local/share/alienfx-studio"
BIN="$HOME/.local/bin/alienfx-studio"
UNIT_DIR="$HOME/.config/systemd/user"
DESKTOP="$HOME/.local/share/applications/alienfx-studio.desktop"

echo ">> verificando dependências (pacman: pyside6 python-dbus python-gobject libgudev)"
/usr/bin/python3 -c "import PySide6.QtWidgets, dbus, gi" || {
    echo "faltam módulos Python do sistema; instale com: sudo pacman -S pyside6 python-dbus python-gobject" >&2
    exit 1
}

if [ "${1:-}" != "--no-test" ]; then
    echo ">> testes"
    (cd "$SRC" && /usr/bin/python3 -m unittest discover -s tests -q)
fi

echo ">> copiando código para $APP"
mkdir -p "$APP"
rm -rf "$APP/alienfx_studio.new"
cp -r "$SRC/alienfx_studio" "$APP/alienfx_studio.new"
find "$APP/alienfx_studio.new" -name __pycache__ -type d -prune -exec rm -rf {} +
rm -rf "$APP/alienfx_studio"
mv "$APP/alienfx_studio.new" "$APP/alienfx_studio"

echo ">> lançador $BIN"
install -Dm755 "$SRC/bin/alienfx-studio" "$BIN"

echo ">> atalho $DESKTOP"
mkdir -p "$(dirname "$DESKTOP")"
sed "s|@BIN@|$BIN|" "$SRC/data/alienfx-studio.desktop.in" > "$DESKTOP"
command -v update-desktop-database >/dev/null && update-desktop-database -q "$(dirname "$DESKTOP")" || true

echo ">> perfis (importa ~/.config/alienrgb/perfil.json na primeira vez)"
"$BIN" list

echo ">> serviço de usuário"
install -Dm644 "$SRC/data/alienfx-studio.service" "$UNIT_DIR/alienfx-studio.service"
if systemctl --user is-enabled -q alienfx-perfil.service 2>/dev/null; then
    echo "   desativando o antigo alienfx-perfil.service (substituído)"
    systemctl --user disable alienfx-perfil.service
fi
systemctl --user daemon-reload
systemctl --user enable alienfx-studio.service
systemctl --user restart alienfx-studio.service
sleep 2
systemctl --user --no-pager --lines=0 status alienfx-studio.service | head -n 3
echo ">> pronto. Abra \"AlienFX Studio\" no menu ou rode: alienfx-studio"
