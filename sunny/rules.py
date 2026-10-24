"""The rule model: what the planner produces and what the workbook module applies.

A rule says *which column* is tested, *how* (the condition), *what gets painted* (the cell or
the whole row) and *with what style*. Rules are plain data so they can be shown to the user,
edited, saved as JSON and applied without any model in the loop.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

OPERATORS = (
    "eq", "ne", "gt", "ge", "lt", "le", "between", "in",
    "contains", "not_contains", "starts_with", "ends_with",
    "empty", "not_empty", "duplicate",
)
NEEDS_VALUE = {"eq", "ne", "gt", "ge", "lt", "le", "contains", "not_contains", "starts_with", "ends_with"}
SCOPES = ("cell", "row")

# Soft fills and matching font colors, the ones Excel itself offers in its presets.
PALETTE = {
    "red": ("FFC7CE", "9C0006"),
    "green": ("C6EFCE", "006100"),
    "yellow": ("FFEB9C", "9C5700"),
    "blue": ("BDD7EE", "1F4E78"),
    "orange": ("F8CBAD", "833C0B"),
    "gray": ("D9D9D9", "3A3A3A"),
    "purple": ("E4DFEC", "3F3151"),
}

HEX_RE = re.compile(r"^[0-9A-Fa-f]{6}$")


class RuleError(ValueError):
    """A rule that cannot be applied: unknown column, bad operator, malformed value…"""


@dataclass
class Style:
    fill: str | None = None        # "RRGGBB"
    font_color: str | None = None  # "RRGGBB"
    bold: bool | None = None
    italic: bool | None = None
    strike: bool | None = None

    def is_empty(self) -> bool:
        return not any((self.fill, self.font_color, self.bold, self.italic, self.strike))


@dataclass
class Condition:
    op: str
    value: Any = None       # number, text or ISO date, depending on the column
    value2: Any = None      # upper bound for "between"
    values: list[Any] = field(default_factory=list)  # for "in"
    case_sensitive: bool = False


@dataclass
class Rule:
    column: str             # header text of the tested column
    condition: Condition
    style: Style
    scope: str = "cell"     # "cell" paints the tested cell, "row" paints the whole row
    description: str = ""   # one line for the user, in their language
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


# ----------------------------------------------------------------------------- JSON schema

RULE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "column": {"type": "string", "description": "Exact header text of the column to test."},
        "scope": {"type": "string", "enum": list(SCOPES)},
        "description": {"type": "string", "description": "One short sentence for the user, in the user's language."},
        "condition": {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": list(OPERATORS)},
                "value": {"type": ["number", "string", "null"]},
                "value2": {"type": ["number", "string", "null"]},
                "values": {"type": "array", "items": {"type": ["number", "string"]}},
                "case_sensitive": {"type": "boolean"},
            },
            "required": ["op", "value", "value2", "values", "case_sensitive"],
            "additionalProperties": False,
        },
        "style": {
            "type": "object",
            "properties": {
                "fill": {"type": ["string", "null"], "description": "RRGGBB or null"},
                "font_color": {"type": ["string", "null"], "description": "RRGGBB or null"},
                "bold": {"type": ["boolean", "null"]},
                "italic": {"type": ["boolean", "null"]},
                "strike": {"type": ["boolean", "null"]},
            },
            "required": ["fill", "font_color", "bold", "italic", "strike"],
            "additionalProperties": False,
        },
    },
    "required": ["column", "scope", "description", "condition", "style"],
    "additionalProperties": False,
}

PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "rules": {"type": "array", "items": RULE_SCHEMA},
        "notes": {
            "type": "string",
            "description": "What could not be turned into a rule, or an empty string. In the user's language.",
        },
    },
    "required": ["rules", "notes"],
    "additionalProperties": False,
}


# ----------------------------------------------------------------------------- parsing

def _hex(value: Any, what: str) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lstrip("#")
    if text.lower() in PALETTE:
        return PALETTE[text.lower()][0] if what == "fill" else PALETTE[text.lower()][1]
    if not HEX_RE.match(text):
        raise RuleError(f"{what}: '{value}' is not an RRGGBB color")
    return text.upper()


def _scalar(value: Any) -> Any:
    """Numbers stay numbers; ISO dates become dates; everything else is text."""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        return float(text) if "." in text else int(text)
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return text


def rule_from_dict(data: dict) -> Rule:
    cond = data.get("condition") or {}
    op = cond.get("op")
    if op not in OPERATORS:
        raise RuleError(f"unknown operator '{op}'")
    column = str(data.get("column") or "").strip()
    if not column:
        raise RuleError("rule without column")
    scope = data.get("scope") or "cell"
    if scope not in SCOPES:
        raise RuleError(f"unknown scope '{scope}'")
    value = _scalar(cond.get("value"))
    value2 = _scalar(cond.get("value2"))
    values = [_scalar(v) for v in (cond.get("values") or [])]
    if op in NEEDS_VALUE and value is None:
        raise RuleError(f"operator '{op}' needs a value")
    if op == "between" and (value is None or value2 is None):
        raise RuleError("'between' needs two values")
    if op == "in" and not values:
        raise RuleError("'in' needs a list of values")
    style_data = data.get("style") or {}
    style = Style(
        fill=_hex(style_data.get("fill"), "fill"),
        font_color=_hex(style_data.get("font_color"), "font_color"),
        bold=style_data.get("bold"),
        italic=style_data.get("italic"),
        strike=style_data.get("strike"),
    )
    if style.is_empty():
        raise RuleError("rule without any style")
    return Rule(
        column=column,
        condition=Condition(op=op, value=value, value2=value2, values=values,
                            case_sensitive=bool(cond.get("case_sensitive", False))),
        style=style,
        scope=scope,
        description=str(data.get("description") or ""),
        enabled=bool(data.get("enabled", True)),
    )


def rules_from_plan(data: dict) -> tuple[list[Rule], str, list[str]]:
    """A plan dict (what the planner returns, or a saved JSON) into rules.

    Returns (rules, notes, errors): bad rules are reported, not fatal, so one odd rule does not
    throw away the rest of the user's request.
    """
    rules: list[Rule] = []
    errors: list[str] = []
    for i, item in enumerate(data.get("rules") or [], start=1):
        try:
            rules.append(rule_from_dict(item))
        except RuleError as e:
            errors.append(f"rule {i}: {e}")
    return rules, str(data.get("notes") or ""), errors


def plan_to_dict(rules: list[Rule], notes: str = "") -> dict:
    out = []
    for r in rules:
        d = r.to_dict()
        for key in ("value", "value2"):
            if isinstance(d["condition"][key], (date, datetime)):
                d["condition"][key] = d["condition"][key].isoformat()
        d["condition"]["values"] = [v.isoformat() if isinstance(v, (date, datetime)) else v for v in d["condition"]["values"]]
        out.append(d)
    return {"rules": out, "notes": notes}
