from __future__ import annotations

from ui_test_platform.agents.resolver import PageResolver
from ui_test_platform.browser.adapter import RefEntry, SnapshotResult
from ui_test_platform.registry.store import SemanticRegistry


def test_resolver_finds_login_button():
    reg = SemanticRegistry()
    resolver = PageResolver(reg)
    snap = SnapshotResult(
        url="https://example.com/login",
        title="Login",
        refs=[
            RefEntry(ref="@e1", name="用户名"),
            RefEntry(ref="@e2", name="登录按钮"),
        ],
        raw="",
    )
    result = resolver.resolve("click", "登录按钮", snap)
    assert result.status == "Resolved"
    assert result.resolved_ref == "@e2"
    assert result.confidence >= 0.85


def test_resolver_synonym_match():
    reg = SemanticRegistry()
    resolver = PageResolver(reg)
    snap = SnapshotResult(
        url="https://example.com/users",
        title="Users",
        refs=[RefEntry(ref="@e5", name="新增")],
        raw="",
    )
    result = resolver.resolve("click", "新建", snap)
    assert result.resolved_ref == "@e5"
