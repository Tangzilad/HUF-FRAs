# Verification Audit — 2026-04-05

Scope: Validate the requested product-level checks against the current repository state.

> **Update note (same date):** The repository now includes a routed Streamlit shell under `app/` with active pages `Start here`, `CIP basis`, `Cross-currency`, and `Short-rate FRA`. Statements below that claim no app shell is present are superseded.

## 1) Sidebar controls trigger full recomputation chain

**Status:** Gap identified.

This section is superseded by the current `app/` implementation (`app/app.py`, `app/widgets.py`), which includes Streamlit sidebar controls and routed pages.

## 2) Required pages reachable from one unified app shell

**Status:** Gap identified.

This section is superseded. A unified app shell exists in `app/app.py` with routed live pages (`Start here`, `CIP basis`, `Cross-currency`, `Short-rate FRA`).

## 3) Reuse of existing analytics in `src/` vs reimplementation in `app/`

**Status:** Confirmed for current architecture.

Routed pages in `app/pages/` call analytics modules from `src/` (for example CIP, cross-currency, and short-rate workflows), maintaining reuse of canonical package logic.

## 4) Learning mode coverage across core charts/tables

**Status:** Partially covered (non-UI).

Learning coverage exists through page-level explainers and an app-level mode toggle (`Basic`/`Learning`) surfaced in sidebar controls.

## 5) Export validation for base and stressed outputs

**Status:** Confirmed.

A regression test now validates CSV exports for both a base dataset and a stressed scenario dataset using shared export helpers and scenario pipelines.

## 6) Docs reflect architecture and run instructions exactly

**Status:** Updated by this audit.

Documentation should treat `app/app.py` as the canonical UI entrypoint and describe only the currently routed pages unless additional pages are explicitly wired.

## 7) Known gaps/limitations and follow-up tasks

### Gaps / limitations
1. Missing unified application shell and page routing.
2. Missing sidebar-driven recomputation workflow.
3. Missing explicit UI-level learning mode across charts/tables.

### Follow-up task mapping
1. **Build app shell:** Create `app/` shell with top-level navigation and page registry.
2. **Wire controls to recomputation:** Define centralized state + dependency graph so sidebar control updates recompute downstream artifacts.
3. **Learning mode UX:** Add learn/expert mode toggle and per-chart/table explanatory overlays backed by `src/explainers`.
4. **Export surface in app:** Add UI export actions for base and stressed artifacts, reusing existing `save_dataframe`/pipeline outputs.
5. **Acceptance test suite:** Add end-to-end tests for page reachability, recomputation triggers, learning-mode coverage, and export parity.
