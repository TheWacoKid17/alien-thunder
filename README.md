<p align="center"><img src="assets/icon-256.png" width="160" alt="Alien Thunder"></p>

<h1 align="center">Alien Thunder</h1>

<p align="center"><b>The Alienware Command Center bits you miss on Linux: per-key lighting, the G-Mode key, and live temperatures and fan speeds, on your panel and floating over your games.</b></p>

---

## The problem

On Windows, Alienware laptops come with the Alienware Command Center. On Linux you
get none of it: the keyboard lights stay whatever color they were, the turbo key
(Fn+F1, G-Mode) does nothing, and there's no quick way to see how hot the CPU is or
how fast the fans are spinning.

## What Alien Thunder does

- **Lighting.** Color every key on its own, light the touchpad, the alien head on the lid
  and the power button, and save it all as profiles. Your profile comes back at login,
  after suspend and when the keyboard reconnects.
- **Effects that keep your colors.** Breathing, pulse, wave and twinkle only change how
  bright each light is, never its color. Keyboard, touchpad and alien head each get
  their own effect and speed.
- **G-Mode.** Fn+F1 works again: fans at full speed and the performance power profile,
  and the F1 key turns white while it's on, like on Windows.
- **Readouts on the panel.** CPU and GPU temperature, both fan speeds and memory in use,
  right next to the system tray and the clock.
- **Overlay.** The same readouts in a small bar that floats above every window, games
  in fullscreen included. Drag it anywhere, on any screen; its ✕ puts it away.

## How it looks

### On your panel

<p align="center"><img src="assets/screenshots/panel.png" alt="Alien Thunder on the panel, next to the system tray"></p>

The icon gets a white **G** while G-Mode is on. Temperatures turn yellow at 75 °C and red
at 90 °C. Hover for a summary; click for the rest.

### Click it

<p align="center"><img src="assets/screenshots/popup.png" width="420" alt="Alien Thunder's panel popup"></p>

G-Mode and the overlay are one switch each. **Lighting** opens the lighting editor.

### The overlay

<p align="center"><img src="assets/screenshots/overlay.png" width="640" alt="The readout bar"></p>

Grab the bar anywhere and drop it where you like, on either screen; it remembers the
spot. The ✕ at its end turns the overlay off, and the switch on the panel brings it
back. Untick a reading in the panel popup and the bar gets shorter.

### The lighting editor

<p align="center"><img src="assets/screenshots/editor.png" alt="The lighting editor"></p>

Click keys to select them (Ctrl+click toggles, drag selects an area), pick a color, and
the keyboard changes as you edit.

<p align="center"><img src="assets/screenshots/effects.png" width="360" alt="The Effects tab"></p>

The **Effects** tab has one effect and one speed for the keyboard, one for the touchpad
and one for the alien head; the background service draws them, and they only dim and
brighten the colors you picked. **Import from Windows** reads the
presets you made in the Alienware Command Center, if your Windows partition is
mounted at `/mnt/windows`; it only reads, it never writes there.

## Install

```bash
git clone https://github.com/cryptoconspiracy/alien-thunder.git
cd alien-thunder
./install.sh
```

Nothing needs root. If a package is missing (PySide6, python-dbus, python-gobject,
layer-shell-qt, gettext), the installer says which and asks before installing it. It
puts the widget on your panel right before the system tray, starts the background
service, and adds **Alien Thunder** to the app menu.

### Updating

```bash
git pull && ./install.sh
```

### Removing

```bash
./uninstall.sh
```

Your lighting profiles stay in `~/.config/alien-thunder`.

## Will it work on my computer?

It was built on, and has only been tested on, an **Alienware m16 R2 with the Brazilian
(ABNT2) keyboard**, on Arch-based Linux with **KDE Plasma 6 on Wayland**.

- **Lighting** talks to two USB devices: the keyboard (0d62:d2b1) and the AW-ELC
  chassis controller (187c:0551). Other Alienware laptops with those same controllers
  may work; the key map is the ABNT2 one.
- **G-Mode** relies on the kernel's `alienware-wmi` driver, which turns G-Mode on when
  the power profile goes to *performance*, and on power-profiles-daemon. The key is
  read from `/dev/input`, so your user has to be in the `input` group.
- **Temperatures and fans** come from `alienware_wmi` and `coretemp`. The GPU reading is
  the laptop's embedded controller, not the NVIDIA driver, so checking it every two
  seconds doesn't wake a sleeping GPU.
- **The overlay** needs a Wayland compositor with the layer-shell protocol (KWin has it).
- **The panel widget** needs KDE Plasma 6.

## Language

Alien Thunder is in English and Brazilian Portuguese, and follows your system's
language. If your system is set to Portuguese but that locale isn't generated, KDE
falls back to English, and so does Alien Thunder, so the two always match.

## For the curious: the command line

```text
alien-thunder                    open the lighting editor
alien-thunder list               list the profiles (* = active)
alien-thunder set <profile>      make a profile the active one and apply it
alien-thunder status             service and device status
alien-thunder gmode [on|off|toggle]
alien-thunder overlay [on|off|show ITEM|hide ITEM|status]
```

`ITEM` is one of `cpu_temp`, `gpu_temp`, `cpu_fan`, `gpu_fan`, `ram`.

## What's new

### 1.1

- Now called Alien Thunder (it was AlienFX Studio). Profiles move over by themselves.
- G-Mode on Fn+F1, with the white F1 key.
- Effects for the keyboard, the touchpad and the alien head, each on its own, and none
  of them changes your colors. The effects that did (rainbow, spectrum, the keyboard's
  hardware effects) are gone; saved profiles switch to the closest one that keeps colors.
- Temperatures, fan speeds and memory on the panel, and the floating readout bar.
- English and Brazilian Portuguese.

## Support the project

Alien Thunder is free and stays free. If it saved you from booting into Windows just to
change your keyboard colors, a donation keeps it going.

<p align="center"><img src="assets/donate/btc.png" width="200" alt="Bitcoin donation QR code"></p>

**Bitcoin**: scan the code, or copy the address (the button at the right of the box):

```text
bc1q2nqp9d8lc0u6z7v9ag4u52sv9g9afepgyyrwu4
```

The same code is in the panel widget's settings, under **Support**, with a Copy button.

## Credits

- The lighting protocols come from [alienfx-tools](https://github.com/T-Troll/alienfx-tools)
  by T-Troll (MIT), and were checked byte for byte against alienrgb.
- The key layout comes from the Alienware Command Center's own drawing of the ABNT2 keyboard.
- G-Mode and the fan readings rely on the Linux kernel's `alienware-wmi` driver.
- The overlay uses KDE's [LayerShellQt](https://invent.kde.org/plasma/layer-shell-qt).

Made by Dan B. MIT license.
