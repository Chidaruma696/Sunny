# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: folder dist/Sunny with Sunny.exe (no console) and the assets.

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[("sunny/assets", "sunny/assets")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "numpy", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtNetwork",
              "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml",
              "PySide6.QtDBus", "PySide6.QtConcurrent", "PySide6.QtPrintSupport", "PySide6.QtSvg", "PySide6.QtSvgWidgets",
              "PySide6.QtQuick3D", "PySide6.QtQuickControls2", "PySide6.QtQuickTest"],
    noarchive=False,
)


def _dead_weight(dest: str) -> bool:
    """Qt ballast a widgets app never uses: software OpenGL (20 MB) and translations."""
    d = dest.replace("\\", "/").lower()
    return "opengl32sw" in d or "/translations/" in d or d.startswith("numpy")


a.binaries = [b for b in a.binaries if not _dead_weight(b[0])]
a.datas = [d for d in a.datas if not _dead_weight(d[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Sunny",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="sunny/assets/sunny.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Sunny",
)
