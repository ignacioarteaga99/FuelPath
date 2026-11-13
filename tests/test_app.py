"""La app (web/index.html): todos los textos que pasan por t() tienen su traducción en EN y PT."""
import re
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")


def _dicc(nombre):
    bloque = re.search(rf"const {nombre} = \{{(.*?)\n\}};", HTML, re.S).group(1)
    return set(re.findall(r'"((?:[^"\\]|\\.)*)"\s*:', bloque))


def _claves():
    usadas = set(re.findall(r'\b[tN]\("((?:[^"\\]|\\.)*)"', HTML))
    usadas |= {x.strip() for x in re.findall(r"data-i18n>([^<]+)<", HTML)}
    return usadas


def test_textos_traducidos():
    en, pt = _dicc("EN"), _dicc("PT")
    faltan_en = sorted(_claves() - en)
    faltan_pt = sorted(_claves() - pt)
    assert not faltan_en, f"Faltan en EN: {faltan_en}"
    assert not faltan_pt, f"Faltan en PT: {faltan_pt}"


def test_sin_emojis_de_teclado_en_botones():
    # Sólo símbolos funcionales (✎ ⧉ ✓ ← ✕ ☾ ☀ ⋯ − +), nada de emojis.
    emojis = re.findall(r"[\U0001F300-\U0001FAFF]", HTML)
    assert not emojis
