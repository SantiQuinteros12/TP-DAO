"""Configuración de la aplicación (sobrescribible por variables de entorno)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

RUTA_DB = os.getenv("BIBLIOTECA_DB", str(BASE_DIR / "data" / "biblioteca.db"))

ORIGENES_CORS = os.getenv(
    "BIBLIOTECA_CORS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
