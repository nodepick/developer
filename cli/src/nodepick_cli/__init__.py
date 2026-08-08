import importlib.metadata

try:
    __version__ = importlib.metadata.version("nodepick-cli")
except Exception:
    __version__ = "0.1.0"

from .main import app

__all__ = ["app", "__version__"]

