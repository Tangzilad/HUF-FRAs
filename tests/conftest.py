from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.state import build_state


@pytest.fixture()
def app_payload() -> dict:
    """Representative deterministic payload for app-level pipeline tests."""

    return build_state()


@pytest.fixture()
def app_payload_with_shifted_spot() -> dict:
    payload = build_state()
    payload["cip"]["spot"] = [x + 0.5 for x in payload["cip"]["spot"]]
    return payload
