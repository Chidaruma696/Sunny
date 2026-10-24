"""Reading a sheet's shape, previewing what a rule would touch, and writing the formatting.

The formatting is written as real Excel conditional formatting (openpyxl FormulaRule), so the
result keeps reacting when the data changes and the file stays an ordinary workbook. The
preview counts are computed here in Python with the same semantics as the formulas, so what
the user is told ("37 cells") is what Excel will paint.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .rules import Rule, RuleError


@dataclass
class ColumnInfo:
    header: str
    letter: str
    index: int               # 1-based
    kind: str                # "number", "date", "text", "empty", "mixed"
    non_empty: int


@dataclass
class SheetInfo:
    name: str
    header_row: int
    first_row: int           # first data row
    last_row: int
    columns: list[ColumnInfo] = field(default_factory=list)

    def column(self, header: str) -> ColumnInfo:
        wanted = header.strip().casefold()
        for c in self.columns:
            if c.header.strip().casefold() == wanted:
                return c
        raise RuleError(f"no column named '{header}' (columns: {', '.join(c.header for c in self.columns)})")

    def describe(self) -> dict:
        """What the planner gets to see: headers and types, never the data."""
        return {
            "sheet": self.name,
            "rows": max(0, self.last_row - self.first_row + 1),
            "columns": [{"header": c.header, "type": c.kind} for c in self.columns],
        }


def _kind(values: list[Any]) -> str:
    kinds = set()
    for v in values:
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if isinstance(v, bool):
            kinds.add("text")
        elif isinstance(v, (int, float)):
            kinds.add("number")
        elif isinstance(v, (date, datetime)):
            kinds.add("date")
        else:
            kinds.add("text")
    if not kinds:
        return "empty"
    if len(kinds) == 1:
        return kinds.pop()
    return "mixed"


def inspect(path: Path, sheet: str | None = None, header_row: int = 1) -> SheetInfo:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet] if sheet else wb.active
        rows = list(ws.iter_rows(min_row=header_row, values_only=True))
    finally:
        wb.close()
    if not rows:
        raise RuleError("the sheet is empty")
    headers = rows[0]
    data = rows[1:]
    # trailing empty rows are not data
    while data and all(v is None or (isinstance(v, str) and not v.strip()) for v in data[-1]):
        data.pop()
    columns: list[ColumnInfo] = []
    for i, h in enumerate(headers, start=1):
        if h is None or not str(h).strip():
            continue
        values = [r[i - 1] if i - 1 < len(r) else None for r in data]
        columns.append(ColumnInfo(
            header=str(h).strip(), letter=get_column_letter(i), index=i,
            kind=_kind(values),
            non_empty=sum(1 for v in values if v is not None and not (isinstance(v, str) and not v.strip())),
        ))
    return SheetInfo(name=ws.title, header_row=header_row, first_row=header_row + 1,
                     last_row=header_row + len(data), columns=columns)


def sheet_names(path: Path) -> list[str]:
    wb = load_workbook(path, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


# ----------------------------------------------------------------------------- matching (preview)

def _text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def _as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def _cmp_pair(cell: Any, target: Any) -> tuple[Any, Any] | None:
    """Both sides as comparable values, or None when they are of different kinds."""
    if isinstance(cell, bool) or isinstance(target, bool):
        return None
    cd, td = _as_date(cell), _as_date(target)
    if td is not None:
        return (cd, td) if cd is not None else None
    if isinstance(target, (int, float)):
        return (cell, target) if isinstance(cell, (int, float)) and not isinstance(cell, bool) else None
    return (_text(cell).casefold(), _text(target).casefold())


def matches(rule: Rule, value: Any, seen_counts: dict[str, int] | None = None) -> bool:
    c = rule.condition
    op = c.op
    empty = value is None or (isinstance(value, str) and not value.strip())
    if op == "empty":
        return empty
    if op == "not_empty":
        return not empty
    if empty:
        return False
    if op == "duplicate":
        return bool(seen_counts) and seen_counts.get(_text(value).casefold(), 0) > 1
    text = _text(value)
    if not c.case_sensitive:
        text_cmp = text.casefold()
    else:
        text_cmp = text
    if op in ("contains", "not_contains", "starts_with", "ends_with"):
        needle = _text(c.value)
        if not c.case_sensitive:
            needle = needle.casefold()
        hit = {"contains": needle in text_cmp, "not_contains": needle not in text_cmp,
               "starts_with": text_cmp.startswith(needle), "ends_with": text_cmp.endswith(needle)}[op]
        return hit
    if op == "in":
        wanted = {_text(v) if c.case_sensitive else _text(v).casefold() for v in c.values}
        return text_cmp in wanted
    if op in ("eq", "ne"):
        pair = _cmp_pair(value, c.value)
        if pair is None:
            equal = False
        else:
            a, b = pair
            if isinstance(a, str) and c.case_sensitive:
                a, b = text, _text(c.value)
            equal = a == b
        return equal if op == "eq" else not equal
    if op in ("gt", "ge", "lt", "le", "between"):
        pair = _cmp_pair(value, c.value)
        if pair is None or isinstance(pair[0], str):
            return False
        a, b = pair
        if op == "between":
            pair2 = _cmp_pair(value, c.value2)
            if pair2 is None:
                return False
            return b <= a <= pair2[1]
        return {"gt": a > b, "ge": a >= b, "lt": a < b, "le": a <= b}[op]
    raise RuleError(f"unknown operator '{op}'")


@dataclass
class Preview:
    rule: Rule
    cells: int          # matching cells in the tested column
    rows: int           # rows the rule paints (== cells, but as rows for scope "row")


def preview(path: Path, info: SheetInfo, rules: list[Rule]) -> list[Preview]:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[info.name]
        rows = list(ws.iter_rows(min_row=info.first_row, max_row=info.last_row, values_only=True))
    finally:
        wb.close()
    out: list[Preview] = []
    for rule in rules:
        col = info.column(rule.column)
        values = [r[col.index - 1] if col.index - 1 < len(r) else None for r in rows]
        counts: dict[str, int] = {}
        if rule.condition.op == "duplicate":
            for v in values:
                if v is not None and _text(v).strip():
                    counts[_text(v).casefold()] = counts.get(_text(v).casefold(), 0) + 1
        n = sum(1 for v in values if matches(rule, v, counts))
        out.append(Preview(rule=rule, cells=n, rows=n))
    return out


# ----------------------------------------------------------------------------- formulas

def _lit(value: Any) -> str:
    """A value as an Excel literal: numbers bare, dates as DATE(), text quoted."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value) if isinstance(value, float) and not value.is_integer() else str(int(value))
    d = _as_date(value)
    if d is not None:
        return f"DATE({d.year},{d.month},{d.day})"
    return '"' + str(value).replace('"', '""') + '"'


