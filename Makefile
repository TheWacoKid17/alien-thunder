# System-wide install, for distribution packages:  make && make DESTDIR=... install
# For a per-user install from this checkout, use ./install.sh instead.

PREFIX ?= /usr
DESTDIR ?=
LIBDIR = $(DESTDIR)$(PREFIX)/lib/alien-thunder
SHARE = $(DESTDIR)$(PREFIX)/share
WIDGET = plasma/alien-thunder

LANGS = $(notdir $(wildcard po/*/))

all: locales

locales:
	for lang in $(LANGS); do \
	  mkdir -p alien_thunder/locale/$$lang/LC_MESSAGES $(WIDGET)/contents/locale/$$lang/LC_MESSAGES; \
	  msgfmt -o alien_thunder/locale/$$lang/LC_MESSAGES/alien-thunder.mo po/$$lang/alien-thunder.po; \
	  msgfmt -o $(WIDGET)/contents/locale/$$lang/LC_MESSAGES/plasma_applet_alien-thunder.mo po/$$lang/plasma_applet_alien-thunder.po; \
	done

check:
	/usr/bin/python3 -m unittest discover -s tests -q

install: locales
	install -d $(LIBDIR)
	cp -r alien_thunder $(LIBDIR)/
	find $(LIBDIR) -name __pycache__ -type d -prune -exec rm -rf {} +
	install -Dm755 bin/alien-thunder $(DESTDIR)$(PREFIX)/bin/alien-thunder
	for unit in alien-thunder alien-thunder-overlay; do \
	  sed 's|%h/.local/bin/alien-thunder|$(PREFIX)/bin/alien-thunder|' data/$$unit.service \
	    | install -Dm644 /dev/stdin $(DESTDIR)$(PREFIX)/lib/systemd/user/$$unit.service; \
	done
	install -Dm644 data/70-alien-thunder.rules $(DESTDIR)$(PREFIX)/lib/udev/rules.d/70-alien-thunder.rules
	install -Dm644 data/alien-thunder.desktop $(SHARE)/applications/alien-thunder.desktop
	for size in 16 22 24 32 48 64 128 256; do \
	  install -Dm644 assets/icon-$$size.png $(SHARE)/icons/hicolor/$${size}x$${size}/apps/alien-thunder.png; \
	done
	install -d $(SHARE)/plasma/plasmoids
	cp -r $(WIDGET) $(SHARE)/plasma/plasmoids/
	install -Dm644 LICENSE $(SHARE)/licenses/alien-thunder/LICENSE

.PHONY: all locales check install
