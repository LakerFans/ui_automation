# 附录 B：BrowserAdapter 契约

实现：`src/ui_test_platform/browser/adapter.py`

## 1. 接口

```python
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
```

## 2. CLI 映射（AgentBrowserBackend）

| Adapter | CLI 命令 |
|---------|----------|
| `open(url)` | `agent-browser --session {s} open {url}` |
| `snapshot(True)` | `agent-browser --session {s} snapshot -i --json` |
| `click(ref)` | `agent-browser --session {s} click {ref}` |
| `fill(ref, text)` | `agent-browser --session {s} fill {ref} {text}` |
| `select(ref, val)` | `agent-browser --session {s} select {ref} {val}` |
| `hover(ref)` | `agent-browser --session {s} hover {ref}` |
| `scroll(dir, px)` | `agent-browser --session {s} scroll {dir} [px]` |
| `wait(ms)` | `agent-browser --session {s} wait {ms}` |
| `press(key)` | `agent-browser --session {s} press {key}` |
| `screenshot(path)` | `agent-browser --session {s} screenshot {path}` |
| `console()` | `agent-browser --session {s} console --json` |
| `close()` | `agent-browser --session {s} close` |

全局选项：`--json` 追加到需要结构化输出的命令。

## 3. Session 模型

- 每个 Run 分配唯一 `session = run_{run_id}`
- `browser_state` 持久化：`{ "session": "...", "last_url": "..." }`
- 恢复 Run 时复用同一 session 名（agent-browser 进程需仍存活；否则 re-open last_url）

## 4. 错误码

| code | 含义 | 处理 |
|------|------|------|
| `BROWSER_CMD_FAILED` | CLI 非零退出 | RETRY |
| `REF_STALE` | ref 不在最新 snapshot | 重新 snapshot + resolve |
| `IFRAME_BLOCKED` | 目标在 iframe 内不可达 | BLOCKED |
| `URL_NOT_ALLOWED` | 超出环境白名单 | 立即失败 |
| `TIMEOUT` | 命令超时 | RETRY |

## 5. Snapshot 数据结构

```python
@dataclass
class SnapshotResult:
    url: str
    title: str
    refs: list[RefEntry]  # ref, role, name, attrs
    raw: str | dict
    has_iframe: bool
```

`RefEntry.ref` 格式：`@e1`, `@e2`, …（与 agent-browser 一致）

## 6. MockBackend

测试与无浏览器 CI 使用 `MockBrowserBackend`，返回固定 snapshot tree，不调用 CLI。
