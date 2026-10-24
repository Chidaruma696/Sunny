"""Understanding a formatting request written in Spanish, without any model.

The request is split into clauses ("rojo donde Estado sea PENDIENTE; en negrita los Importes
mayores de 50 mil"). Each clause yields one rule: the style words (colors, negrita, cursiva,
tachado), the scope (fila / celda), the column (a header mentioned in the clause, or the column
whose values contain the value named) and the condition (sea, distinto, mayor, menor, entre,
contenga, empiece, termine, vacío, repetido…). What cannot be understood is reported, never
guessed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from .rules import PALETTE, Condition, Rule, Style

COLOR_WORDS = {
    "rojo": "red", "roja": "red", "rojos": "red", "rojas": "red", "colorado": "red",
    "verde": "green", "verdes": "green",
    "amarillo": "yellow", "amarilla": "yellow", "amarillos": "yellow", "amarillas": "yellow",
    "azul": "blue", "azules": "blue", "celeste": "blue",
    "naranja": "orange", "naranjas": "orange", "anaranjado": "orange", "anaranjada": "orange",
    "gris": "gray", "grises": "gray", "plomo": "gray",
    "morado": "purple", "morada": "purple", "morados": "purple", "moradas": "purple",
    "lila": "purple", "violeta": "purple", "purpura": "purple",
}
COLOR_NAMES_ES = {"red": "rojo", "green": "verde", "yellow": "amarillo", "blue": "azul",
                  "orange": "naranja", "gray": "gris", "purple": "morado"}
BOLD_WORDS = ("negrita", "negritas", "bold", "resaltado en negrita")
ITALIC_WORDS = ("cursiva", "cursivas", "italica", "italicas")
STRIKE_WORDS = ("tachado", "tachada", "tachados", "tachadas", "tacha", "tachar", "tachalo", "tachala", "tachalos", "tachalas")
ROW_WORDS = ("fila", "filas", "renglon", "renglones", "linea", "lineas", "registro", "registros", "toda la fila", "todo el renglon")
CELL_WORDS = ("celda", "celdas", "casilla", "casillas")
FILLER = {"de", "del", "la", "las", "el", "los", "en", "a", "al", "que", "con", "color", "pinta", "pintar", "pon", "poner",
          "marca", "marcar", "marcame", "pintame", "ponme", "resalta", "resaltar", "resaltame", "colorea", "colorear",
          "quiero", "me", "todos", "todas", "todo", "toda", "lo", "donde", "cuando", "si", "cuyo", "cuya", "cuyos", "cuyas",
          "columna", "campo", "valor", "valores", "dato", "datos", "esten", "este", "sean", "sea", "es", "son", "fondo",
          "letra", "texto", "y", "e", "o", "u", "un", "una", "unos", "unas", "mas", "tambien", "ademas", "por", "favor",
          "hazlo", "ponlo", "ponlos", "ponlas", "dejalo", "dejalos", "dejalas"}

MIL = {"mil": 1_000, "millon": 1_000_000, "millones": 1_000_000, "k": 1_000, "m": 1_000_000}


@dataclass
class Parsed:
    rules: list[Rule]
    notes: list[str] = field(default_factory=list)   # what was not understood, one line each


def normalize(text: str) -> str:
    """Lowercase, no accents, same length as the input (so spans line up with the original)."""
    out = []
    for ch in text.lower():
        if ch == "ñ":
            out.append("ñ")
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        base = decomposed[0] if decomposed and unicodedata.category(decomposed[0]) != "Mn" else ch
        out.append(base if len(base) == 1 else ch)
    return "".join(out)


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^\wñ$%#.,/:-]+", normalize(text)) if w]


# ----------------------------------------------------------------------------- values

def parse_number(text: str) -> float | int | None:
    t = normalize(text).replace("$", "").replace("mxn", "").replace("pesos", "").replace("%", "").strip()
    m = re.fullmatch(r"(-?\d[\d.,]*)\s*(mil|millon|millones|k|m)?", t)
    if not m:
        return None
    raw, unit = m.group(1), m.group(2)
    if "," in raw and "." in raw:
        # both separators: the last one is the decimal mark ("12,000.50" or "12.000,50")
        decimal = "." if raw.rfind(".") > raw.rfind(",") else ","
        other = "," if decimal == "." else "."
        raw = raw.replace(other, "").replace(decimal, ".")
    # thousands separators: a dot or comma followed by exactly three digits, when there is only one kind
    if re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", raw):
        raw = re.sub(r"[.,]", "", raw)
    elif re.fullmatch(r"-?\d+,\d+", raw):
        raw = raw.replace(",", ".")
    elif re.fullmatch(r"-?\d+(\.\d+)?", raw):
        pass
    else:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if unit:
        value *= MIL[unit]
    return int(value) if value.is_integer() else value


def parse_date(text: str) -> date | None:
    t = text.strip()
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def parse_value(text: str):
    text = text.strip().strip("«»\"'“”‘’").strip().rstrip(".;:")
    if not text:
        return None
    d = parse_date(text)
    if d is not None:
        return d
    n = parse_number(text)
    if n is not None:
        return n
    return text


# ----------------------------------------------------------------------------- the parser

@dataclass
class _Clause:
    original: str
    norm: str
    style: Style
    scope: str
    scope_explicit: bool
    color_name: str | None


class SpanishParser:
    """Turns a Spanish request into rules for the given headers.

    VALUES, when given, maps each normalized text value of the sheet to the headers of the columns
    that contain it (see workbook.value_index), so "rojo los PENDIENTE" finds the Estado column
    without naming it, and "verde lo que diga vocho" finds the column whose texts contain "vocho".
    """

    def __init__(self, headers: list[str], values: dict[str, list[str]] | None = None,
                 lookup: Callable[[str], list[str]] | None = None):
        self.headers = headers
        self._norm_headers = sorted(((normalize(h).strip(), h) for h in headers), key=lambda p: -len(p[0]))
        self.values = values or {}
        self.lookup = lookup

    def columns_for(self, value: str, op: str) -> list[str]:
        """Headers of the columns where VALUE (normalized) appears, exactly or as a piece,
        depending on the operator. Header order of the sheet."""
        needle = normalize(value).strip()
        if not needle:
            return []
        if self.lookup is not None and op not in ("contains", "not_contains", "starts_with", "ends_with"):
            found = set(self.lookup(needle))
        else:
            found = set()
            for key, headers in self.values.items():
                hit = {"contains": needle in key, "not_contains": needle in key,
                       "starts_with": key.startswith(needle), "ends_with": key.endswith(needle)}.get(op, key == needle)
                if hit:
                    found.update(headers)
            if not found and self.lookup is not None:
                found = set(self.lookup(needle))
        return [h for h in self.headers if h in found]

    # --- splitting
    def split(self, text: str) -> list[str]:
        chunks = re.split(r"[;\n]|(?<=[^\d])\.\s+|\s+pero\s+|\s+mientras que\s+|\s+en cambio\s+", text)
        clauses: list[str] = []
        for chunk in chunks:
            if not chunk or not chunk.strip():
                continue
            # a comma or "y" separates two clauses only when both sides carry a style of their own;
            # otherwise it belongs to the clause ("entre 1 y 5", "PAGADO o CANCELADO")
            start = 0
            for m in re.finditer(r",|\s+y\s+|\s+e\s+", chunk):
                left, right = chunk[start:m.start()], chunk[m.end():]
                if left.strip() and right.strip() and self._has_style(left) and self._has_style(right):
                    clauses.append(left.strip())
                    start = m.end()
            if chunk[start:].strip():
                clauses.append(chunk[start:].strip())
        return clauses

    def _has_style(self, text: str) -> bool:
        n = normalize(text)
        words = set(re.split(r"[^\wñ#]+", n))
        if words & set(COLOR_WORDS) or words & set(BOLD_WORDS) or words & set(ITALIC_WORDS) or words & set(STRIKE_WORDS):
            return True
        return bool(re.search(r"#[0-9a-f]{6}\b", n))

    # --- one clause
    def parse(self, text: str) -> Parsed:
        rules: list[Rule] = []
        notes: list[str] = []
        previous_scope: str | None = None
        for clause in self.split(text):
            try:
                rule = self.parse_clause(clause, previous_scope)
            except ValueError as e:
                notes.append(f"No entendí «{clause.strip()}»: {e}")
                continue
            rules.append(rule)
            previous_scope = rule.scope
        if not rules and not notes:
            notes.append("No encontré ninguna orden. Ejemplo: «rojo donde Estado sea PENDIENTE».")
        return Parsed(rules=rules, notes=notes)

    def _strip_style(self, original: str) -> _Clause:
        norm = normalize(original)
        style = Style()
        color_name = None
        spans: list[tuple[int, int]] = []
        for m in re.finditer(r"#([0-9a-f]{6})\b", norm):
            style.fill = m.group(1).upper()
            spans.append(m.span())
        for m in re.finditer(r"[\wñ]+", norm):
            w = m.group(0)
            if w in COLOR_WORDS and style.fill is None:
                color_name = COLOR_WORDS[w]
                style.fill, style.font_color = PALETTE[color_name]
                spans.append(m.span())
            elif w in BOLD_WORDS:
                style.bold = True
                spans.append(m.span())
            elif w in ITALIC_WORDS:
                style.italic = True
                spans.append(m.span())
            elif w in STRIKE_WORDS:
                style.strike = True
                spans.append(m.span())
        # "letra roja" / "texto rojo" → font color only
        if color_name and re.search(r"\b(letra|texto|fuente)\s+(de\s+color\s+)?(" + "|".join(COLOR_WORDS) + r")\b", norm):
            style.fill = None
        if style.is_empty():
            raise ValueError("no dice qué color o estilo poner (rojo, verde, negrita, tachado…)")
        scope, explicit = "cell", False
        for w in ROW_WORDS:
            if re.search(rf"\b{w}\b", norm):
                scope, explicit = "row", True
                break
        for w in CELL_WORDS:
            if re.search(rf"\b{w}\b", norm):
                scope, explicit = "cell", True
                break
        # remove the style words from the working copy, keeping lengths aligned
        work = list(norm)
        for a, b in spans:
            for i in range(a, b):
                work[i] = " "
        return _Clause(original=original, norm="".join(work), style=style, scope=scope, scope_explicit=explicit,
                       color_name=color_name)

    def _find_column(self, norm: str) -> tuple[str, tuple[int, int]] | None:
        for nh, h in self._norm_headers:
            if not nh:
                continue
            # tolerate a plural or singular that differs from the header ("Importes" for "Importe")
            stem = nh[:-2] if nh.endswith("es") and len(nh) > 4 else nh[:-1] if nh.endswith("s") and len(nh) > 3 else nh
            m = re.search(rf"(?<![\wñ])(?:{re.escape(nh)}|{re.escape(stem)})(?:e?s)?(?![\wñ])", norm)
            if m:
                return h, m.span()
        return None

    def parse_clause(self, original: str, previous_scope: str | None = None) -> Rule:
        c = self._strip_style(original)
        norm = c.norm
        found = self._find_column(norm)
        column = found[0] if found else None
        if found:
            a, b = found[1]
            norm = norm[:a] + " " * (b - a) + norm[b:]
        op, value, value2, values = self._condition(norm, c.original)
        scope = c.scope
        if column is None:
            # "rojo las filas PENDIENTE, verde las PAGADO": the second clause names no column and no
            # scope, it is a continuation of the first, so it paints the same thing
            if not c.scope_explicit and previous_scope:
                scope = previous_scope
            # infer the column from the value named
            candidates: list[str] = []
            for v in ([value] if value is not None else []) + list(values):
                if isinstance(v, str):
                    candidates = self.columns_for(v, op)
                    if candidates:
                        break
            if len(candidates) == 1:
                column = candidates[0]
            elif len(candidates) > 1:
                raise ValueError(f"ese valor está en varias columnas ({', '.join(candidates)}); dime cuál")
            else:
                raise ValueError("no sé qué columna mirar; nómbrala (" + ", ".join(self.headers[:6]) + ("…" if len(self.headers) > 6 else "") + ")")
        rule = Rule(column=column, scope=scope, style=c.style,
                    condition=Condition(op=op, value=value, value2=value2, values=values),
                    description="")
        rule.description = describe(rule, c.color_name)
        return rule

    # --- conditions
    def _condition(self, norm: str, original: str):
        """Returns (op, value, value2, values). NORM has style words and the column blanked out."""
        def val(span: tuple[int, int]):
            return parse_value(original[span[0]:span[1]])

        def tail(start: int) -> tuple[int, int]:
            """Span of the value: from START to the end, minus trailing filler."""
            end = len(norm)
            seg = norm[start:end]
            # cut at a later connector that starts another thought
            m = re.search(r"\s+(en|de|para|como|con)\s+(las?|los?|el|toda|todas|todo|todos)\b", seg)
            if m and m.start() > 0:
                end = start + m.start()
            words = norm[start:end].split()
            while words and words[-1] in FILLER | set(ROW_WORDS) | set(CELL_WORDS):
                words.pop()
            while words and words[0] in FILLER - {"o", "u"}:
                words.pop(0)
            if not words:
                raise ValueError("falta el valor con el que comparar")
            text = " ".join(words)
            s = norm.find(text, start)
            return (s, s + len(text))

        if re.search(r"\b(repetid[oa]s?|duplicad[oa]s?|se repit[ae]n?)\b", norm):
            return "duplicate", None, None, []
        if re.search(r"\b(no\s+(este\s+|esten\s+)?vaci[oa]s?|con\s+dato|con\s+valor|tengan?\s+(algo|dato|valor)|llen[oa]s?|no\s+(este|esten)\s+en\s+blanco)\b", norm):
            return "not_empty", None, None, []
        if re.search(r"\b(vaci[oa]s?|en\s+blanco|sin\s+(dato|valor|nada|llenar)|no\s+teng[aa]n?|le\s+falt[ea]n?|falt[ea]n?)\b", norm):
            return "empty", None, None, []

        m = re.search(r"\bentre\s+(.+?)\s+(y|e|a)\s+(.+)$", norm)
        if m:
            v1 = parse_value(original[m.start(1):m.end(1)])
            end2 = tail(m.start(3))
            return "between", v1, val(end2), []

        patterns = [
            ("ge", r"\b(mayor(es)?\s+o\s+igual(es)?\s+(que|a|de)|>=|a\s+partir\s+de|al\s+menos|como\s+minimo|minimo|desde)\s+"),
            ("le", r"\b(menor(es)?\s+o\s+igual(es)?\s+(que|a|de)|<=|hasta|como\s+maximo|maximo|a\s+lo\s+sumo)\s+"),
            ("gt", r"\b(mayor(es)?\s+(que|a|de)|mas\s+de|mas\s+que|superior(es)?\s+a|por\s+encima\s+de|arriba\s+de|pas[ea]n?\s+de|supere[n]?)\s+|>\s*"),
            ("lt", r"\b(menor(es)?\s+(que|a|de)|menos\s+de|menos\s+que|inferior(es)?\s+a|por\s+debajo\s+de|abajo\s+de|debajo\s+de|no\s+lleg[au]e?n?\s+a)\s+|<\s*"),
            ("ne", r"\b(no\s+sea[n]?|no\s+es|no\s+son|distint[oa]s?\s+(de|a)|diferente[s]?\s+(de|a))\s+|!=\s*|<>\s*"),
            ("not_contains", r"\b(no\s+(contenga[n]?|contiene[n]?|incluya[n]?|incluye[n]?|diga[n]?|lleve[n]?))\s+"),
            ("contains", r"\b(contenga[n]?|contiene[n]?|incluya[n]?|incluye[n]?|diga[n]?|lleve[n]?|con\s+el\s+texto|que\s+tenga[n]?\s+la\s+palabra|con\s+la\s+palabra)\s+"),
            ("starts_with", r"\b(empiece[n]?|empieza[n]?|comience[n]?|comienza[n]?|inicie[n]?|inicia[n]?)\s+(por|con|en)\s+"),
            ("ends_with", r"\b(termine[n]?|termina[n]?|acabe[n]?|acaba[n]?|finalice[n]?)\s+(por|con|en)\s+"),
            ("eq", r"\b(sea[n]?|es|son|igual(es)?\s+a|=|diga[n]?|este[n]?\s+en|esten\s+como|marcad[oa]s?\s+como|valga[n]?)\s+"),
        ]
        for op, pat in patterns:
            m = re.search(pat, norm)
            if m:
                span = tail(m.end())
                raw = original[span[0]:span[1]]
                if op == "eq":
                    parts = [p for p in re.split(r"\s*,\s*|\s+o\s+|\s+u\s+", raw) if p.strip()]
                    if len(parts) > 1:
                        return "in", None, None, [parse_value(p) for p in parts]
                return op, parse_value(raw), None, []
        # no operator: a bare value after the column ("Estado PENDIENTE") or nothing at all
        words = [w for w in norm.split() if w not in FILLER and w not in ROW_WORDS and w not in CELL_WORDS]
        if words:
            text = " ".join(words)
            s = norm.find(words[0])
            raw = original[s:s + len(text)] if norm[s:s + len(text)] == text else text
            parts = [p for p in re.split(r"\s*,\s*|\s+o\s+|\s+u\s+", raw) if p.strip()]
            if len(parts) > 1:
                return "in", None, None, [parse_value(p) for p in parts]
            return "eq", parse_value(raw), None, []
        return "not_empty", None, None, []


# ----------------------------------------------------------------------------- descriptions

def _fmt(v) -> str:
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ")
    if isinstance(v, int):
        return f"{v:,}".replace(",", " ")
    return str(v)


def describe(rule: Rule, color_name: str | None = None) -> str:
    c = rule.condition
    what = "Filas" if rule.scope == "row" else "Celdas"
    col = rule.column
    cond = {
        "eq": lambda: f"con {col} igual a {_fmt(c.value)}",
        "ne": lambda: f"con {col} distinto de {_fmt(c.value)}",
        "gt": lambda: f"con {col} mayor que {_fmt(c.value)}",
        "ge": lambda: f"con {col} mayor o igual que {_fmt(c.value)}",
        "lt": lambda: f"con {col} menor que {_fmt(c.value)}",
        "le": lambda: f"con {col} menor o igual que {_fmt(c.value)}",
        "between": lambda: f"con {col} entre {_fmt(c.value)} y {_fmt(c.value2)}",
        "in": lambda: f"con {col} igual a " + " o ".join(_fmt(v) for v in c.values),
        "contains": lambda: f"con {col} que contiene «{c.value}»",
        "not_contains": lambda: f"con {col} que no contiene «{c.value}»",
        "starts_with": lambda: f"con {col} que empieza por «{c.value}»",
        "ends_with": lambda: f"con {col} que termina en «{c.value}»",
        "empty": lambda: f"sin {col}",
        "not_empty": lambda: f"con {col}",
        "duplicate": lambda: f"con {col} repetido",
    }[c.op]()
    styles = []
    if color_name:
        styles.append(f"en {COLOR_NAMES_ES[color_name]}")
    elif rule.style.fill:
        styles.append(f"en #{rule.style.fill}")
    if rule.style.bold:
        styles.append("en negrita")
    if rule.style.italic:
        styles.append("en cursiva")
    if rule.style.strike:
        styles.append("tachado")
    return f"{what} {cond}, {' y '.join(styles)}"
