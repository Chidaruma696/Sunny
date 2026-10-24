from datetime import date

import pytest

from sunny.parser import SpanishParser, parse_number, parse_value

HEADERS = ["Factura", "Cliente", "Estado", "Importe", "Vence", "Fecha de pago", "Unidad"]
VALUES = {"pendiente": ["Estado"], "pagado": ["Estado"], "acme": ["Cliente"], "cancelado": ["Estado"], "x": ["Cliente", "Estado"],
          "vw vocho 2001 blanco": ["Unidad"], "nissan tsuru": ["Unidad"], "vocho azul": ["Unidad"]}


def parser():
    return SpanishParser(HEADERS, values=VALUES)


def test_contains_finds_the_column_by_a_piece_of_text():
    r = one("pinta todo lo que diga vocho de verde")
    assert (r.column, r.condition.op, r.condition.value, r.style.fill) == ("Unidad", "contains", "vocho", "C6EFCE")
    r = one("amarillo lo que empiece por nissan")
    assert (r.column, r.condition.op, r.condition.value) == ("Unidad", "starts_with", "nissan")


def one(text):
    p = parser().parse(text)
    assert not p.notes, p.notes
    assert len(p.rules) == 1, p.rules
    return p.rules[0]


@pytest.mark.parametrize("text,expected", [
    ("50 mil", 50000), ("50,000", 50000), ("50.000", 50000), ("49999.5", 49999.5), ("1.5 millones", 1500000),
    ("$ 12,000.50", 12000.5), ("100", 100), ("-3", -3), ("hola", None), ("10%", 10),
])
def test_numbers(text, expected):
    assert parse_number(text) == expected


def test_values_pick_dates_numbers_and_text():
    assert parse_value("31/01/2026") == date(2026, 1, 31)
    assert parse_value("2026-01-31") == date(2026, 1, 31)
    assert parse_value("«PENDIENTE»") == "PENDIENTE"
    assert parse_value("2 mil") == 2000


def test_row_equals_with_color():
    r = one("pinta de rojo las filas donde Estado sea PENDIENTE")
    assert (r.column, r.scope, r.condition.op, r.condition.value) == ("Estado", "row", "eq", "PENDIENTE")
    assert r.style.fill == "FFC7CE" and r.style.font_color == "9C0006"
    assert r.description == "Filas con Estado igual a PENDIENTE, en rojo"


def test_greater_than_bold_cell():
    r = one("en negrita los Importes mayores de 50 mil")
    assert (r.column, r.scope, r.condition.op, r.condition.value) == ("Importe", "cell", "gt", 50000)
    assert r.style.bold is True and r.style.fill is None


def test_column_inferred_from_value():
    r = one("rojo los PENDIENTE")
    assert r.column == "Estado" and r.condition.op == "eq" and r.condition.value == "PENDIENTE"


def test_ambiguous_value_asks_for_the_column():
    p = parser().parse("rojo los X")
    assert not p.rules and "varias columnas" in p.notes[0]


def test_several_clauses_in_one_sentence():
    p = parser().parse("rojo donde Estado sea PENDIENTE, verde donde sea PAGADO y en negrita los Importes mayores de 50 mil")
    assert not p.notes, p.notes
    ops = [(r.column, r.condition.op, r.condition.value, r.style.fill, r.style.bold) for r in p.rules]
    assert ops == [("Estado", "eq", "PENDIENTE", "FFC7CE", None), ("Estado", "eq", "PAGADO", "C6EFCE", None),
                   ("Importe", "gt", 50000, None, True)]


def test_continuation_inherits_the_scope():
    p = parser().parse("rojo las filas PENDIENTE, verde las PAGADO y en negrita los Importes mayores de 50 mil")
    assert [r.scope for r in p.rules] == ["row", "row", "cell"]


def test_pero_splits_and_values_without_column():
    p = parser().parse("marcame todos los PENDIENTE de rojo pero los PAGADO en verde")
    assert [(r.column, r.condition.value, r.style.fill) for r in p.rules] == [("Estado", "PENDIENTE", "FFC7CE"), ("Estado", "PAGADO", "C6EFCE")]


def test_between_and_dates():
    r = one("amarillo cuando Vence esté entre 01/01/2026 y 31/03/2026")
    assert r.condition.op == "between" and r.condition.value == date(2026, 1, 1) and r.condition.value2 == date(2026, 3, 31)
    r = one("en gris las filas con Fecha de pago menor que 15/02/2026")
    assert r.column == "Fecha de pago" and r.condition.op == "lt" and r.condition.value == date(2026, 2, 15)


def test_empty_not_empty_duplicate_contains():
    r = one("en gris lo que no tenga Factura")
    assert (r.column, r.condition.op) == ("Factura", "empty")
    r = one("azul las filas con Factura")
    assert (r.column, r.condition.op, r.scope) == ("Factura", "not_empty", "row")
    r = one("naranja los Cliente repetidos")
    assert (r.column, r.condition.op) == ("Cliente", "duplicate")
    r = one("tacha las filas cuyo Cliente contenga acme")
    assert (r.column, r.condition.op, r.condition.value, r.style.strike) == ("Cliente", "contains", "acme", True)


def test_in_list_and_not_equal():
    r = one("morado donde Estado sea PAGADO o CANCELADO")
    assert r.condition.op == "in" and r.condition.values == ["PAGADO", "CANCELADO"]
    r = one("rojo las filas donde Estado no sea PAGADO")
    assert r.condition.op == "ne" and r.condition.value == "PAGADO"


def test_font_only_and_hex_colors():
    r = one("letra roja donde Importe sea menor que 0")
    assert r.style.fill is None and r.style.font_color == "9C0006" and r.condition.op == "lt"
    r = one("#ffcc00 donde Estado sea PENDIENTE")
    assert r.style.fill == "FFCC00"


def test_unknown_clause_is_reported_not_guessed():
    p = parser().parse("ordena por fecha; rojo donde Estado sea PENDIENTE")
    assert len(p.rules) == 1 and len(p.notes) == 1 and "ordena por fecha" in p.notes[0]
