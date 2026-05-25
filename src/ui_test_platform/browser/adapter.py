from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ui_test_platform.config import settings


@dataclass
class RefEntry:
    ref: str
    role: str = ""
    name: str = ""
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass
class CommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    code: str = "OK"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotResult:
    url: str
    title: str
    refs: list[RefEntry]
    raw: str | dict
    has_iframe: bool = False


@dataclass
class ConsoleResult:
    logs: list[dict[str, Any]]
    raw: str


class BrowserAdapter(Protocol):
    session: str

    def open(self, url: str) -> CommandResult: ...
    def snapshot(self, interactive: bool = True) -> SnapshotResult: ...
    def click(self, ref: str) -> CommandResult: ...
    def fill(self, ref: str, text: str) -> CommandResult: ...
    def select(self, ref: str, value: str) -> CommandResult: ...
    def hover(self, ref: str) -> CommandResult: ...
    def scroll(self, direction: str, pixels: int | None = None) -> CommandResult: ...
    def wait(self, target: str) -> CommandResult: ...
    def press(self, key: str) -> CommandResult: ...
    def screenshot(self, path: str) -> CommandResult: ...
    def console(self, clear: bool = False) -> ConsoleResult: ...
    def close(self) -> CommandResult: ...


REF_LINE = re.compile(
    r"^(?P<ref>@[eE]\d+)\s*(?:\[(?P<role>[^\]]*)\])?\s*(?P<name>.*)$"
)


def parse_snapshot_text(text: str, url: str = "", title: str = "") -> SnapshotResult:
    refs: list[RefEntry] = []
    has_iframe = "iframe" in text.lower()
    for line in text.splitlines():
        m = REF_LINE.match(line.strip())
        if not m:
            if line.startswith("URL:"):
                url = line.split(":", 1)[1].strip()
            elif line.startswith("Page:"):
                title = line.split(":", 1)[1].strip()
            continue
        name = m.group("name").strip().strip('"')
        refs.append(
            RefEntry(ref=m.group("ref"), role=m.group("role") or "", name=name)
        )
    return SnapshotResult(url=url, title=title, refs=refs, raw=text, has_iframe=has_iframe)


