from __future__ import annotations

import importlib
from pathlib import Path

EXPECTED_PAGES = ["Start here", "CIP basis", "Cross-currency", "Short-rate FRA", "Risk P&L", "Stress Lab"]


def test_app_boot_import_smoke() -> None:
    module = importlib.import_module("app.app")
    assert hasattr(module, "boot")


def test_router_reachability_contains_all_pages_with_callables() -> None:
    module = importlib.import_module("app.app")
    routes = module.PAGE_ROUTES

    assert list(routes.keys()) == EXPECTED_PAGES
    assert all(callable(handler) for handler in routes.values())


def test_page_import_smoke_and_package_exports() -> None:
    risk_pnl = importlib.import_module("app.pages.risk_pnl")
    stress_lab = importlib.import_module("app.pages.stress_lab")
    pages = importlib.import_module("app.pages")

    assert hasattr(risk_pnl, "render")
    assert hasattr(stress_lab, "render")
    assert hasattr(pages, "render_risk_pnl_page")
    assert hasattr(pages, "render_stress_lab_page")


def test_set_page_config_only_in_app_entrypoint_for_routed_pages() -> None:
    routed_page_files = [
        Path("app/pages/home.py"),
        Path("app/pages/cip_page.py"),
        Path("app/pages/cross_currency_page.py"),
        Path("app/pages/short_rate_page.py"),
        Path("app/pages/risk_pnl.py"),
        Path("app/pages/stress_lab.py"),
    ]

    offenders: list[str] = []
    for page_file in routed_page_files:
        text = page_file.read_text(encoding="utf-8")
        if "set_page_config" in text:
            offenders.append(str(page_file))

    assert offenders == []

    module = importlib.import_module("app.app")
    app_module_file = module.__file__
    assert app_module_file is not None
    app_source = Path(app_module_file).read_text(encoding="utf-8")
    assert "set_page_config" in app_source
