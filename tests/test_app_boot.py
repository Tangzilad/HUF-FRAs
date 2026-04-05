from __future__ import annotations

import importlib


def test_app_boot_import_smoke() -> None:
    module = importlib.import_module("app.app")
    assert hasattr(module, "boot")
