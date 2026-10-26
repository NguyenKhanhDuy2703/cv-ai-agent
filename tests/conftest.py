import os
import sys

import pytest

os.environ["LLM_RETRY_MIN_WAIT"] = "0.001"
os.environ["LLM_RETRY_MAX_WAIT"] = "0.005"

# Ensure pytest runs smoothly even if OS policy blocks binary orjson.pyd
try:
    import orjson  # noqa: F401
except ImportError:
    sys.modules["orjson"] = None


@pytest.fixture
def canonical_en_document():
    from tests.helpers import load_canonical_fixture

    return load_canonical_fixture("en.v1.json")["document"]


@pytest.fixture
def candidate_profile():
    from src.schemas.generation import CandidateProfile
    from tests.helpers import request_payload

    return CandidateProfile.model_validate(request_payload()["profile"])

