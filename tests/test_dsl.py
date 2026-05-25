from __future__ import annotations

import pytest

from ui_test_platform.dsl.compiler import DSLCompiler
from ui_test_platform.dsl.models import ActionStep


def test_compile_search_expands_to_fill_and_submit():
    compiler = DSLCompiler()
    steps = [
        ActionStep(action="search", target="搜索框", value="keyword", intent="搜索"),
    ]
    ast = compiler.compile(steps)
    actions = [c.action for c in ast.children]
    assert actions == ["fill", "press_enter"]


def test_illegal_action_rejected():
    compiler = DSLCompiler()
    step = ActionStep.model_construct(action="eval_js", url="https://x.com")
    with pytest.raises(ValueError, match="Illegal action"):
        compiler.compile([step])


def test_open_requires_url():
    with pytest.raises(ValueError):
        ActionStep(action="open")