def formula_for(rule: Rule, col: ColumnInfo, first_row: int, last_row: int) -> str:
    """The conditional-formatting formula, relative to the first data row."""
    ref = f"${col.letter}{first_row}"
    c = rule.condition
    op = c.op
    if op == "empty":
        return f'{ref}=""'
    if op == "not_empty":
        return f'{ref}<>""'
    if op == "duplicate":
        rng = f"${col.letter}${first_row}:${col.letter}${last_row}"
        return f'AND({ref}<>"",COUNTIF({rng},{ref})>1)'
    if op in ("contains", "not_contains"):
        fn = "FIND" if c.case_sensitive else "SEARCH"
        test = f"ISNUMBER({fn}({_lit(_text(c.value))},{ref}))"
        return test if op == "contains" else f'AND({ref}<>"",NOT({test}))'
    if op == "starts_with":
        s = _text(c.value)
        left = f"LEFT({ref},{len(s)})"
        return f"EXACT({left},{_lit(s)})" if c.case_sensitive else f"{left}={_lit(s)}"
    if op == "ends_with":
        s = _text(c.value)
        right = f"RIGHT({ref},{len(s)})"
        return f"EXACT({right},{_lit(s)})" if c.case_sensitive else f"{right}={_lit(s)}"
    if op == "in":
        if c.case_sensitive:
            parts = ",".join(f"EXACT({ref},{_lit(_text(v))})" for v in c.values)
        else:
            parts = ",".join(f"{ref}={_lit(v)}" for v in c.values)
        return f"OR({parts})"
    numeric = isinstance(c.value, (int, float)) and not isinstance(c.value, bool) or _as_date(c.value) is not None
    if op in ("eq", "ne"):
        if numeric:
            test = f"AND(ISNUMBER({ref}),{ref}={_lit(c.value)})"
        elif c.case_sensitive:
            test = f"EXACT({ref},{_lit(_text(c.value))})"
        else:
            test = f"{ref}={_lit(_text(c.value))}"
        return test if op == "eq" else f'AND({ref}<>"",NOT({test}))'
    if op in ("gt", "ge", "lt", "le"):
        sym = {"gt": ">", "ge": ">=", "lt": "<", "le": "<="}[op]
        return f"AND(ISNUMBER({ref}),{ref}{sym}{_lit(c.value)})"
    if op == "between":
        return f"AND(ISNUMBER({ref}),{ref}>={_lit(c.value)},{ref}<={_lit(c.value2)})"
    raise RuleError(f"unknown operator '{op}'")


def _differential_style(rule: Rule) -> tuple[PatternFill | None, Font | None]:
    s = rule.style
    fill = PatternFill(start_color=s.fill, end_color=s.fill, fill_type="solid") if s.fill else None
    font_kwargs: dict[str, Any] = {}
    if s.font_color:
        font_kwargs["color"] = s.font_color
    if s.bold is not None:
        font_kwargs["bold"] = s.bold
    if s.italic is not None:
        font_kwargs["italic"] = s.italic
    if s.strike is not None:
        font_kwargs["strike"] = s.strike
    font = Font(**font_kwargs) if font_kwargs else None
    return fill, font


def output_path(source: Path, suffix: str = " - Sunny") -> Path:
    return source.with_name(f"{source.stem}{suffix}{source.suffix}")


def apply(source: Path, info: SheetInfo, rules: list[Rule], destination: Path | None = None) -> Path:
    """Write the rules as conditional formatting into a copy of SOURCE. Never touches the original."""
    destination = destination or output_path(source)
    if destination.resolve() == source.resolve():
        raise RuleError("the destination must be a different file from the source")
    shutil.copyfile(source, destination)
    wb = load_workbook(destination)
    try:
        ws = wb[info.name]
        last_col = max(c.index for c in info.columns) if info.columns else ws.max_column
        for rule in rules:
            if not rule.enabled:
                continue
            col = info.column(rule.column)
            if rule.scope == "row":
                rng = f"A{info.first_row}:{get_column_letter(last_col)}{info.last_row}"
            else:
                rng = f"{col.letter}{info.first_row}:{col.letter}{info.last_row}"
            fill, font = _differential_style(rule)
            formula = formula_for(rule, col, info.first_row, info.last_row)
            # Excel resolves a relative column reference against the range's first column; the
            # formula pins the column with $ so the same rule works for cell and row scope.
            ws.conditional_formatting.add(rng, FormulaRule(formula=[formula], fill=fill, font=font, stopIfTrue=False))
        wb.save(destination)
    finally:
        wb.close()
    return destination
