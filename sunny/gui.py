"""Sunny's main window (PySide6). Interface in Spanish."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import APP_KANA, APP_NAME, REPO_URL, __version__
from .parser import SpanishParser
from .planner import DEFAULT_MODEL, Plan, PlannerError, plan
from .rules import Rule, RuleError, plan_to_dict, rules_from_plan
from .settings import ORG, load_settings, save_settings
from .theme import MUTED, QSS, SUN_DARK, shadow
from .workbook import Preview, SheetInfo, apply, inspect, output_path, preview, sheet_names, value_index

MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]


def resource(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for candidate in (base / "sunny" / "assets" / name, base / "assets" / name,
                      Path(__file__).resolve().parent / "assets" / name):
        if candidate.exists():
            return candidate
    return base / "assets" / name


class PlanWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, request: str, shape: dict, api_key: str, model: str):
        super().__init__()
        self.request, self.shape, self.api_key, self.model = request, shape, api_key, model

    def run(self) -> None:
        try:
            self.done.emit(plan(self.request, self.shape, api_key=self.api_key or None, model=self.model))
        except PlannerError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"{type(e).__name__}: {e}")


class DropLine(QLineEdit):
    """Read-only path field that accepts a dropped .xlsx."""

    dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Arrastra aquí un Excel (.xlsx) o pulsa ELEGIR…")

    def dragEnterEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):  # noqa: N802
        for u in e.mimeData().urls():
            if u.isLocalFile() and u.toLocalFile().lower().endswith((".xlsx", ".xlsm")):
                self.dropped.emit(u.toLocalFile())
                break
        e.acceptProposedAction()


class SettingsDialog(QDialog):
    def __init__(self, parent, api_key: str, model: str, use_model: bool):
        super().__init__(parent)
        self.setWindowTitle("Ajustes")
        form = QFormLayout(self)
        intro = QLabel("Sunny entiende las órdenes en español por sí sola, sin internet ni cuentas. "
                       "Si además quieres que las entienda Claude (frases más libres), activa esto y pon una clave.")
        intro.setObjectName("note")
        intro.setWordWrap(True)
        form.addRow(intro)
        self.use_model = QCheckBox("Usar Claude para entender la orden (opcional)")
        self.use_model.setChecked(use_model)
        form.addRow(self.use_model)
        self.key = QLineEdit(api_key)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("sk-ant-…")
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItems(MODELS)
        self.model.setCurrentText(model or DEFAULT_MODEL)
        form.addRow("Clave de la API de Anthropic", self.key)
        form.addRow("Modelo", self.model)
        note = QLabel("La clave se guarda en este equipo. Al modelo solo viajan los nombres de las "
                      "columnas y tu orden, nunca los datos de las celdas.")
        note.setObjectName("note")
        note.setWordWrap(True)
        form.addRow(note)
        self.use_model.toggled.connect(self.key.setEnabled)
        self.use_model.toggled.connect(self.model.setEnabled)
        self.key.setEnabled(use_model)
        self.model.setEnabled(use_model)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class Window(QMainWindow):
    def __init__(self, excel: str | None = None, request: str | None = None, sheet: str | None = None):
        super().__init__()
        self.qsettings = QSettings(ORG, APP_NAME)
        self.source: Path | None = None
        self.info: SheetInfo | None = None
        self.rules: list[Rule] = []
        self.previews: list[Preview] = []
        self.notes = ""
        self.worker: PlanWorker | None = None
        self.last_output: Path | None = None
        self.setWindowTitle(f"{APP_NAME} {APP_KANA}")
        self.setWindowIcon(QIcon(str(resource("sunny.ico"))))
        self.setMinimumSize(760, 700)
        self._build()
        geometry = self.qsettings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if excel:
            self._load(Path(excel), sheet)
        if request:
            self.request.setPlainText(request)
        self._refresh()

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        col = QVBoxLayout(root)
        col.setContentsMargins(24, 20, 24, 20)
        col.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel(APP_NAME.upper())
        title.setObjectName("title")
        kana = QLabel(APP_KANA)
        kana.setObjectName("kana")
        kicker = QLabel("FORMATO CONDICIONAL  ·  DICHO EN PALABRAS")
        kicker.setObjectName("kicker")
        version = QLabel(f"v{__version__}")
        version.setObjectName("version")
        block = QVBoxLayout()
        block.setSpacing(0)
        row_t = QHBoxLayout()
        row_t.setSpacing(12)
        row_t.addWidget(title)
        row_t.addWidget(kana, 0, Qt.AlignmentFlag.AlignBottom)
        row_t.addStretch()
        block.addLayout(row_t)
        block.addWidget(kicker)
        head.addLayout(block)
        head.addStretch()
        head.addWidget(version, 0, Qt.AlignmentFlag.AlignTop)
        col.addLayout(head)

        # 01 file
        panel, lay = self._panel("01 · ARCHIVO")
        row = QHBoxLayout()
        self.path = DropLine()
        self.path.dropped.connect(lambda p: self._load(Path(p)))
        self.btn_pick = self._button("Elegir…", self._pick)
        row.addWidget(self.path, 1)
        row.addWidget(self.btn_pick)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Hoja:"))
        self.sheet = QComboBox()
        self.sheet.currentTextChanged.connect(self._sheet_changed)
        row2.addWidget(self.sheet, 1)
        self.shape = QLabel("")
        self.shape.setObjectName("note")
        self.shape.setWordWrap(True)
        row2.addWidget(self.shape, 2)
        lay.addLayout(row2)
        col.addWidget(panel)

        # 02 request
        panel, lay = self._panel("02 · QUÉ QUIERES")
        self.request = QPlainTextEdit()
        self.request.setPlaceholderText(
            "Ejemplo: pinta de rojo las filas donde Estado sea PENDIENTE y de verde donde sea PAGADO; "
            "en negrita los Importes mayores de 50 mil; en gris lo que no tenga Factura.")
        self.request.setMaximumHeight(96)
        lay.addWidget(self.request)
        row = QHBoxLayout()
        self.btn_plan = QPushButton("ENTENDER")
        self.btn_plan.setObjectName("primary")
        self.btn_plan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plan.clicked.connect(self._plan)
        shadow(self.btn_plan, 4)
        row.addWidget(self.btn_plan)
        self.status = QLabel("")
        self.status.setObjectName("note")
        self.status.setWordWrap(True)
        row.addWidget(self.status, 1)
        self.btn_load = self._button("Cargar reglas…", self._load_rules)
        self.btn_save = self._button("Guardar reglas…", self._save_rules)
        row.addWidget(self.btn_load)
        row.addWidget(self.btn_save)
        lay.addLayout(row)
        col.addWidget(panel)

        # 03 rules
        panel, lay = self._panel("03 · LO QUE ENTENDÍ")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", "Regla", "Columna", "Pinta", "Alcanza"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(160)
        lay.addWidget(self.table, 1)
        self.notes_label = QLabel("")
        self.notes_label.setObjectName("note")
        self.notes_label.setWordWrap(True)
        lay.addWidget(self.notes_label)
        col.addWidget(panel, 1)

        # apply
        row = QHBoxLayout()
        self.btn_apply = QPushButton("APLICAR")
        self.btn_apply.setObjectName("primary")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.clicked.connect(self._apply)
        shadow(self.btn_apply, 5)
        row.addWidget(self.btn_apply)
        self.dest = QLineEdit()
        self.dest.setPlaceholderText("Se guarda como «<nombre> - Sunny.xlsx» junto al original")
        row.addWidget(self.dest, 1)
        self.btn_dest = self._button("Destino…", self._pick_dest)
        row.addWidget(self.btn_dest)
        self.btn_open = self._button("Abrir carpeta", self._open_folder)
        self.btn_open.setEnabled(False)
        row.addWidget(self.btn_open)
        col.addLayout(row)

        foot = QHBoxLayout()
        hint = QLabel("El original no se toca: Sunny escribe una copia con formato condicional de Excel, "
                      "que sigue vivo si cambian los datos.")
        hint.setObjectName("note")
        hint.setWordWrap(True)
        foot.addWidget(hint, 1)
        btn_settings = QPushButton("Ajustes")
        btn_settings.setObjectName("text")
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(self._settings)
        foot.addWidget(btn_settings)
        btn_about = QPushButton("Acerca de")
        btn_about.setObjectName("text")
        btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_about.clicked.connect(self._about)
        foot.addWidget(btn_about)
        col.addLayout(foot)

    def _panel(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow(panel)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        label = QLabel(title)
        label.setObjectName("section")
        lay.addWidget(label)
        return panel, lay

    def _button(self, text: str, slot) -> QPushButton:
        b = QPushButton(text.upper())
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    # ------------------------------------------------------------------ file
    def _pick(self) -> None:
        start = self.qsettings.value("folder", str(Path.home() / "Documents"))
        path, _ = QFileDialog.getOpenFileName(self, "Elegir Excel", str(start), "Excel (*.xlsx *.xlsm)")
        if path:
            self.qsettings.setValue("folder", str(Path(path).parent))
            self._load(Path(path))

    def _load(self, path: Path, sheet: str | None = None) -> None:
        try:
            names = sheet_names(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, f"No pude abrir el archivo:\n{e}")
            return
        self.source = path
        self.path.setText(str(path))
        self.sheet.blockSignals(True)
        self.sheet.clear()
        self.sheet.addItems(names)
        if sheet and sheet in names:
            self.sheet.setCurrentText(sheet)
        self.sheet.blockSignals(False)
        self.dest.setText(str(output_path(path)))
        self._sheet_changed()

    def _sheet_changed(self) -> None:
        if not self.source or not self.sheet.currentText():
            return
        try:
            self.info = inspect(self.source, self.sheet.currentText())
        except Exception as e:  # noqa: BLE001
            self.info = None
            self.shape.setText(f"✗ {e}")
            self._refresh()
            return
        rows = self.info.last_row - self.info.first_row + 1
        cols = ", ".join(c.header for c in self.info.columns)
        self.shape.setText(f"{rows} filas · {len(self.info.columns)} columnas: {cols}")
        if self.rules:
            self._preview()
        self._refresh()

    # ------------------------------------------------------------------ rules
    def _plan(self) -> None:
        if not self.info:
            return
        text = self.request.toPlainText().strip()
        if not text:
            return
        settings = load_settings()
        if settings.get("use_model"):
            if not settings.get("api_key"):
                QMessageBox.information(self, APP_NAME, "Para usar Claude hace falta la clave de la API. Ponla en Ajustes, "
                                        "o desactiva «Usar Claude» y Sunny entiende la orden por sí sola.")
                self._settings()
                return
            self.status.setText("Entendiendo…")
            self.worker = PlanWorker(text, self.info.describe(), settings["api_key"], settings.get("model") or DEFAULT_MODEL)
            self.worker.done.connect(self._planned)
            self.worker.failed.connect(self._plan_failed)
            self.worker.start()
            self._refresh()
            return
        parser = SpanishParser([c.header for c in self.info.columns], values=value_index(self.source, self.info))
        parsed = parser.parse(text)
        self.rules = parsed.rules
        self.notes = "\n".join(parsed.notes)
        extra = f"  ⚠ {len(parsed.notes)} sin entender" if parsed.notes else ""
        self.status.setText(f"{len(self.rules)} reglas{extra}")
        self._preview()
        self._refresh()

    def _planned(self, result: Plan) -> None:
        self.rules = result.rules
        self.notes = result.notes
        extra = f"  ⚠ {len(result.errors)} reglas descartadas" if result.errors else ""
        self.status.setText(f"{len(self.rules)} reglas{extra}")
        self._preview()
        self._refresh()

    def _plan_failed(self, message: str) -> None:
        self.status.setText("")
        QMessageBox.warning(self, APP_NAME, message)
        self._refresh()

    def _preview(self) -> None:
        self.table.setRowCount(0)
        self.previews = []
        if not (self.info and self.rules):
            self.notes_label.setText(self.notes)
            return
        try:
            self.previews = preview(self.source, self.info, self.rules)
        except RuleError as e:
            self.notes_label.setText(f"✗ {e}")
            return
        self.table.setRowCount(len(self.previews))
        for i, pv in enumerate(self.previews):
            check = QCheckBox()
            check.setChecked(pv.rule.enabled)
            check.toggled.connect(lambda on, r=pv.rule: setattr(r, "enabled", on))
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(6, 0, 6, 0)
            hl.addWidget(check, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 0, holder)
            self.table.setItem(i, 1, QTableWidgetItem(pv.rule.description or pv.rule.column))
            self.table.setItem(i, 2, QTableWidgetItem(pv.rule.column))
            swatch = QTableWidgetItem("  " + ("fila" if pv.rule.scope == "row" else "celda"))
            if pv.rule.style.fill:
                swatch.setBackground(QColor("#" + pv.rule.style.fill))
            if pv.rule.style.font_color:
                swatch.setForeground(QColor("#" + pv.rule.style.font_color))
            self.table.setItem(i, 3, swatch)
            unit = "filas" if pv.rule.scope == "row" else "celdas"
            count = QTableWidgetItem(f"{pv.cells} {unit}")
            count.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if pv.cells == 0:
                count.setForeground(QColor(MUTED))
            self.table.setItem(i, 4, count)
        self.notes_label.setText(self.notes)

    def _load_rules(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Cargar reglas", "", "Reglas (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.rules, self.notes, errors = rules_from_plan(data)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, f"No pude leer las reglas:\n{e}")
            return
        self.status.setText(f"{len(self.rules)} reglas de {Path(path).name}" + (f"  ⚠ {len(errors)} descartadas" if errors else ""))
        self._preview()
        self._refresh()

    def _save_rules(self) -> None:
        if not self.rules:
            return
        start = str(self.source.with_suffix(".reglas.json")) if self.source else ""
        path, _ = QFileDialog.getSaveFileName(self, "Guardar reglas", start, "Reglas (*.json)")
        if path:
            Path(path).write_text(json.dumps(plan_to_dict(self.rules, self.notes), ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ apply
    def _pick_dest(self) -> None:
        start = self.dest.text() or (str(output_path(self.source)) if self.source else "")
        path, _ = QFileDialog.getSaveFileName(self, "Guardar como", start, "Excel (*.xlsx)")
        if path:
            self.dest.setText(path)

    def _apply(self) -> None:
        if not (self.source and self.info and self.rules):
            return
        dest = Path(self.dest.text()) if self.dest.text().strip() else output_path(self.source)
        try:
            out = apply(self.source, self.info, self.rules, dest)
        except (RuleError, OSError) as e:
            QMessageBox.warning(self, APP_NAME, f"No se pudo guardar:\n{e}")
            return
        self.last_output = out
        self.btn_open.setEnabled(True)
        n = sum(1 for r in self.rules if r.enabled)
        self.status.setText(f"✓ {n} reglas escritas en {out.name}")

    def _open_folder(self) -> None:
        if self.last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output.parent)))

    def _refresh(self) -> None:
        busy = self.worker is not None and self.worker.isRunning()
        self.btn_plan.setEnabled(bool(self.info) and not busy)
        self.btn_apply.setEnabled(bool(self.info and self.rules) and not busy)
        self.btn_save.setEnabled(bool(self.rules))
        self.btn_load.setEnabled(bool(self.info) and not busy)

    # ------------------------------------------------------------------ misc
    def _settings(self) -> None:
        current = load_settings()
        dlg = SettingsDialog(self, current.get("api_key", ""), current.get("model", ""), bool(current.get("use_model")))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_settings(dlg.key.text().strip(), dlg.model.currentText().strip() or DEFAULT_MODEL, dlg.use_model.isChecked())

    def _about(self) -> None:
        QMessageBox.about(self, f"Acerca de {APP_NAME}", f"""
