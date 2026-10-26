import os
import sys

os.environ["LLM_RETRY_MIN_WAIT"] = "0.001"
os.environ["LLM_RETRY_MAX_WAIT"] = "0.005"

# Ensure pytest runs smoothly even if OS policy blocks binary orjson.pyd
try:
    import orjson  # noqa: F401
except ImportError:
    sys.modules["orjson"] = None

