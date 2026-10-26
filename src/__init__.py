"""Stateless CV generation agent package."""
import sys

# Safeguard against binary load failures (e.g. Windows Application Control blocking orjson.pyd)
try:
    import orjson  # noqa: F401
except ImportError:
    sys.modules["orjson"] = None
