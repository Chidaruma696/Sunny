[🇪🇸 Español](README.es.md)

<div align="center">
  <br/>
  <img src="sunny/assets/sunny.png" width="180" alt="Sunny icon" />

# Sunny

**サニー · Conditional formatting for Excel, described in plain words.**

<br/>

![Windows 10/11](https://img.shields.io/badge/windows-10%2F11%20x64-0078d4?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/qt-pyside6-41cd52?style=for-the-badge&logo=qt&logoColor=white)
![Apache 2.0 license](https://img.shields.io/badge/license-Apache%202.0-1b150d?style=for-the-badge)

<br/>

[![Download installer](https://img.shields.io/github/v/release/Chidaruma696/Sunny?label=%E2%AC%87%EF%B8%8F%20DOWNLOAD%20INSTALLER&style=for-the-badge&color=f0a020)](https://github.com/Chidaruma696/Sunny/releases/latest)

<br/>

*Drop the Excel, say what you want highlighted, check what it understood, apply · the original is never touched*

</div>

---

> [!IMPORTANT]
> **Your data stays on your machine.** To understand the request Sunny asks Claude, but it only sends the column
> headers, their types and your sentence. Not one cell value leaves the computer. The repository ignores `*.xlsx`
> so office files never end up in git by accident.

<br/>

## 📲 Download

1. Open the [latest release](https://github.com/Chidaruma696/Sunny/releases/latest) and grab `Sunny-x.y.z-setup.exe`.
2. Run it. It installs per user without asking for administrator rights. No Python or anything else required.
3. Open Sunny, go to **Ajustes** and paste an [Anthropic API key](https://console.anthropic.com/). One key is enough for the whole office; each request costs a fraction of a cent.

<br/>

## ☀️ What it does

| You write | Sunny understands | Excel gets |
| --- | --- | --- |
| *"Pinta de rojo las filas donde Estado sea PENDIENTE, de verde donde sea PAGADO, y en negrita los importes mayores de 50 mil"* | Three rules, each with the column it tests, the condition, the style and how many cells it would touch right now | Three real **conditional formatting** rules, written into a copy `<name> - Sunny.xlsx` |

Because the result is Excel's own conditional formatting (not painted cells), it keeps working when the data changes, and the file stays an ordinary workbook anyone can open and edit.

What a rule can say: equals, differs, greater / less / between (numbers and dates), contains, starts or ends with, is empty or not, is in a list, is duplicated in its column. What it can paint: fill color, font color, bold, italic, strikethrough; the tested cell or the whole row.

Before anything is written you see every rule as a line ("Filas con Estado PENDIENTE en rojo · 37 filas"), can untick the ones you do not want, and can save the set as JSON to reuse it next month without asking the model again.

<br/>

## ⚙️ How it works

1. `workbook.py` reads the sheet's shape: headers, the type of each column (number, date, text), row count.
2. `planner.py` sends that shape plus your sentence to Claude with a fixed JSON schema (structured output), so the answer is rules, never prose. Default model `claude-opus-5-5`, changeable in the settings.
3. `rules.py` validates each rule (known column, sane operator, real color) and drops the odd one without losing the rest.
4. `workbook.py` counts the matches in Python for the preview and, on **APLICAR**, writes `FormulaRule`s with [openpyxl](https://openpyxl.readthedocs.io/) into a copy. The formulas pin the tested column (`$C2="PENDIENTE"`), guard numeric comparisons with `ISNUMBER` so text never counts as "greater than", and express dates as `DATE(y,m,d)`.

The window is Qt ([PySide6](https://doc.qt.io/qtforpython-6/)) with the Komi look: paper and ink, square corners, hard shadows, sunlight palette. The interface is in Spanish.

<br/>

## ⌨️ Command line

The same executable (or `python -m sunny`) takes arguments:

```
Sunny.exe ventas.xlsx                                       # opens the window with that file
Sunny.exe --cli ventas.xlsx "rojo donde Estado sea PENDIENTE"   # asks the model, previews, writes "ventas - Sunny.xlsx"
Sunny.exe --cli ventas.xlsx --reglas mes.json -o listo.xlsx     # applies saved rules, no model, no network
```

| Option | Effect |
| --- | --- |
| `-s HOJA` | Sheet to work on (default: the active one) |
| `-o ARCHIVO.xlsx` | Where to save (default: `<name> - Sunny.xlsx` next to the original) |
| `--reglas REGLAS.json` | Apply saved rules instead of asking the model |
| `--guardar-reglas REGLAS.json` | Save the rules obtained |
| `--modelo MODELO` | Claude model for this run |
| `--cli` | Work without opening the window |

The API key comes from the settings saved by the window or from `ANTHROPIC_API_KEY`.

<br/>

## 🛠️ Build

You need Python 3.11+ and, for the installer, [Inno Setup 6](https://jrsoftware.org/isdl.php).

```powershell
git clone https://github.com/Chidaruma696/Sunny.git
cd Sunny
.\build.ps1                # .venv + deps + PyInstaller + Inno Setup → dist\Sunny-X.Y.Z-setup.exe
.\build.ps1 -NoInstaller   # only dist\Sunny\Sunny.exe
.\build.ps1 -Test          # the tests
```

To develop without building:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m sunny
.\.venv\Scripts\python -m pytest
```

Layout:

```
sunny/rules.py      Rule model, JSON schema for the planner, validation
sunny/workbook.py   Sheet shape, preview counts, conditional formatting with openpyxl
sunny/planner.py    Claude call with structured output (headers + request in, rules out)
sunny/settings.py   API key and model, shared by window and CLI
sunny/gui.py        PySide6 window (drag and drop, preview table, apply)
sunny/theme.py      Komi QSS, Sunny palette
sunny/cli.py        Arguments and entry point
tests/              pytest: rules, formulas, preview counts, written workbook
sunny.spec          PyInstaller (one folder, no console)
installer/Sunny.iss Inno Setup
build.ps1           All of the above in one step
```

<br/>

## 🗺️ Roadmap

- [ ] Offline mode: a small rule syntax for people who would rather not use a model.
- [ ] Number formats and column widths as part of a request.
- [ ] Several sheets in one go.
- [ ] Dark theme.

<br/>

## ⚖️ Legal

Sunny is free software under the [Apache 2.0](LICENSE) license. Third-party components and their licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Touhou Project and its characters belong to Team Shanghai Alice (ZUN); unofficial fan work made under their guidelines for derivative works, with no affiliation or endorsement.

<br/>

<div align="center">

サニー

</div>
