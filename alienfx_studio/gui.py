"""Interface grafica (PySide6) do AlienFX Studio."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import time

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPalette,
                           QPen)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox,
                               QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
                               QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
                               QRadioButton, QRubberBand, QScrollArea, QSizePolicy, QSlider,
                               QSpinBox, QTabWidget, QToolButton, QVBoxLayout, QWidget)

from . import effects, engine, hw, layout, profiles, protocol

APP_NAME = "AlienFX Studio"
ACCENT = QColor("#00c8ff")
PALETTE = ["#ff0000", "#ff2900", "#ff8000", "#ffd000", "#80ff00", "#00ff40", "#00ffd0", "#00a0ff",
           "#0020ff", "#8000ff", "#ff00c0", "#ff62e2", "#ffffff", "#ffb070", "#630000", "#000000"]


def qcolor(h: str | None) -> QColor | None:
    return QColor(h) if h else None


def text_color_for(c: QColor) -> QColor:
    lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return QColor("#111111") if lum > 140 else QColor("#f2f2f2")


# ====================================================================== widgets
class ColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, color="#ff0000", title="Escolher cor", parent=None):
        super().__init__(parent)
        self.title = title
        self._color = color
        self.setMinimumSize(QSize(64, 28))
        self.clicked.connect(self._pick)
        self._refresh()

    def color(self) -> str:
        return self._color

    def setColor(self, c: str, emit=False):
        self._color = profiles.norm_hex(c)
        self._refresh()
        if emit:
            self.colorChanged.emit(self._color)

    def _refresh(self):
        c = QColor(self._color)
        self.setStyleSheet(
            f"QPushButton {{ background:{self._color}; color:{text_color_for(c).name()};"
            f" border:1px solid #555; border-radius:4px; padding:3px 8px; }}"
            f"QPushButton:disabled {{ background:#3a3d42; color:#8a8f96; border:1px dashed #666; }}")
        self.setText(self._color.upper())

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self, self.title)
        if c.isValid():
            self.setColor(c.name(), emit=True)


class Swatch(QToolButton):
    def __init__(self, color: str, size=22, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(size, size)
        self.setToolTip(color.upper())
        self.setStyleSheet(f"QToolButton {{ background:{color}; border:1px solid #444; border-radius:3px; }}"
                           f"QToolButton:hover {{ border:2px solid {ACCENT.name()}; }}")


class KeyboardView(QWidget):
    selectionChanged = Signal()
    keyActivated = Signal(int)  # duplo clique
    keyPicked = Signal(int)  # conta-gotas

    MARGIN = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors: dict[int, QColor] = {}
        self.preview: dict[int, QColor] | None = None
        self.selection: set[int] = set()
        self.banner = ""
        self.pick_mode = False
        self._press = None
        self._press_key = None
        self._base_sel: set[int] = set()
        self._dragging = False
        self._band = QRubberBand(QRubberBand.Rectangle, self)
        self.setMouseTracking(True)
        self.setMinimumSize(640, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)

    # --------------------------------------------------------- geometria
    def _xf(self):
        w = self.width() - 2 * self.MARGIN
        h = self.height() - 2 * self.MARGIN
        s = min(w / layout.CANVAS_W, h / layout.CANVAS_H)
        ox = self.MARGIN + (w - layout.CANVAS_W * s) / 2
        oy = self.MARGIN + (h - layout.CANVAS_H * s) / 2
        return s, ox, oy

    def key_rect(self, k: layout.Key) -> QRectF:
        s, ox, oy = self._xf()
        x, y, w, h = k.rect
        pad = 2.5
        return QRectF(ox + (x + pad) * s, oy + (y + pad) * s, (w - 2 * pad) * s, (h - 2 * pad) * s)

    def key_at(self, pos) -> int | None:
        for k in layout.KEYS:
            if self.key_rect(k).contains(QPointF(pos)):
                return k.id
        return None

    def sizeHint(self):
        return QSize(1000, 430)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return int(w * layout.CANVAS_H / layout.CANVAS_W) + 2 * self.MARGIN

    # --------------------------------------------------------- desenho
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s, ox, oy = self._xf()
        deck = QRectF(ox - 8 * s, oy - 8 * s, (layout.CANVAS_W + 16) * s, (layout.KEYS_H + 16) * s)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#15171a"))
        p.drawRoundedRect(deck, 10, 10)
        font = QFont(self.font())
        src = self.preview if self.preview is not None else self.colors
        for k in layout.KEYS:
            r = self.key_rect(k)
            c = src.get(k.id)
            path = QPainterPath()
            rad = 5 * s
            if k.id == 55:  # Enter ISO em "L" invertido
                s_ = s
                x, y, w, h = k.rect
                top_h = 52.7
                cut = 11.0
                path.moveTo(ox + (x + 2.5) * s_, oy + (y + 2.5) * s_)
                path.lineTo(ox + (x + w - 2.5) * s_, oy + (y + 2.5) * s_)
                path.lineTo(ox + (x + w - 2.5) * s_, oy + (y + h - 2.5) * s_)
                path.lineTo(ox + (x + cut + 2.5) * s_, oy + (y + h - 2.5) * s_)
                path.lineTo(ox + (x + cut + 2.5) * s_, oy + (y + top_h - 2.5) * s_)
                path.lineTo(ox + (x + 2.5) * s_, oy + (y + top_h - 2.5) * s_)
                path.closeSubpath()
            else:
                path.addRoundedRect(r, rad, rad)
            if c is None:
                p.setBrush(QColor("#2b2e33"))
                p.setPen(QPen(QColor("#555a60"), 1, Qt.DashLine))
            else:
                p.setBrush(c)
                p.setPen(QPen(QColor(0, 0, 0, 160), 1))
            p.drawPath(path)
            if k.id in self.selection:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(ACCENT, max(2.0, 3.2 * s)))
                p.drawPath(path)
                p.setPen(QPen(QColor("white"), 1))
                p.drawPath(path)
            tc = text_color_for(c) if c is not None else QColor("#9aa0a6")
            p.setPen(tc)
            fs = max(6.0, (11 if len(k.label) <= 3 else 9) * s * 1.35)
            font.setPointSizeF(fs * 0.75)
            font.setBold(k.id in self.selection)
            p.setFont(font)
            p.drawText(r, Qt.AlignCenter, k.label)
        # legenda dos extras
        font.setBold(False)
        font.setPointSizeF(max(7.0, 9 * s * 1.2) * 0.75)
        p.setFont(font)
        p.setPen(QColor("#8a9099"))
        lx = ox + 6 * 68.0 * s + 6 * s
        p.drawText(QRectF(lx, oy + layout.EXTRA_Y * s, 600 * s, layout.EXTRA_H * s),
                   Qt.AlignVCenter | Qt.AlignLeft,
                   "← LEDs do AWCC sem tecla no ABNT2 (teclados JP/UK)")
        if self.banner:
            p.setPen(QColor("#ffd27a"))
            p.drawText(QRectF(lx, oy + layout.EXTRA_Y * s + layout.EXTRA_H * s * 0.0, 590 * s, layout.EXTRA_H * s),
                       Qt.AlignVCenter | Qt.AlignRight, self.banner)
        p.end()

    # --------------------------------------------------------- mouse
    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        self._press = ev.position().toPoint()
        self._press_key = self.key_at(self._press)
        mods = ev.modifiers()
        self._base_sel = set(self.selection) if mods & (Qt.ControlModifier | Qt.ShiftModifier) else set()
        self._dragging = False

    def mouseMoveEvent(self, ev):
        if self._press is None:
            k = self.key_at(ev.position().toPoint())
            self.setCursor(Qt.CrossCursor if self.pick_mode else
                           (Qt.PointingHandCursor if k is not None else Qt.ArrowCursor))
            return
        pos = ev.position().toPoint()
        if not self._dragging and (pos - self._press).manhattanLength() > 6 and not self.pick_mode:
            self._dragging = True
            self._band.show()
        if self._dragging:
            rect = QRect(self._press, pos).normalized()
            self._band.setGeometry(rect)
            hit = {k.id for k in layout.KEYS if self.key_rect(k).intersects(QRectF(rect))}
            self.selection = self._base_sel | hit
            self.update()
            self.selectionChanged.emit()

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton or self._press is None:
            return
        if self._dragging:
            self._band.hide()
        else:
            k = self._press_key
            mods = ev.modifiers()
            if self.pick_mode:
                self.pick_mode = False
                self.setCursor(Qt.ArrowCursor)
                if k is not None:
                    self.keyPicked.emit(k)
            elif k is None:
                if not mods & (Qt.ControlModifier | Qt.ShiftModifier):
                    self.selection = set()
            elif mods & Qt.ControlModifier:
                self.selection ^= {k}
            elif mods & Qt.ShiftModifier:
                self.selection |= {k}
            else:
                self.selection = {k}
            self.update()
            self.selectionChanged.emit()
        self._press = None
        self._dragging = False

    def mouseDoubleClickEvent(self, ev):
        k = self.key_at(ev.position().toPoint())
        if k is not None:
            self.selection = {k}
            self.update()
            self.selectionChanged.emit()
            self.keyActivated.emit(k)

    def event(self, ev):
        if ev.type() == ev.Type.ToolTip:
            k = self.key_at(ev.pos())
            if k is not None:
                key = layout.KEY_BY_ID[k]
                c = self.colors.get(k)
                leds = ", ".join(str(x) for x in key.leds)
                extra = "\nLED sem tecla física no ABNT2" if key.extra else ""
                self.setToolTip(f"{key.name}\nLED(s): {leds}  (AWCC: {key.awcc})\n"
                                f"Cor: {c.name().upper() if c else 'sem cor (não enviado)'}{extra}")
            else:
                self.setToolTip("")
        return super().event(ev)


# ====================================================================== janela
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon.fromTheme("input-keyboard", QIcon.fromTheme("preferences-desktop-color")))
        for m in profiles.ensure_initialized():
            print(m)
        self.cfg = profiles.load_config()
        self.slug: str | None = None
        self.profile: dict = copy.deepcopy(profiles.DEFAULT_PROFILE)
        self.direct_engine: engine.Engine | None = None
        self.preview_sent = False
        self._loading = False
        self._daemon_ok = None

        self.save_timer = QTimer(self, singleShot=True, interval=700, timeout=self.save_now)
        self.live_timer = QTimer(self, singleShot=True, interval=150, timeout=self.push_live)
        self.anim_timer = QTimer(self, interval=66, timeout=self._animate)
        self.anim_fx = None
        self.anim_t0 = 0.0

        self._build()
        self.reload_profile_list(select=profiles.active_slug())
        self.refresh_daemon_status()
        QTimer(self, interval=5000, timeout=self.refresh_daemon_status).start()

    # ------------------------------------------------------------ construcao
    def _build(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 8)

        # barra de perfis
        bar = QHBoxLayout()
        bar.addWidget(QLabel("<b>Perfil:</b>"))
        self.cb_profile = QComboBox()
        self.cb_profile.setMinimumWidth(230)
        self.cb_profile.currentIndexChanged.connect(self.on_profile_selected)
        bar.addWidget(self.cb_profile)
        for text, icon, slot, tip in (
                ("Novo", "document-new", self.new_profile, "Criar perfil novo"),
                ("Renomear", "edit-rename", self.rename_profile, "Renomear perfil"),
                ("Duplicar", "edit-copy", self.duplicate_profile, "Duplicar perfil"),
                ("Excluir", "edit-delete", self.delete_profile, "Excluir perfil"),
                ("Tornar ativo", "starred", self.activate_profile,
                 "Torna este o perfil persistente (aplicado no login, após suspender, etc.)"),
                ("Importar do Windows…", "document-import", self.import_windows,
                 "Importar predefinições do Alienware Command Center")):
            b = QToolButton()
            b.setText(text)
            b.setIcon(QIcon.fromTheme(icon))
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bar.addWidget(b)
            if text == "Tornar ativo":
                self.btn_activate = b
        bar.addStretch(1)
        self.lbl_daemon = QLabel()
        bar.addWidget(self.lbl_daemon)
        root.addLayout(bar)

        self.lbl_hint = QLabel()
        self.lbl_hint.setStyleSheet("color:#d9a441;")
        root.addWidget(self.lbl_hint)

        mid = QHBoxLayout()
        self.kb = KeyboardView()
        self.kb.selectionChanged.connect(self.on_selection_changed)
        self.kb.keyActivated.connect(lambda _k: self.pick_color_dialog())
        self.kb.keyPicked.connect(self.on_key_picked)
        mid.addWidget(self.kb, 1)

        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(360)
        self.tabs.setMaximumWidth(420)
        self.tabs.addTab(self._scroll(self._tab_colors()), "Cores")
        self.tabs.addTab(self._scroll(self._tab_effects()), "Efeitos")
        self.tabs.addTab(self._scroll(self._tab_chassis()), "Chassi")
        self.tabs.addTab(self._scroll(self._tab_options()), "Opções")
        mid.addWidget(self.tabs)
        root.addLayout(mid, 1)

        bottom = QHBoxLayout()
        self.lbl_sel = QLabel("Nenhuma tecla selecionada")
        bottom.addWidget(self.lbl_sel)
        bottom.addStretch(1)
        self.chk_live = QCheckBox("Aplicar ao vivo")
        self.chk_live.setChecked(True)
        self.chk_live.setToolTip("Envia as alterações para os LEDs enquanto você edita")
        bottom.addWidget(self.chk_live)
        self.lbl_saved = QLabel("")
        self.lbl_saved.setStyleSheet("color:#888;")
        bottom.addWidget(self.lbl_saved)
        self.btn_apply = QPushButton(QIcon.fromTheme("dialog-ok-apply"), "Aplicar")
        self.btn_apply.setDefault(True)
        self.btn_apply.setMinimumWidth(120)
        self.btn_apply.clicked.connect(self.apply_now)
        bottom.addWidget(self.btn_apply)
        root.addLayout(bottom)

        self.setCentralWidget(central)
        self.resize(1480, 640)

        act = QAction(self, shortcut="Ctrl+A", triggered=lambda: self.select_group("Todas"))
        self.addAction(act)
        act = QAction(self, shortcut="Escape", triggered=lambda: self.set_selection(set()))
        self.addAction(act)
        act = QAction(self, shortcut="Ctrl+I", triggered=self.invert_selection)
        self.addAction(act)

    def _scroll(self, w):
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QScrollArea.NoFrame)
        sa.setWidget(w)
        return sa

    def _tab_colors(self):
        w = QWidget()
        v = QVBoxLayout(w)

        g = QGroupBox("Cor para a seleção")
        gl = QVBoxLayout(g)
        row = QHBoxLayout()
        self.btn_color = ColorButton("#ff0000", "Cor das teclas selecionadas")
        self.btn_color.colorChanged.connect(lambda c: self.apply_color_to_selection(c))
        row.addWidget(self.btn_color, 1)
        b = QPushButton("Aplicar à seleção")
        b.clicked.connect(lambda: self.apply_color_to_selection(self.btn_color.color()))
        row.addWidget(b)
        gl.addLayout(row)
        row = QHBoxLayout()
        b = QPushButton(QIcon.fromTheme("color-picker"), "Conta-gotas")
        b.setToolTip("Clique numa tecla para copiar a cor dela")
        b.clicked.connect(self.start_pick)
        row.addWidget(b)
        b = QPushButton("Apagar seleção")
        b.setToolTip("Define preto (LED apagado) nas teclas selecionadas")
        b.clicked.connect(lambda: self.apply_color_to_selection("#000000", recent=False))
        row.addWidget(b)
        gl.addLayout(row)

        gl.addWidget(QLabel("Paleta:"))
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, c in enumerate(PALETTE):
            s = Swatch(c)
            s.clicked.connect(lambda _=False, c=c: self.choose_color(c))
            grid.addWidget(s, i // 8, i % 8)
        gl.addLayout(grid)
        gl.addWidget(QLabel("Cores recentes:"))
        self.recent_grid = QGridLayout()
        self.recent_grid.setSpacing(4)
        gl.addLayout(self.recent_grid)
        self._refresh_recent()
        v.addWidget(g)

        g = QGroupBox("Brilho geral (teclado e chassi)")
        gl = QHBoxLayout(g)
        self.sl_bright = QSlider(Qt.Horizontal)
        self.sl_bright.setRange(0, 100)
        self.sl_bright.valueChanged.connect(self.on_brightness)
        self.lbl_bright = QLabel("100%")
        self.lbl_bright.setMinimumWidth(40)
        gl.addWidget(self.sl_bright, 1)
        gl.addWidget(self.lbl_bright)
        v.addWidget(g)

        g = QGroupBox("Padrões de teclas")
        gl = QVBoxLayout(g)
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, name in enumerate(layout.GROUPS):
            b = QPushButton(name)
            b.setToolTip("Clique: selecionar • Ctrl+clique: adicionar à seleção")
            b.clicked.connect(lambda _=False, n=name: self.select_group(n))
            grid.addWidget(b, i // 2, i % 2)
        gl.addLayout(grid)
        row = QHBoxLayout()
        b = QPushButton("Inverter seleção")
        b.clicked.connect(self.invert_selection)
        row.addWidget(b)
        b = QPushButton("Limpar seleção")
        b.clicked.connect(lambda: self.set_selection(set()))
        row.addWidget(b)
        gl.addLayout(row)
        gl.addWidget(QLabel("Meus grupos:"))
        row = QHBoxLayout()
        self.cb_groups = QComboBox()
        row.addWidget(self.cb_groups, 1)
        b = QPushButton("Selecionar")
        b.clicked.connect(self.select_custom_group)
        row.addWidget(b)
        gl.addLayout(row)
        row = QHBoxLayout()
        b = QPushButton("Salvar seleção como grupo…")
        b.clicked.connect(self.save_custom_group)
        row.addWidget(b)
        b = QPushButton("Excluir grupo")
        b.clicked.connect(self.delete_custom_group)
        row.addWidget(b)
        gl.addLayout(row)
        self._refresh_groups()
        v.addWidget(g)
        v.addStretch(1)
        return w

    def _tab_effects(self):
        w = QWidget()
        v = QVBoxLayout(w)
        g = QGroupBox("Efeito do teclado")
        gl = QVBoxLayout(g)
        self.rb_mode = QButtonGroup(self)
        for i, (key, text) in enumerate((("estatico", "Estático (cores por tecla)"),
                                         ("hardware", "Efeito de hardware (sem uso de CPU)"),
                                         ("software", "Efeito de software (roda no serviço)"))):
            rb = QRadioButton(text)
            rb.setProperty("modo", key)
            self.rb_mode.addButton(rb, i)
            gl.addWidget(rb)
        self.rb_mode.idToggled.connect(self.on_effect_mode)
        form = QFormLayout()
        self.cb_effect = QComboBox()
        self.cb_effect.currentIndexChanged.connect(self.on_effect_param)
        form.addRow("Efeito:", self.cb_effect)
        self.btn_ec1 = ColorButton("#ff0000", "Cor 1 do efeito")
        self.btn_ec1.colorChanged.connect(self.on_effect_param)
        form.addRow("Cor 1:", self.btn_ec1)
        self.btn_ec2 = ColorButton("#0000ff", "Cor 2 do efeito")
        self.btn_ec2.colorChanged.connect(self.on_effect_param)
        form.addRow("Cor 2:", self.btn_ec2)
        self.cb_cmode = QComboBox()
        for k, t in protocol.KB_COLOR_MODES.items():
            self.cb_cmode.addItem(t, k)
        self.cb_cmode.currentIndexChanged.connect(self.on_effect_param)
        form.addRow("Cores:", self.cb_cmode)
        self.sl_tempo = QSlider(Qt.Horizontal)
        self.sl_tempo.setRange(0, 255)
        self.sl_tempo.setToolTip("Byte de tempo do controlador (0–255)")
        self.sl_tempo.valueChanged.connect(self.on_effect_param)
        form.addRow("Tempo:", self.sl_tempo)
        self.sl_speed = QSlider(Qt.Horizontal)
        self.sl_speed.setRange(1, 50)
        self.sl_speed.valueChanged.connect(self.on_effect_param)
        form.addRow("Velocidade:", self.sl_speed)
        gl.addLayout(form)
        self.lbl_effect_note = QLabel()
        self.lbl_effect_note.setWordWrap(True)
        self.lbl_effect_note.setStyleSheet("color:#999;")
        gl.addWidget(self.lbl_effect_note)
        v.addWidget(g)
        v.addStretch(1)
        return w

    def _tab_chassis(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.zone_widgets = {}
        for zone, title in (("touchpad", "Touchpad"), ("logo", "Logo (Alienhead na tampa)")):
            g = QGroupBox(title)
            f = QFormLayout(g)
            cb = QComboBox()
            for k, t in protocol.CHASSIS_EFFECTS.items():
                cb.addItem(t, k)
            c1 = ColorButton("#ff2900", f"{title}: cor")
            c2 = ColorButton("#000000", f"{title}: cor 2")
            sl = QSlider(Qt.Horizontal)
            sl.setRange(1, 255)
            sl.setToolTip("Tempo da transição (byte do controlador, 1–255)")
            f.addRow("Efeito:", cb)
            f.addRow("Cor:", c1)
            f.addRow("Cor 2 (morph):", c2)
            f.addRow("Tempo:", sl)
            for wdg, sig in ((cb, cb.currentIndexChanged), (c1, c1.colorChanged), (c2, c2.colorChanged),
                             (sl, sl.valueChanged)):
                sig.connect(lambda *_a, z=zone: self.on_zone_changed(z))
            self.zone_widgets[zone] = (cb, c1, c2, sl)
            v.addWidget(g)
        g = QGroupBox("Botão de energia")
        f = QFormLayout(g)
        self.btn_pw_ac = ColorButton("#ff2900", "Botão de energia na tomada")
        self.btn_pw_bat = ColorButton("#ff2900", "Botão de energia na bateria")
        self.btn_pw_ac.colorChanged.connect(self.on_power_changed)
        self.btn_pw_bat.colorChanged.connect(self.on_power_changed)
        f.addRow("Na tomada (AC):", self.btn_pw_ac)
        f.addRow("Na bateria:", self.btn_pw_bat)
        note = QLabel("O controlador guarda o comportamento do botão (inclusive dormindo e "
                      "carregando). Para evitar gravações repetidas, as cores só são enviadas "
                      "quando mudam e o perfil é o ativo — não ao vivo. Use “Aplicar” ou o botão abaixo.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#999;")
        f.addRow(note)
        b = QPushButton("Gravar cores do botão agora")
        b.clicked.connect(self.write_power_now)
        f.addRow(b)
        v.addWidget(g)
        v.addStretch(1)
        return w

    def _tab_options(self):
        w = QWidget()
        v = QVBoxLayout(w)
        g = QGroupBox("Serviço em segundo plano")
        f = QFormLayout(g)
        self.lbl_service = QLabel()
        self.lbl_service.setWordWrap(True)
        self.lbl_service.setMinimumHeight(self.lbl_service.fontMetrics().lineSpacing() * 3)
        self.lbl_service.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        f.addRow(self.lbl_service)
        row = QHBoxLayout()
        b = QPushButton("Reiniciar serviço")
        b.clicked.connect(lambda: self._systemctl("restart"))
        row.addWidget(b)
        b = QPushButton("Reaplicar perfil ativo")
        b.clicked.connect(self.reapply_active)
        row.addWidget(b)
        f.addRow(row)
        self.sp_fps = QSpinBox()
        self.sp_fps.setRange(1, 20)
        self.sp_fps.setValue(self.cfg["fps"])
        self.sp_fps.setSuffix(" fps")
        self.sp_fps.valueChanged.connect(self.on_options)
        f.addRow("Efeitos de software:", self.sp_fps)
        self.cb_backend = QComboBox()
        self.cb_backend.addItem("hidraw direto (touchpad, logo e efeitos)", "hidraw")
        self.cb_backend.addItem("alienrgb (compatível, só cores fixas)", "alienrgb")
        self.cb_backend.setCurrentIndex(0 if self.cfg["chassi_backend"] == "hidraw" else 1)
        self.cb_backend.currentIndexChanged.connect(self.on_options)
        f.addRow("Chassi via:", self.cb_backend)
        v.addWidget(g)
        g = QGroupBox("Dispositivos")
        f = QVBoxLayout(g)
        self.lbl_devs = QLabel()
        self.lbl_devs.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addWidget(self.lbl_devs)
        help_ = QLabel("Dicas: clique seleciona; Ctrl+clique alterna; Shift+clique adiciona; arraste para "
                       "selecionar uma área; duplo clique abre o seletor de cor; Ctrl+A seleciona tudo; "
                       "Ctrl+I inverte; Esc limpa.\nCLI: alienfx-studio list | set <perfil> | apply [perfil] | status")
        help_.setWordWrap(True)
        help_.setStyleSheet("color:#999;")
        f.addWidget(help_)
        v.addWidget(g)
        v.addStretch(1)
        return w

    # ------------------------------------------------------------ perfis
    def reload_profile_list(self, select: str | None = None):
        self._loading = True
        act = profiles.active_slug()
        self.cb_profile.clear()
        for slug, name in profiles.list_profiles():
            self.cb_profile.addItem(("★ " if slug == act else "") + name, slug)
        self._loading = False
        idx = self.cb_profile.findData(select or self.slug or act)
        self.cb_profile.setCurrentIndex(max(0, idx))
        self.on_profile_selected(self.cb_profile.currentIndex())

    def on_profile_selected(self, idx):
        if self._loading or idx < 0:
            return
        slug = self.cb_profile.itemData(idx)
        if slug == self.slug:
            return
        self.save_now()
        try:
            self.profile = profiles.load(slug)
        except profiles.ProfileError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        self.slug = slug
        self.load_into_widgets()
        self.schedule_live()

    def load_into_widgets(self):
        self._loading = True
        p = self.profile
        self.kb.colors = {int(k): QColor(v) for k, v in p["teclado"].items()}
        for k in layout.KEYS:  # tecla mostra a cor do LED principal
            if k.id not in self.kb.colors:
                for led in k.leds[1:]:
                    if str(led) in p["teclado"]:
                        self.kb.colors[k.id] = QColor(p["teclado"][str(led)])
        self.sl_bright.setValue(p["brilho"])
        self.lbl_bright.setText(f"{p['brilho']}%")
        e = p["efeito_teclado"]
        modes = ["estatico", "hardware", "software"]
        self.rb_mode.button(modes.index(e["modo"])).setChecked(True)
        self._fill_effect_combo(e["modo"], e["efeito"])
        self.btn_ec1.setColor(e["cor1"])
        self.btn_ec2.setColor(e["cor2"])
        self.cb_cmode.setCurrentIndex(self.cb_cmode.findData(e["modo_cor"]))
        self.sl_tempo.setValue(e["tempo"])
        self.sl_speed.setValue(int(round(e["velocidade"] * 10)))
        for zone, (cb, c1, c2, sl) in self.zone_widgets.items():
            z = p["chassi"][zone]
            cb.setCurrentIndex(max(0, cb.findData(z["efeito"])))
            c1.setColor(z["cor"])
            c2.setColor(z["cor2"])
            sl.setValue(max(1, z["tempo"]))
        self.btn_pw_ac.setColor(p["chassi"]["energia"]["ac"])
        self.btn_pw_bat.setColor(p["chassi"]["energia"]["bateria"])
        self._loading = False
        self._update_effect_ui()
        self._update_hint()
        self.kb.update()

    def _update_hint(self):
        act = profiles.active_slug()
        self.btn_activate.setEnabled(self.slug != act)
        if self.slug == act:
            self.lbl_hint.setText("")
            self.lbl_hint.hide()
        else:
            self.lbl_hint.setText("Você está editando um perfil que não é o ativo: ele aparece nos LEDs "
                                  "só enquanto esta janela estiver aberta. Use “Tornar ativo” para mantê-lo.")
            self.lbl_hint.show()

    def _ask_name(self, title, default=""):
        name, ok = QInputDialog.getText(self, title, "Nome do perfil:", text=default)
        name = name.strip()
        return name if ok and name else None

    def new_profile(self):
        name = self._ask_name("Novo perfil")
        if name:
            self.save_now()
            slug = profiles.create(name)
            self.reload_profile_list(select=slug)

    def rename_profile(self):
        if not self.slug:
            return
        name = self._ask_name("Renomear perfil", self.profile["nome"])
        if name:
            self.save_now()
            self.slug = profiles.rename(self.slug, name)
            self.profile["nome"] = name
            self.reload_profile_list(select=self.slug)

    def duplicate_profile(self):
        if not self.slug:
            return
        name = self._ask_name("Duplicar perfil", self.profile["nome"] + " (cópia)")
        if name:
            self.save_now()
            slug = profiles.duplicate(self.slug, name)
            self.reload_profile_list(select=slug)

    def delete_profile(self):
        if not self.slug:
            return
        if self.slug == profiles.active_slug():
            QMessageBox.information(self, APP_NAME, "Este é o perfil ativo. Ative outro perfil antes de excluí-lo.")
            return
        if QMessageBox.question(self, APP_NAME, f"Excluir o perfil “{self.profile['nome']}”?") != QMessageBox.Yes:
            return
        self.save_timer.stop()
        profiles.delete(self.slug)
        self.slug = None
        self.reload_profile_list(select=profiles.active_slug())

    def activate_profile(self):
        if not self.slug:
            return
        self.save_now()
        profiles.set_active(self.slug)
        self.preview_sent = False
        ok = self._daemon("Reload")
        if ok is None:
            self._direct_apply(power=True)
        self.reload_profile_list(select=self.slug)
        self.statusBar().showMessage(f"“{self.profile['nome']}” agora é o perfil ativo", 5000)

    def import_windows(self):
        from . import winimport
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            items = winimport.list_presets()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, f"Não foi possível ler as predefinições do AWCC:\n{e}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        dlg = QDialog(self)
        dlg.setWindowTitle("Importar do Windows (Alienware Command Center)")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Marque as predefinições para importar como perfis novos "
                             "(a partição do Windows é só lida):"))
        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.NoSelection)
        for it in items:
            li = QListWidgetItem(f"{it['nome']}  —  {it['resumo']}")
            li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
            li.setCheckState(Qt.Unchecked)
            li.setData(Qt.UserRole, it["id"])
            lst.addItem(li)
        lay.addWidget(lst)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Importar")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.resize(620, 480)
        if dlg.exec() != QDialog.Accepted:
            return
        chosen = {lst.item(i).data(Qt.UserRole) for i in range(lst.count())
                  if lst.item(i).checkState() == Qt.Checked}
        last = None
        for it in items:
            if it["id"] in chosen:
                last = profiles.create(it["nome"] + " (Windows)", it["perfil"])
        if last:
            self.save_now()
            self.reload_profile_list(select=last)
            self.statusBar().showMessage(f"{len(chosen)} perfil(is) importado(s)", 5000)

    # ------------------------------------------------------------ selecao / cores
    def set_selection(self, sel: set[int]):
        self.kb.selection = set(sel)
        self.kb.update()
        self.on_selection_changed()

    def on_selection_changed(self):
        n = len(self.kb.selection)
        if n == 0:
            self.lbl_sel.setText("Nenhuma tecla selecionada — clique, Ctrl/Shift+clique ou arraste para selecionar")
        elif n == 1:
            k = layout.KEY_BY_ID[next(iter(self.kb.selection))]
            self.lbl_sel.setText(f"Selecionada: {k.name} (LED {', '.join(map(str, k.leds))})")
        else:
            self.lbl_sel.setText(f"{n} teclas selecionadas")

    def select_group(self, name: str):
        ids = set(layout.GROUPS[name])
        if QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            ids |= self.kb.selection
        self.set_selection(ids)

    def invert_selection(self):
        self.set_selection({k.id for k in layout.KEYS} - self.kb.selection)

    def choose_color(self, c: str):
        self.btn_color.setColor(c)
        self.apply_color_to_selection(c)

    def apply_color_to_selection(self, c: str, recent=True):
        if not self.kb.selection:
            self.statusBar().showMessage("Selecione teclas primeiro", 3000)
            return
        c = profiles.norm_hex(c)
        for kid in self.kb.selection:
            for led in layout.KEY_BY_ID[kid].leds:
                self.profile["teclado"][str(led)] = c
            self.kb.colors[kid] = QColor(c)
        if recent:
            self._push_recent(c)
        if self.profile["efeito_teclado"]["modo"] == "hardware":
            self.statusBar().showMessage("Aviso: um efeito de hardware está ativo; as cores por tecla "
                                         "valem no modo Estático ou nos efeitos de software", 6000)
        self.kb.update()
        self.changed()

    def pick_color_dialog(self):
        cur = None
        if len(self.kb.selection) == 1:
            cur = self.kb.colors.get(next(iter(self.kb.selection)))
        c = QColorDialog.getColor(cur or QColor(self.btn_color.color()), self, "Cor da tecla")
        if c.isValid():
            self.btn_color.setColor(c.name())
            self.apply_color_to_selection(c.name())

    def start_pick(self):
        self.kb.pick_mode = True
        self.kb.setCursor(Qt.CrossCursor)
        self.statusBar().showMessage("Conta-gotas: clique numa tecla", 4000)

    def on_key_picked(self, kid):
        c = self.kb.colors.get(kid)
        if c is not None:
            self.btn_color.setColor(c.name())
            self.statusBar().showMessage(f"Cor {c.name().upper()} copiada de {layout.KEY_BY_ID[kid].name}", 4000)

    def _push_recent(self, c):
        rec = [x for x in self.cfg.get("cores_recentes", []) if x != c]
        self.cfg["cores_recentes"] = ([c] + rec)[:16]
        self._save_cfg_keys("cores_recentes")
        self._refresh_recent()

    def _refresh_recent(self):
        while self.recent_grid.count():
            it = self.recent_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        rec = self.cfg.get("cores_recentes", [])
        if not rec:
            lbl = QLabel("(nenhuma ainda)")
            lbl.setStyleSheet("color:#888;")
            self.recent_grid.addWidget(lbl, 0, 0, 1, 8)
        for i, c in enumerate(rec):
            s = Swatch(c)
            s.clicked.connect(lambda _=False, c=c: self.choose_color(c))
            self.recent_grid.addWidget(s, i // 8, i % 8)

    def _save_cfg_keys(self, *keys):
        cfg = profiles.load_config()  # relê para nao sobrescrever o perfil ativo mudado por fora
        for k in keys:
            cfg[k] = self.cfg[k]
        profiles.save_config(cfg)
        self.cfg = cfg

    def _refresh_groups(self):
        self.cb_groups.clear()
        for name in sorted(self.cfg.get("grupos", {})):
            self.cb_groups.addItem(name)

    def select_custom_group(self):
        name = self.cb_groups.currentText()
        ids = set(self.cfg.get("grupos", {}).get(name, [])) & set(layout.KEY_BY_ID)
        if ids:
            self.set_selection(ids)

    def save_custom_group(self):
        if not self.kb.selection:
            self.statusBar().showMessage("Selecione teclas primeiro", 3000)
            return
        name, ok = QInputDialog.getText(self, "Salvar grupo", "Nome do grupo:")
        if ok and name.strip():
            self.cfg.setdefault("grupos", {})[name.strip()] = sorted(self.kb.selection)
            self._save_cfg_keys("grupos")
            self._refresh_groups()
            self.cb_groups.setCurrentText(name.strip())

    def delete_custom_group(self):
        name = self.cb_groups.currentText()
        if name and name in self.cfg.get("grupos", {}):
            del self.cfg["grupos"][name]
            self._save_cfg_keys("grupos")
            self._refresh_groups()

    def on_brightness(self, v):
        self.lbl_bright.setText(f"{v}%")
        if self._loading:
            return
        self.profile["brilho"] = v
        self.changed()

    # ------------------------------------------------------------ efeitos
    def _fill_effect_combo(self, mode, current=None):
        self.cb_effect.blockSignals(True)
        self.cb_effect.clear()
        if mode == "hardware":
            for k, (_t, name) in protocol.KB_HW_EFFECTS.items():
                self.cb_effect.addItem(name, k)
        elif mode == "software":
            for k, name in effects.SW_EFFECTS.items():
                self.cb_effect.addItem(name, k)
        idx = self.cb_effect.findData(current)
        self.cb_effect.setCurrentIndex(max(0, idx))
        self.cb_effect.blockSignals(False)

    def on_effect_mode(self, bid, checked):
        if not checked:
            return
        mode = self.rb_mode.button(bid).property("modo")
        if not self._loading:
            self._fill_effect_combo(mode, self.profile["efeito_teclado"].get("efeito"))
            self.profile["efeito_teclado"]["modo"] = mode
            if self.cb_effect.count():
                self.profile["efeito_teclado"]["efeito"] = self.cb_effect.currentData()
            self.changed()
        self._update_effect_ui()

    def on_effect_param(self, *_a):
        if self._loading:
            return
        e = self.profile["efeito_teclado"]
        if self.cb_effect.count():
            e["efeito"] = self.cb_effect.currentData()
        e["cor1"] = self.btn_ec1.color()
        e["cor2"] = self.btn_ec2.color()
        e["modo_cor"] = self.cb_cmode.currentData()
        e["tempo"] = self.sl_tempo.value()
        e["velocidade"] = self.sl_speed.value() / 10.0
        self._update_effect_ui()
        self.changed()

    def _update_effect_ui(self):
        e = self.profile["efeito_teclado"]
        mode = e["modo"]
        hwm, swm = mode == "hardware", mode == "software"
        self.cb_effect.setEnabled(hwm or swm)
        self.btn_ec1.setEnabled(hwm or (swm and e["efeito"] in ("onda_cor", "cintilar")))
        self.btn_ec2.setEnabled(hwm and e["modo_cor"] == 2)
        self.cb_cmode.setEnabled(hwm)
        self.sl_tempo.setEnabled(hwm)
        self.sl_speed.setEnabled(swm)
        if hwm:
            note = ("Efeito executado pelo próprio controlador do teclado (zero CPU). "
                    "Traduzido do alienfx-tools — precisa de confirmação visual. "
                    "As cores por tecla ficam guardadas e voltam no modo Estático.")
            self.kb.banner = f"Efeito de hardware: {self.cb_effect.currentText()} (prévia = cores por tecla)"
        elif swm:
            note = (f"Renderizado pelo serviço em segundo plano a {self.cfg['fps']} fps "
                    "(baixo uso de CPU). A prévia ao lado é animada.")
            self.kb.banner = ""
        else:
            note = "Cada tecla usa a cor definida na aba Cores."
            self.kb.banner = ""
        self.lbl_effect_note.setText(note)
        self._restart_anim()
        self.kb.update()

    def _restart_anim(self):
        e = self.profile["efeito_teclado"]
        if e["modo"] == "software":
            try:
                self.anim_fx = engine.make_sw_effect(profiles.normalize(self.profile))
            except (ValueError, profiles.ProfileError):
                self.anim_fx = None
            if self.anim_fx:
                self.anim_t0 = time.monotonic()
                self.anim_timer.setInterval(int(1000 / self.cfg["fps"]))
                self.anim_timer.start()
                return
        self.anim_timer.stop()
        self.anim_fx = None
        self.kb.preview = None

    def _animate(self):
        if not self.anim_fx or not self.isVisible():
            return
        fr = self.anim_fx.frame(time.monotonic() - self.anim_t0)
        f = max(0.15, self.profile["brilho"] / 100.0)  # prévia legível mesmo com brilho baixo
        prev = {}
        for k in layout.KEYS:
            c = fr.get(k.id)
            if c is not None:
                prev[k.id] = QColor(*(min(255, int(x / f)) for x in c))
        self.kb.preview = prev
        self.kb.update()

    # ------------------------------------------------------------ chassi
    def on_zone_changed(self, zone):
        if self._loading:
            return
        cb, c1, c2, sl = self.zone_widgets[zone]
        z = self.profile["chassi"][zone]
        z.update(efeito=cb.currentData(), cor=c1.color(), cor2=c2.color(), tempo=sl.value())
        self.changed()

    def on_power_changed(self, *_a):
        if self._loading:
            return
        self.profile["chassi"]["energia"] = {"ac": self.btn_pw_ac.color(), "bateria": self.btn_pw_bat.color()}
        self.changed(live=False)
        self.statusBar().showMessage("Cores do botão de energia serão gravadas ao clicar em Aplicar "
                                     "(perfil ativo) ou em “Gravar cores do botão agora”", 6000)

    def write_power_now(self):
        self.save_now()
        ok = self._daemon("WritePower", self.slug or "")
        if ok is None:
            try:
                self._engine().write_power_now(self.profile, self.cfg["chassi_backend"])
                ok = True
            except hw.DeviceError as e:
                QMessageBox.warning(self, APP_NAME, str(e))
                return
        self.statusBar().showMessage("Botão de energia gravado" if ok else "Falha ao gravar o botão de energia", 5000)

    # ------------------------------------------------------------ opcoes/servico
    def on_options(self, *_a):
        self.cfg["fps"] = self.sp_fps.value()
        self.cfg["chassi_backend"] = self.cb_backend.currentData()
        self._save_cfg_keys("fps", "chassi_backend")
        self._update_effect_ui()

    def _systemctl(self, verb):
        r = subprocess.run(["systemctl", "--user", verb, "alienfx-studio.service"], capture_output=True, text=True)
        if r.returncode:
            QMessageBox.warning(self, APP_NAME, r.stderr or f"systemctl {verb} falhou")
        QTimer.singleShot(1500, self.refresh_daemon_status)
        self.preview_sent = False
        QTimer.singleShot(1800, self.schedule_live)

    def reapply_active(self):
        ok = self._daemon("Reload")
        if ok is None:
            slug = profiles.active_slug()
            if slug:
                self._direct_apply(profiles.load(slug), power=True, force=True)
        self.preview_sent = False
        self.statusBar().showMessage("Perfil ativo reaplicado", 3000)

    def refresh_daemon_status(self):
        info = engine.env_info()
        running = engine.daemon_running()
        self._daemon_ok = running
        st = {}
        if running:
            try:
                st = json.loads(str(engine.daemon_call("Status", timeout=3)))
            except Exception:  # noqa: BLE001
                st = {}
        if running:
            err = st.get("ultimo_erro")
            self.lbl_daemon.setText("● serviço ativo" if not err else "● serviço: tentando novamente")
            self.lbl_daemon.setStyleSheet("color:#3fb950;" if not err else "color:#d29922;")
            self.lbl_daemon.setToolTip(err or "O serviço mantém o perfil ativo aplicado")
            txt = (f"Rodando (pid {st.get('pid')}). Aplicando: {st.get('aplicando')}"
                   + (f" [{st.get('override')}]" if st.get("override") else "")
                   + (f"\nEfeito de software: {st.get('efeito_software')}" if st.get("efeito_software") else "")
                   + (f"\nÚltimo erro: {err}" if err else ""))
        else:
            self.lbl_daemon.setText("● serviço parado")
            self.lbl_daemon.setStyleSheet("color:#f85149;")
            self.lbl_daemon.setToolTip("Sem o serviço, a GUI aplica diretamente; efeitos de software não rodam")
            txt = "Parado. Inicie com: systemctl --user enable --now alienfx-studio"
        self.lbl_service.setText(txt)
        self.lbl_devs.setText(f"Teclado 0d62:d2b1: {info['teclado'] or 'não encontrado'}\n"
                              f"AW-ELC 187c:0551: {info['chassi'] or 'não encontrado'}\n"
                              f"alienrgb: {'disponível' if info['alienrgb'] else 'ausente'}")

    # ------------------------------------------------------------ aplicar/salvar
    def changed(self, live=True):
        if self._loading or not self.slug:
            return
        self.lbl_saved.setText("modificado…")
        self.save_timer.start()
        if live:
            self.schedule_live()

    def schedule_live(self):
        if self.chk_live.isChecked():
            self.live_timer.start()

    def save_now(self):
        self.save_timer.stop()
        if self.slug and not self._loading:
            try:
                profiles.save(self.slug, self.profile)
                self.lbl_saved.setText("salvo")
            except (OSError, profiles.ProfileError) as e:
                self.lbl_saved.setText("erro ao salvar")
                self.statusBar().showMessage(str(e), 8000)

    def _daemon(self, method, *args):
        """Chama o serviço. Retorna None se ele não estiver disponível."""
        if not engine.daemon_running():
            return None
        try:
            return bool(engine.daemon_call(method, *args, timeout=25))
        except Exception as e:  # noqa: BLE001
            self.statusBar().showMessage(f"Serviço: {e}", 6000)
            return None

    def _engine(self):
        if self.direct_engine is None:
            self.direct_engine = engine.Engine(log=lambda m: None)
        return self.direct_engine

    def _direct_apply(self, prof=None, power=False, force=False):
        try:
            self._engine().apply(prof or self.profile, power=power, force=force,
                                 backend=self.cfg["chassi_backend"])
            return True
        except hw.DeviceError as e:
            self.statusBar().showMessage(f"Erro: {e}", 8000)
            return False

    def push_live(self):
        if not self.slug:
            return
        payload = json.dumps(self.profile, ensure_ascii=False)
        ok = self._daemon("Preview", payload)
        if ok is None:
            ok = self._direct_apply(power=False)
        else:
            self.preview_sent = True
        if ok is False:
            self.statusBar().showMessage("Falha ao aplicar (veja a aba Opções)", 5000)

    def apply_now(self):
        self.save_now()
        is_active = self.slug == profiles.active_slug()
        ok = self._daemon("Reload" if is_active else "ApplyProfile", *([] if is_active else [self.slug]))
        if ok is None:
            ok = self._direct_apply(power=is_active, force=True)
        else:
            self.preview_sent = not is_active
        msg = "Aplicado" if ok else "Falha ao aplicar (o serviço tentará de novo)"
        if ok and not is_active:
            msg += " — perfil não ativo: volta ao ativo ao fechar"
        self.statusBar().showMessage(msg, 5000)

    def closeEvent(self, ev):
        self.save_now()
        self.anim_timer.stop()
        if engine.daemon_running():
            try:
                engine.daemon_call("EndPreview", timeout=10)
            except Exception:  # noqa: BLE001
                pass
        elif self.slug != profiles.active_slug():
            slug = profiles.active_slug()
            if slug:
                self._direct_apply(profiles.load(slug), force=True)
        if self.direct_engine:
            self.direct_engine.close()
        super().closeEvent(ev)


def main(argv=None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName("alienfx-studio")
    app.setWindowIcon(QIcon.fromTheme("input-keyboard"))
    w = MainWindow()
    w.show()
    return app.exec()