<h2 style="margin:0">{APP_NAME} <span style="color:{SUN_DARK}">{APP_KANA}</span> <small>v{__version__}</small></h2>
<p>Dices en palabras qué quieres resaltar en un Excel y Sunny lo convierte en formato condicional:
reglas que Excel sigue aplicando cuando cambian los datos. El original no se toca.</p>
<p>Las órdenes se entienden aquí mismo, en español, sin internet. Opcionalmente puede pedírselo a
<a href="https://www.anthropic.com/claude">Claude</a> (API de Anthropic, con tu clave); entonces solo viajan las cabeceras y la orden.</p>
<p><b>Créditos</b><br>
Diseño: estética Komi Store (papel y tinta).<br>
Excel: <a href="https://openpyxl.readthedocs.io/">openpyxl</a> (MIT).<br>
Interfaz: <a href="https://doc.qt.io/qtforpython-6/">Qt for Python / PySide6</a> (LGPL-3.0).<br>
Código fuente: <a href="{REPO_URL}">{REPO_URL}</a> (Apache 2.0).</p>
<p style="color:{MUTED};font-size:9pt">Touhou Project y sus personajes pertenecen a Team Shanghai Alice (ZUN);
obra de fans no oficial hecha según sus directrices para obras derivadas, sin afiliación ni respaldo.</p>
""")

    def closeEvent(self, e):  # noqa: N802
        self.qsettings.setValue("geometry", self.saveGeometry())
        super().closeEvent(e)


def run(excel: str | None = None, request: str | None = None, sheet: str | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    app.setWindowIcon(QIcon(str(resource("sunny.ico"))))
    window = Window(excel, request, sheet)
    window.show()
    return app.exec()
