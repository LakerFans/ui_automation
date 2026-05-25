from __future__ import annotations

import re
import uuid
from typing import Any

from ui_test_platform.dsl.models import ActionStep, IntentEntry, TestPlan, SCHEMA_VERSION
from ui_test_platform.registry.store import registry


class PlannerAgent:
    """Rule-based planner for MVP; structured for LLM swap-in."""

    def plan(
        self,
        natural_language: str,
        *,
        history: dict[str, Any] | None = None,
        base_url: str = "https://example.com",
    ) -> TestPlan:
        text = natural_language.strip()
        intents: list[IntentEntry] = []
        steps: list[ActionStep] = []

        if history and history.get("remaining_steps"):
            return TestPlan(
                task=history.get("task", text),
                intents=history.get("intents", []),
                steps=[ActionStep(**s) for s in history["remaining_steps"]],
            )

        if self._mentions_login(text):
            intents.extend(
                [
                    IntentEntry(intent_id="i1", text="打开登录页"),
                    IntentEntry(intent_id="i2", text="输入用户名"),
                    IntentEntry(intent_id="i3", text="输入密码"),
                    IntentEntry(intent_id="i4", text="点击登录"),
                    IntentEntry(intent_id="i5", text="验证登录成功"),
                ]
            )
            steps.extend(
                [
                    ActionStep(
                        intent_id="i1",
                        intent="打开登录页",
                        action="open",
                        url=f"{base_url.rstrip('/')}/login",
                    ),
                    ActionStep(
                        intent_id="i2",
                        intent="输入用户名",
                        action="fill",
                        target=self._resolve_field("用户名"),
                        value="admin",
                    ),
                    ActionStep(
                        intent_id="i3",
                        intent="输入密码",
                        action="fill",
                        target=self._resolve_field("密码"),
                        value="password",
                    ),
                    ActionStep(
                        intent_id="i4",
                        intent="点击登录",
                        action="click",
                        target=self._resolve_field("登录按钮"),
                    ),
                    ActionStep(
                        intent_id="i5",
                        intent="验证登录成功",
                        action="assert",
                        assert_type="url_assert",
                        value="/dashboard",
                    ),
                ]
            )
            return TestPlan(schema_version=SCHEMA_VERSION, task=text, intents=intents, steps=steps)

        if self._mentions_add_user(text):
            intents = [
                IntentEntry(intent_id="i1", text="打开用户管理"),
                IntentEntry(intent_id="i2", text="点击新增"),
                IntentEntry(intent_id="i3", text="填写用户名"),
                IntentEntry(intent_id="i4", text="填写手机号"),
                IntentEntry(intent_id="i5", text="提交"),
                IntentEntry(intent_id="i6", text="验证新增成功"),
            ]
            steps = [
                ActionStep(
                    intent_id="i1",
                    intent="打开用户管理",
                    action="open",
                    url=f"{base_url.rstrip('/')}/users",
                ),
                ActionStep(intent_id="i2", intent="点击新增", action="click", target="新增"),
                ActionStep(
                    intent_id="i3",
                    intent="填写用户名",
                    action="fill",
                    target="用户名",
                    value="test_user",
                ),
                ActionStep(
                    intent_id="i4",
                    intent="填写手机号",
                    action="fill",
                    target="手机号",
                    value="13800000000",
                ),
                ActionStep(intent_id="i5", intent="提交", action="click", target="提交"),
                ActionStep(
                    intent_id="i6",
                    intent="验证新增成功",
                    action="assert",
                    assert_type="text_assert",
                    value="新增成功",
                ),
            ]
            return TestPlan(schema_version=SCHEMA_VERSION, task=text, intents=intents, steps=steps)

        if self._mentions_delete(text):
            keyword = self._extract_keyword(text) or "test"
            intents = [
                IntentEntry(intent_id="i1", text="打开用户管理"),
                IntentEntry(intent_id="i2", text="搜索关键词"),
                IntentEntry(intent_id="i3", text="点击删除"),
                IntentEntry(intent_id="i4", text="确认删除"),
                IntentEntry(intent_id="i5", text="验证删除成功"),
            ]
            steps = [
                ActionStep(
                    intent_id="i1",
                    intent="打开用户管理",
                    action="open",
                    url=f"{base_url.rstrip('/')}/users",
                ),
                ActionStep(
                    intent_id="i2",
                    intent="搜索关键词",
                    action="search",
                    target="搜索框",
                    value=keyword,
                ),
                ActionStep(intent_id="i3", intent="点击删除", action="click", target="删除", risk_confirmed=False),
                ActionStep(intent_id="i4", intent="确认删除", action="click", target="确认", risk_confirmed=False),
                ActionStep(
                    intent_id="i5",
                    intent="验证删除成功",
                    action="assert",
                    assert_type="text_assert",
                    value="删除成功",
                ),
            ]
            return TestPlan(schema_version=SCHEMA_VERSION, task=text, intents=intents, steps=steps)

        # Generic fallback: open base + snapshot
        i1 = IntentEntry(intent_id="i1", text="打开页面")
        steps = [
            ActionStep(intent_id="i1", intent="打开页面", action="open", url=base_url),
            ActionStep(intent="页面快照", action="snapshot"),
        ]
        return TestPlan(schema_version=SCHEMA_VERSION, task=text, intents=[i1], steps=steps)

    def replan(
        self,
        plan: TestPlan,
        failed_index: int,
        error: str,
    ) -> TestPlan:
        """Replan only unexecuted steps (anti-drift)."""
        remaining = [s.model_dump() for s in plan.steps[failed_index:]]
        return self.plan(
            plan.task,
            history={"task": plan.task, "intents": [i.model_dump() for i in plan.intents], "remaining_steps": remaining},
        )

    def _resolve_field(self, term: str) -> str:
        return term

    def _mentions_login(self, text: str) -> bool:
        return bool(re.search(r"登录|login", text, re.I))

    def _mentions_add_user(self, text: str) -> bool:
        return bool(re.search(r"新增用户|添加用户|create user", text, re.I))

    def _mentions_delete(self, text: str) -> bool:
        return bool(re.search(r"删除", text))

    def _extract_keyword(self, text: str) -> str | None:
        m = re.search(r"搜索\s*['\"]?(\w+)['\"]?", text)
        return m.group(1) if m else None
