# Verification Audit — 2026-04-05

Scope: Validate the requested product-level checks against the current repository state.

## 1) Sidebar controls trigger full recomputation chain

**Status:** Gap identified.

There is no `app/` tree and no web UI framework wiring (for example Streamlit/Dash sidebar controls) in this repository snapshot. The runnable interfaces are CLI (`fra_simulation.py`, `scripts/explain.py`) plus notebooks.

## 2) Required pages reachable from one unified app shell

**Status:** Gap identified.

No unified app shell exists in the current codebase. Documentation and workflows are organized through Markdown guides and notebooks, not routed app pages.

## 3) Reuse of existing analytics in `src/` vs reimplementation in `app/`

**Status:** Confirmed for current architecture.

There is no `app/` implementation that duplicates analytics. Execution entrypoints import and call packaged logic from `src/` (for example explainers and risk/curve/model analytics), which indicates reuse of canonical module code rather than shadow implementations.

## 4) Learning mode coverage across core charts/tables

**Status:** Partially covered (non-UI).

Learning coverage exists through the explainer layer and CLI topics (`parametric`, `short-rate`, `cross-currency`, `cip`, `risk`, `all`). This covers core analytics domains in narrative form, but there is no app-level "learning mode" toggle over UI charts/tables because a chart/table app shell is not present.

## 5) Export validation for base and stressed outputs

**Status:** Confirmed.

A regression test now validates CSV exports for both a base dataset and a stressed scenario dataset using shared export helpers and scenario pipelines.

## 6) Docs reflect architecture and run instructions exactly

**Status:** Updated by this audit.

This audit explicitly documents that the repository is currently package/CLI/notebook driven, not a unified page-based application shell.

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
