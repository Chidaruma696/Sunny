"""Komi look in Qt: paper and ink, square corners, thick borders, hard shadows. Sunny palette (sunlight)."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

PAPER = "#FFF8E6"
INK = "#2B1D08"
SUN = "#F0A020"
SUN_DARK = "#D4860A"
LIGHT = "#FFE9B8"
LIGHT_DARK = "#FFD070"
MUTED = "#8A7657"
DANGER = "#C8402E"

QSS = f"""
* {{
    font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10.5pt;
    color: {INK};
}}
QMainWindow, QDialog, QMessageBox, QWidget#root {{ background: {PAPER}; }}
QLabel#title {{ font-size: 28pt; font-weight: 900; letter-spacing: 3px; }}
QLabel#kana {{ font-size: 16pt; font-weight: 700; color: {SUN_DARK}; }}
QLabel#kicker {{ font-size: 8.5pt; font-weight: 700; letter-spacing: 3px; color: {SUN_DARK}; }}
QLabel#version {{ font-size: 8.5pt; color: {MUTED}; }}
QLabel#section {{ font-size: 9pt; font-weight: 800; letter-spacing: 2px; }}
QLabel#note {{ color: {MUTED}; font-size: 9pt; }}
QLabel#error {{ color: {DANGER}; font-weight: 700; }}

QFrame#panel {{ background: #FFFFFF; border: 2px solid {INK}; border-radius: 0; }}

QPushButton {{
    background: #FFFFFF; color: {INK};
    border: 2px solid {INK}; border-radius: 0;
    padding: 6px 14px; font-weight: 700;
}}
QPushButton:hover {{ background: {LIGHT}; }}
QPushButton:pressed {{ background: {LIGHT_DARK}; }}
QPushButton:disabled {{ color: #A89A80; border-color: #D6C9AE; background: #FBF6EA; }}
QPushButton#primary {{ background: {SUN}; color: {INK}; font-size: 12.5pt; padding: 10px 28px; letter-spacing: 2px; }}
QPushButton#primary:hover {{ background: {SUN_DARK}; }}
QPushButton#primary:pressed {{ background: {INK}; color: #FFFFFF; }}
QPushButton#primary:disabled {{ background: #D6C9AE; color: #FFFFFF; border-color: #D6C9AE; }}
QPushButton#text {{ border: none; background: transparent; text-decoration: underline; padding: 2px 4px; }}
QPushButton#text:hover {{ color: {SUN_DARK}; }}

QListWidget, QPlainTextEdit, QLineEdit, QComboBox, QTableWidget {{
    background: #FFFFFF; border: 2px solid {INK}; border-radius: 0; padding: 4px;
    selection-background-color: {LIGHT_DARK}; selection-color: {INK};
}}
QListWidget::item {{ padding: 4px 6px; }}
QListWidget::item:selected {{ background: {LIGHT_DARK}; color: {INK}; }}
QLineEdit:disabled, QPlainTextEdit:disabled {{ color: #A89A80; background: #FBF6EA; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: #FFFFFF; border: 2px solid {INK}; selection-background-color: {LIGHT_DARK}; }}
QTableWidget {{ gridline-color: #E8DCC2; }}
QHeaderView::section {{ background: {LIGHT}; border: none; border-bottom: 2px solid {INK}; padding: 4px; font-weight: 800; }}

QProgressBar {{
    border: 2px solid {INK}; border-radius: 0; background: #FFFFFF;
    text-align: center; font-weight: 700; height: 22px;
}}
QProgressBar::chunk {{ background: {SUN}; }}

QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 2px solid {INK}; border-radius: 0; background: #FFFFFF;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {SUN}; }}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{ border-color: #D6C9AE; }}

QScrollBar:vertical {{ background: {LIGHT}; width: 12px; border: none; }}
QScrollBar::handle:vertical {{ background: {INK}; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {LIGHT}; height: 12px; border: none; }}
QScrollBar::handle:horizontal {{ background: {INK}; min-width: 24px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{ background: {INK}; color: #FFFFFF; border: none; padding: 4px 6px; }}
"""


def shadow(widget: QWidget, offset: int = 4) -> None:
    """Hard shadow (no blur), Komi style."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(0)
    effect.setOffset(offset, offset)
    effect.setColor(QColor(INK))
    widget.setGraphicsEffect(effect)
