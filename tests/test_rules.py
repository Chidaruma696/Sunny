from datetime import date

import pytest

from sunny.rules import RuleError, plan_to_dict, rule_from_dict, rules_from_plan


def base(**over):
    d = {
        "column": "Estado", "scope": "row", "description": "rojo pendiente",
        "condition": {"op": "eq", "value": "PENDIENTE", "value2": None, "values": [], "case_sensitive": False},
        "style": {"fill": "FFC7CE", "font_color": "9C0006", "bold": None, "italic": None, "strike": None},
    }
    d.update(over)
    return d


def test_parses_a_plain_rule():
    r = rule_from_dict(base())
    assert r.column == "Estado" and r.scope == "row"
    assert r.condition.op == "eq" and r.condition.value == "PENDIENTE"
    assert r.style.fill == "FFC7CE" and r.style.font_color == "9C0006"


def test_palette_names_and_hash_prefix_are_accepted():
    r = rule_from_dict(base(style={"fill": "green", "font_color": "#006100", "bold": True, "italic": None, "strike": None}))
    assert r.style.fill == "C6EFCE" and r.style.font_color == "006100" and r.style.bold is True


def test_numbers_and_dates_become_real_values():
    r = rule_from_dict(base(condition={"op": "gt", "value": "50000", "value2": None, "values": [], "case_sensitive": False}))
    assert r.condition.value == 50000
    r = rule_from_dict(base(condition={"op": "lt", "value": "2026-01-31", "value2": None, "values": [], "case_sensitive": False}))
    assert r.condition.value == date(2026, 1, 31)


@pytest.mark.parametrize("bad", [
    {"condition": {"op": "like", "value": "x", "value2": None, "values": [], "case_sensitive": False}},
    {"column": ""},
    {"scope": "sheet"},
    {"condition": {"op": "gt", "value": None, "value2": None, "values": [], "case_sensitive": False}},
    {"condition": {"op": "between", "value": 1, "value2": None, "values": [], "case_sensitive": False}},
    {"condition": {"op": "in", "value": None, "value2": None, "values": [], "case_sensitive": False}},
    {"style": {"fill": None, "font_color": None, "bold": None, "italic": None, "strike": None}},
    {"style": {"fill": "rojo", "font_color": None, "bold": None, "italic": None, "strike": None}},
])
def test_rejects_malformed_rules(bad):
    with pytest.raises(RuleError):
        rule_from_dict(base(**bad))


def test_plan_keeps_good_rules_and_reports_bad_ones():
    rules, notes, errors = rules_from_plan({"rules": [base(), base(scope="nope")], "notes": "ordenar no se puede"})
    assert len(rules) == 1 and len(errors) == 1 and "rule 2" in errors[0]
    assert notes == "ordenar no se puede"


def test_round_trip_through_json_dict():
    r = rule_from_dict(base(condition={"op": "between", "value": "2026-01-01", "value2": "2026-12-31", "values": [], "case_sensitive": False}))
    data = plan_to_dict([r], "n")
    assert data["rules"][0]["condition"]["value"] == "2026-01-01"
    again, _, errors = rules_from_plan(data)
    assert not errors and again[0].condition.value2 == date(2026, 12, 31)
