"""Punto de entrada para Render / gunicorn (evita rutas con espacio en APP hecha)."""

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "APP hecha"
sys.path.insert(0, str(APP_DIR))

from server import app  # noqa: E402
