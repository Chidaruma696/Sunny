"""PyInstaller entry point (avoids the relative imports of sunny/__main__.py)."""

import sys

from sunny.cli import main

sys.exit(main())
