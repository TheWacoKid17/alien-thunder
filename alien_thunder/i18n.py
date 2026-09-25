"""Translations. The strings are English; po/pt_BR/alien-thunder.po has the Portuguese."""
import gettext as _gettext
import locale
import os

LOCALEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")

try:
    # Python's gettext reads $LANG on its own, even when that locale isn't generated
    # and KDE has fallen back to English. Asking glibc first keeps us in step with KDE.
    locale.setlocale(locale.LC_MESSAGES, "")
    _t = _gettext.translation("alien-thunder", LOCALEDIR, fallback=True)
except locale.Error:
    _t = _gettext.NullTranslations()

gettext = _t.gettext
ngettext = _t.ngettext


def N_(text: str) -> str:
    """Marks a string for translation where it's defined; _() translates it where it's shown."""
    return text
