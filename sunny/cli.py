"""Entry point: no arguments opens the window; with --cli it works without one."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import APP_NAME, __version__


def _attach_console() -> None:
    """Sunny.exe is a windowed program (no console), so in --cli mode it has no stdout. On Windows,
    attach to the console it was launched from, so the output lands in that terminal."""
    if sys.platform == "win32" and sys.stdout is None:
        import ctypes

        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)  # noqa: SIM115
            sys.stderr = sys.stdout
    # Windows consoles often run in cp1252 and cannot draw ✓ ⚠ ✗.
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sunny",
        description="Formato condicional para Excel dicho en palabras. Sin argumentos abre la ventana.",
    )
    p.add_argument("excel", nargs="?", help="archivo .xlsx")
    p.add_argument("orden", nargs="?", help="qué formato quieres, en palabras")
    p.add_argument("-s", "--hoja", metavar="HOJA", help="hoja del libro (por defecto, la activa)")
    p.add_argument("-o", "--salida", metavar="ARCHIVO.xlsx", help="dónde guardar (por defecto, «<nombre> - Sunny.xlsx» junto al original)")
    p.add_argument("--reglas", metavar="REGLAS.json", help="aplicar estas reglas guardadas en vez de entender una frase")
    p.add_argument("--guardar-reglas", metavar="REGLAS.json", help="guardar las reglas obtenidas en este archivo")
    p.add_argument("--cli", action="store_true", help="trabajar sin abrir la ventana")
    p.add_argument("-V", "--version", action="version", version=f"{APP_NAME} {__version__}")
    args = p.parse_args(argv)

    if not args.cli:
        from .gui import run

        return run(args.excel, args.orden, args.hoja)

    _attach_console()
    if not args.excel:
        p.error("indica el archivo .xlsx")
    source = Path(args.excel)
    if not source.is_file():
        p.error(f"no existe {source}")

    from .rules import RuleError, plan_to_dict, rules_from_plan
    from .workbook import apply, inspect, output_path, preview

    try:
        info = inspect(source, args.hoja)
    except RuleError as e:
        print(f"✗ {e}")
        return 1
    print(f"{source.name} · hoja «{info.name}» · {info.last_row - info.first_row + 1} filas · "
          + ", ".join(f"{c.header} ({c.kind})" for c in info.columns))

    notes = ""
    if args.reglas:
        data = json.loads(Path(args.reglas).read_text(encoding="utf-8"))
        rules, notes, errors = rules_from_plan(data)
    else:
        if not args.orden:
            p.error("indica la orden entre comillas, o --reglas con un JSON")
        from .parser import SpanishParser
        from .workbook import value_index

        parsed = SpanishParser([c.header for c in info.columns], values=value_index(source, info)).parse(args.orden)
        rules, notes, errors = parsed.rules, "\n".join(parsed.notes), []

    for e in errors:
        print(f"⚠ {e}")
    if notes:
        print(f"ℹ {notes}")
    if not rules:
        print("✗ no salió ninguna regla")
        return 1
    try:
        previews = preview(source, info, rules)
    except RuleError as e:
        print(f"✗ {e}")
        return 1
    for pv in previews:
        where = "filas" if pv.rule.scope == "row" else "celdas"
        print(f"  · {pv.rule.description or pv.rule.column}: {pv.cells} {where}")
    if args.guardar_reglas:
        Path(args.guardar_reglas).write_text(json.dumps(plan_to_dict(rules, notes), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"reglas guardadas en {args.guardar_reglas}")
    destination = Path(args.salida) if args.salida else output_path(source)
    try:
        out = apply(source, info, rules, destination)
    except RuleError as e:
        print(f"✗ {e}")
        return 1
    print(f"✓ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
