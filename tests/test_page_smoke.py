from __future__ import annotations

import sys
from types import SimpleNamespace

import app.pages.home as home
import app.pages.risk_pnl as risk_pnl
from app.pages import stress_lab


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict = {}
        self.messages: list[str] = []

    def title(self, *args, **kwargs):
        return None

    def subheader(self, *args, **kwargs):
        return None

    def caption(self, *args, **kwargs):
        return None

    def write(self, message=None, *args, **kwargs):
        if message is not None:
            self.messages.append(str(message))
        return None

    def info(self, message=None, *args, **kwargs):
        if message is not None:
            self.messages.append(str(message))
        return None

    def markdown(self, message=None, *args, **kwargs):
        if message is not None:
            self.messages.append(str(message))
        return None

    def json(self, *args, **kwargs):
        return None

    def dataframe(self, *args, **kwargs):
        return None

    def bar_chart(self, *args, **kwargs):
        return None

    def line_chart(self, *args, **kwargs):
        return None

    def metric(self, *args, **kwargs):
        return None

    def divider(self, *args, **kwargs):
        return None

    def expander(self, *args, **kwargs):
        return _Ctx()

    def columns(self, n, *args, **kwargs):
        count = n if isinstance(n, int) else len(n)
        return [_Ctx() for _ in range(count)]

    def selectbox(self, label, options, index=0, *args, **kwargs):
        return options[index]

    def slider(self, label, min_value=None, max_value=None, value=None, *args, **kwargs):
        return value

    def number_input(self, label, min_value=None, max_value=None, value=None, *args, **kwargs):
        return value


def test_risk_and_stress_render_smoke_with_defaults(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(risk_pnl, "st", fake_st)

    risk_pnl.render({})

    fake_streamlit_module = SimpleNamespace(**{k: getattr(fake_st, k) for k in dir(fake_st) if not k.startswith("__")})
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit_module)

    stress_lab.render({})


def test_home_learning_mode_references_path_and_progression(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(home, "st", fake_st)

    home.render({"explanation_mode": "learning"})

    rendered = " ".join(fake_st.messages)

    assert "Suggested path:" in rendered
    assert "CIP basis → Cross-currency → Short-rate FRA" in rendered
    assert "Work in sequence" in rendered
    assert "Start with" in rendered
    assert "then move to" in rendered
    assert "once market structure is clear" in rendered
