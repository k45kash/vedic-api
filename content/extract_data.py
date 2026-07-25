#!/usr/bin/env python3
"""Пересборка контентной базы: вытаскивает JS-константы из исходного HTML в JSON.

Запуск из корня репозитория:
    .venv/bin/python content/extract_data.py

Пути считаются от самого файла, поэтому скрипт работает из любого клона и
не зависит от каталогов на конкретной машине. Исходник и выход можно
переопределить аргументами: extract_data.py [SRC] [OUT].

ВАЖНО, что скрипт покрывает не всё. Он вытаскивает 28 JSON — те, что лежали
в HTML готовыми JS-константами. Ещё пять файлов собраны разбором вёрстки и
стилей вручную, скрипт их НЕ перезапишет и НЕ восстановит:
    chart_geometry.json · design_tokens.json · disclaimers.json
    filter_defs.json    · ui_texts.json
История того извлечения — в docs/content-base/EXTRACTION-PLAN.md.
"""
import json, re, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Исходник живёт в репозитории рядом с прототипами — из него собран весь content/.
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "prototype", "nakshatry_polnyy.html")
OUT = sys.argv[2] if len(sys.argv) > 2 else HERE

if not os.path.exists(SRC):
    sys.exit(f"Исходный HTML не найден: {SRC}\n"
             f"Укажи путь аргументом: python content/extract_data.py <файл.html>")

html = open(SRC, encoding="utf-8").read()

def extract_literal(decl_regex):
    """Find declaration, return the balanced [..] or {..} literal text."""
    m = re.search(decl_regex, html)
    if not m:
        return None
    start = html.find("=", m.start())
    while html[start] not in "[{":
        start += 1
    depth = 0; j = start; instr = None; esc = False
    while j < len(html):
        c = html[j]
        if instr:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == instr: instr = None
        else:
            if c in "\"'": instr = c
            elif c in "[{": depth += 1
            elif c in "]}":
                depth -= 1
                if depth == 0:
                    return html[start:j+1]
        j += 1
    return None

def js_to_json(text):
    """Tolerant conversion of a simple JS literal (unquoted keys, single quotes)."""
    out = []; i = 0; n = len(text)
    while i < n:
        c = text[i]
        if c == '"':  # double-quoted string: copy verbatim
            j = i + 1
            while j < n:
                if text[j] == "\\": j += 2; continue
                if text[j] == '"': break
                j += 1
            out.append(text[i:j+1]); i = j + 1
        elif c == "'":  # single-quoted string -> double-quoted
            j = i + 1; buf = []
            while j < n:
                if text[j] == "\\":
                    nxt = text[j+1]
                    buf.append(nxt if nxt == "'" else "\\" + nxt)
                    j += 2; continue
                if text[j] == "'": break
                buf.append(text[j]); j += 1
            s = "".join(buf).replace('"', '\\"')
            out.append('"' + s + '"'); i = j + 1
        elif c == "/" and i + 1 < n and text[i+1] == "/":  # line comment
            j = text.find("\n", i)
            i = n if j == -1 else j
        else:
            out.append(c); i += 1
    s = "".join(out)
    # quote unquoted identifier keys: {key: / ,key:
    s = re.sub(r'([\{,\[]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', s)
    # also digit keys {1:1, 9:1}
    s = re.sub(r'([\{,]\s*)(\d+)(\s*:)', r'\1"\2"\3', s)
    # trailing commas
    s = re.sub(r',(\s*[\]\}])', r'\1', s)
    return s

