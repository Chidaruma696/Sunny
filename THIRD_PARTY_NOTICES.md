# Third-party notices

Sunny is distributed under Apache 2.0 (see `LICENSE`). It includes or uses the following third-party software:

| Component | Use | License |
|---|---|---|
| [Qt for Python (PySide6)](https://doc.qt.io/qtforpython-6/) and [Qt](https://www.qt.io/) | Graphical interface | LGPL-3.0. The Qt libraries ship as separate DLLs inside the installation folder, so they can be replaced with other versions. |
| [openpyxl](https://openpyxl.readthedocs.io/) | Reading and writing .xlsx files, conditional formatting | MIT |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | Client for the Claude API, which turns the request into rules | MIT |
| [PyInstaller](https://pyinstaller.org/) | Packaging the executable (not part of the final program) | GPL-2.0 with an exception for the generated executables |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | Building the installer | Inno Setup License |
| [Pillow](https://python-pillow.org/) | Only to generate the icon (`tools/make_icon.py`) | MIT-CMU |

The interface design follows the look of Komi Store (paper and ink, square corners, hard shadows).

Touhou Project and its characters belong to Team Shanghai Alice (ZUN); unofficial fan work made under their guidelines for derivative works, with no affiliation or endorsement.
