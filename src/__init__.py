"""Independent CV generation service with durable AI-owned jobs."""
import sys

# Safeguard against binary load failures (e.g. Windows Application Control blocking orjson.pyd)
try:
    import orjson  # noqa: F401
except ImportError:
    sys.modules["orjson"] = None