# name -> (declaration regex, output filename)
TARGETS = {
    # strict-JSON consts (content base)
    "DATA":             (r'const DATA = \[',             "nakshatras.json"),
    "NAMES":            (r'const NAMES = \[',            "nakshatra_names.json"),
    "PLANET_LAYER":     (r'const PLANET_LAYER = \{',     "planet_in_nakshatra.json"),
    "EVENTS_DATA":      (r'const EVENTS_DATA = \{',      "events_muhurta.json"),
    "GLOSSARY":         (r'const GLOSSARY = \{',         "glossary.json"),
    "HOUSES_DATA":      (r'const HOUSES_DATA = \{',      "houses.json"),
    "MANTRA_UP":        (r'const MANTRA_UP = \{',        "mantra_upaya.json"),
    "MUHURTA30_DATA":   (r'const MUHURTA30_DATA = \{',   "muhurta30.json"),
    "PADA_DATA":        (r'const PADA_DATA = \{',        "padas.json"),
    "PANCHANGA_DATA":   (r'const PANCHANGA_DATA = \{',   "panchanga.json"),
    "PLACEMENTS_DATA":  (r'const PLACEMENTS_DATA = \{',  "placements.json"),
    "PLANET_STORIES":   (r'const PLANET_STORIES = \{',   "planet_stories.json"),
    "RETRO_DATA":       (r'const RETRO_DATA = \{',       "retrograde.json"),
    "SADHANA_DATA":     (r'const SADHANA_DATA = \{',     "sadhana.json"),
    "SIGNS_DATA":       (r'const SIGNS_DATA = \{',       "signs.json"),
    "SOURCES_DATA":     (r'const SOURCES_DATA = \{',     "sources.json"),
    "TARA_SCHOOL":      (r'const TARA_SCHOOL = \{',      "tara_school.json"),
    "TITHI_DATA":       (r'const TITHI_DATA = \{',       "tithi.json"),
    "YOGAKARMA_DATA":   (r'const YOGAKARMA_DATA = \{',   "yogakarma.json"),
    # calculator tables (loose JS literals)
    "TARA":             (r'\bvar TARA=\[',               "tara_bala.json"),
    "TARA_DANA":        (r'\bvar TARA_DANA=\[',          "tara_dana.json"),
    "NAK_RULERS_SEQ":   (r'\bvar NAK_RULERS_SEQ=\[',     "nak_rulers_seq.json"),
    "NAK_RULER_SHORT":  (r'\bvar NAK_RULER_SHORT=\[',    "nak_ruler_short.json"),
    "PICKER_WEIGHTS":   (r'\bvar PICKER_WEIGHTS=\{',     "picker_weights.json"),
    "GAND_PADA":        (r'\bvar GAND_PADA=\{',          "gandanta_padas.json"),
    "SADHANA_DAY_IDX":  (r'\bvar SADHANA_DAY_IDX=\{',    "sadhana_day_index.json"),
    "SIGN_SHORT":       (r'\bvar SIGN_SHORT=\[',         "sign_short.json"),
    # UI colors, grouped afterwards
    "PLANET_COLORS":    (r'const PLANET_COLORS=\{',      None),
    "RULER_COLORS":     (r'const RULER_COLORS=\{',       None),
    "SADHANA_ELEM_COL": (r'\bvar SADHANA_ELEM_COL=\{',   None),
}

os.makedirs(OUT, exist_ok=True)
parsed = {}
errors = []
for name, (rx, fname) in TARGETS.items():
    lit = extract_literal(rx)
    if lit is None:
        errors.append(f"{name}: declaration not found")
        continue
    try:
        obj = json.loads(lit)
    except json.JSONDecodeError:
        try:
            obj = json.loads(js_to_json(lit))
        except json.JSONDecodeError as e:
            errors.append(f"{name}: parse failed: {e}")
            continue
    parsed[name] = obj
    if fname:
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

# grouped UI colors file
colors = {k: parsed[k] for k in ("PLANET_COLORS", "RULER_COLORS", "SADHANA_ELEM_COL") if k in parsed}
if colors:
    with open(os.path.join(OUT, "ui_colors.json"), "w", encoding="utf-8") as f:
        json.dump(colors, f, ensure_ascii=False, indent=2)

print(f"extracted: {len(parsed)}/{len(TARGETS)}")
for e in errors:
    print("ERROR:", e)
sys.exit(1 if errors else 0)
