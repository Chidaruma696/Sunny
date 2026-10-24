"""Turning the user's words into rules with Claude.

Only the sheet's shape travels: sheet name, row count, column headers and their types. The
cell values never leave the machine. The model answers with JSON that matches PLAN_SCHEMA
(structured output), so what comes back is rules, not prose.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .rules import PALETTE, PLAN_SCHEMA, Rule, rules_from_plan

DEFAULT_MODEL = "claude-opus-5-5"
SETTINGS_ORG = "Chidaruma"

SYSTEM = """You turn a request about formatting a spreadsheet into conditional-formatting rules.

You receive the sheet's shape (headers and the type of each column) and the user's request, usually
in Spanish. Answer with rules only, following the schema. Guidelines:

- "column" is the exact header text. Pick the column the user means even if they paraphrase it.
- Use "scope": "row" when the user says rows, lines, records or "the whole row"; otherwise "cell".
- Text comparisons are case-insensitive unless the user insists on exact case.
- For colors use these fills (RRGGBB): red FFC7CE, green C6EFCE, yellow FFEB9C, blue BDD7EE,
  orange F8CBAD, gray D9D9D9, purple E4DFEC. Pair a fill with its dark font color when the user
  only says a color: red 9C0006, green 006100, yellow 9C5700, blue 1F4E78, orange 833C0B,
  gray 3A3A3A, purple 3F3151. If the user gives an explicit hex color, use it as given.
- Dates go in ISO format (YYYY-MM-DD). Numbers are bare numbers. Thousands separators or currency
  signs in the request are not part of the value ("50 mil" is 50000).
- When the user asks for something a rule cannot express (sorting, deleting, formulas, charts),
  leave it out of "rules" and say so briefly in "notes", in the user's language.
- "description" is one short sentence in the user's language describing what that rule paints.
- Do not invent rules the user did not ask for.
"""


class PlannerError(RuntimeError):
    """Anything that stops us from getting rules out of the model."""


@dataclass
class Plan:
    rules: list[Rule]
    notes: str
    errors: list[str]
    raw: dict


def api_key_from_env() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or None


def plan(request: str, shape: dict, api_key: str | None = None, model: str = DEFAULT_MODEL) -> Plan:
    """Ask the model for rules. SHAPE is SheetInfo.describe(). Raises PlannerError."""
    if not request.strip():
        raise PlannerError("empty request")
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise PlannerError("the anthropic package is not installed") from e

    key = api_key or api_key_from_env()
    if not key:
        raise PlannerError("no API key: set it in the settings or in ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key)
    user = json.dumps({"sheet": shape, "request": request}, ensure_ascii=False)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError as e:
        raise PlannerError("the API key was rejected") from e
    except anthropic.RateLimitError as e:
        raise PlannerError("rate limited by the API, try again in a minute") from e
    except anthropic.APIStatusError as e:
        raise PlannerError(f"API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise PlannerError("could not reach the API: check the connection") from e
    if response.stop_reason == "refusal":
        raise PlannerError("the model declined the request")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise PlannerError("the model did not answer with valid JSON") from e
    rules, notes, errors = rules_from_plan(data)
    return Plan(rules=rules, notes=notes, errors=errors, raw=data)


def palette_help() -> str:
    return ", ".join(PALETTE)
