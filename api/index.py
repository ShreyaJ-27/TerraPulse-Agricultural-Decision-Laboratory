"""Same-origin Vercel entry point for the TerraPulse API."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "science" / "src"))
os.environ["APP_ENV"] = "production"

from app.main import app  # noqa: E402, F401