class AgentBrowserBackend:
    def __init__(self, session: str) -> None:
        self.session = session
        self._bin = settings.agent_browser_bin

    def _run(self, *args: str, timeout: int | None = None) -> CommandResult:
        cmd = [self._bin, "--session", self.session, *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or settings.command_timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(ok=False, stderr=str(exc), code="TIMEOUT")
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            code = "IFRAME_BLOCKED" if "iframe" in stderr.lower() else "BROWSER_CMD_FAILED"
            return CommandResult(
                ok=False,
                stdout=proc.stdout,
                stderr=stderr,
                code=code,
            )
        return CommandResult(ok=True, stdout=proc.stdout, stderr=proc.stderr)

    def open(self, url: str) -> CommandResult:
        return self._run("open", url)

    def snapshot(self, interactive: bool = True) -> SnapshotResult:
        args = ["snapshot"]
        if interactive:
            args.append("-i")
        args.extend(["--json"])
        result = self._run(*args)
        if not result.ok:
            return SnapshotResult(url="", title="", refs=[], raw=result.stderr, has_iframe=False)
        try:
            data = json.loads(result.stdout)
            refs = [
                RefEntry(
                    ref=item.get("ref", ""),
                    role=item.get("role", ""),
                    name=item.get("name", "") or item.get("text", ""),
                )
                for item in data.get("refs", data.get("elements", []))
            ]
            return SnapshotResult(
                url=data.get("url", ""),
                title=data.get("title", data.get("page", "")),
                refs=refs,
                raw=data,
                has_iframe=data.get("has_iframe", False),
            )
        except json.JSONDecodeError:
            return parse_snapshot_text(result.stdout)

    def click(self, ref: str) -> CommandResult:
        return self._run("click", ref)

    def fill(self, ref: str, text: str) -> CommandResult:
        return self._run("fill", ref, text)

    def select(self, ref: str, value: str) -> CommandResult:
        return self._run("select", ref, value)

    def hover(self, ref: str) -> CommandResult:
        return self._run("hover", ref)

    def scroll(self, direction: str, pixels: int | None = None) -> CommandResult:
        args = ["scroll", direction]
        if pixels is not None:
            args.append(str(pixels))
        return self._run(*args)

    def wait(self, target: str) -> CommandResult:
        return self._run("wait", target)

    def press(self, key: str) -> CommandResult:
        return self._run("press", key)

    def screenshot(self, path: str) -> CommandResult:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return self._run("screenshot", path)

    def console(self, clear: bool = False) -> ConsoleResult:
        args = ["console", "--json"]
        if clear:
            args.insert(1, "--clear")
        result = self._run(*args)
        if not result.ok:
            return ConsoleResult(logs=[], raw=result.stderr)
        try:
            data = json.loads(result.stdout)
            logs = data if isinstance(data, list) else data.get("logs", [])
            return ConsoleResult(logs=logs, raw=result.stdout)
        except json.JSONDecodeError:
            return ConsoleResult(logs=[], raw=result.stdout)

    def close(self) -> CommandResult:
        return self._run("close")


class MockBrowserBackend:
    """In-memory browser for tests and CI without a real browser."""

    def __init__(self, session: str) -> None:
        self.session = session
        self._url = "https://example.com/login"
        self._refs = [
            RefEntry(ref="@e1", role="heading", name="Log in"),
            RefEntry(ref="@e2", role="input", name="用户名"),
            RefEntry(ref="@e3", role="input", name="密码"),
            RefEntry(ref="@e4", role="button", name="登录按钮"),
            RefEntry(ref="@e5", role="button", name="新增"),
            RefEntry(ref="@e6", role="input", name="搜索框"),
        ]

    def open(self, url: str) -> CommandResult:
        self._url = url
        return CommandResult(ok=True, data={"url": url})

    def snapshot(self, interactive: bool = True) -> SnapshotResult:
        return SnapshotResult(
            url=self._url,
            title="Mock Page",
            refs=list(self._refs),
            raw={"url": self._url, "refs": [r.__dict__ for r in self._refs]},
            has_iframe=False,
        )

    def click(self, ref: str) -> CommandResult:
        if ref not in {r.ref for r in self._refs}:
            return CommandResult(ok=False, code="REF_STALE", stderr=f"ref {ref} stale")
        if self._url.endswith("/login"):
            self._url = "https://example.com/dashboard"
        return CommandResult(ok=True)

    def fill(self, ref: str, text: str) -> CommandResult:
        if ref not in {r.ref for r in self._refs}:
            return CommandResult(ok=False, code="REF_STALE", stderr=f"ref {ref} stale")
        return CommandResult(ok=True)

    def select(self, ref: str, value: str) -> CommandResult:
        return self.fill(ref, value)

    def hover(self, ref: str) -> CommandResult:
        return CommandResult(ok=True)

    def scroll(self, direction: str, pixels: int | None = None) -> CommandResult:
        return CommandResult(ok=True)

    def wait(self, target: str) -> CommandResult:
        return CommandResult(ok=True)

    def press(self, key: str) -> CommandResult:
        return CommandResult(ok=True)

    def screenshot(self, path: str) -> CommandResult:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x89PNG\r\n")
        return CommandResult(ok=True)

    def console(self, clear: bool = False) -> ConsoleResult:
        return ConsoleResult(logs=[], raw="[]")

    def close(self) -> CommandResult:
        return CommandResult(ok=True)


def create_browser(session: str) -> BrowserAdapter:
    if settings.browser_backend == "mock":
        return MockBrowserBackend(session)
    return AgentBrowserBackend(session)
