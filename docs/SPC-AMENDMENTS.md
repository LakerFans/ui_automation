# SPC v2 修订说明（G1–G8 收口）

本文档对原 SPC 中 8 项不一致/待澄清项给出**正式决策**，作为实现的唯一依据。

## G1：`search keyword` 与 DSL 白名单

**决策**：将 `search` 纳入 DSL 白名单，定义为**复合语义动作**。

- Planner 可输出 `action: search`，字段 `target`（搜索框语义名）、`value`（关键词）
- Executor 将其展开为：`snapshot → fill(搜索框) → click(搜索按钮|press Enter)`
- §6.2 示例保持不变，无需改为 fill+click 手写链

## G2：DeepAgents vs LangGraph 双编排边界

**决策**：

| 层级 | 职责 | 生命周期 |
|------|------|----------|
| **Orchestrator（DeepAgents 风格）** | 跨用例调度、write_todos、Agent 委派、上下文压缩、资源配额 | 测试套件 / 批次 |
| **LangGraph** | 单用例状态机：INIT→PLAN→EXECUTE→ASSERT→RETRY→REPORT→END | 单次 Run |

LangGraph **不**负责多用例并行；Orchestrator **不**直接操作 browser ref。

## G3：Playwright 与 agent-browser 关系

**决策**：

- Layer4 **仅暴露 `BrowserAdapter` 接口**
- **主执行路径**：agent-browser CLI（底层 CDP，非 Playwright API）
- Playwright **不对外暴露**；若未来需要 HAR/网络拦截，作为 BrowserAdapter 内部特权扩展，仅 Executor 可调用

## G4：微服务 vs 单体 MVP

**决策**：Phase 0–2 采用**单体模块化包**（`src/ui_test_platform/`），按包边界预留拆分点：

- `orchestrator/` → orchestrator-service
- `agents/` → planner/executor/resolver/report services
- `browser/` → browser-worker

§11 微服务划分作为 Phase 3 目标，不在 MVP 强制拆分。

## G5：`browser_*` 命令命名

**决策**：平台内统一 **BrowserAdapter** 方法名；CLI 映射见 [appendix-b-browser-adapter.md](appendix-b-browser-adapter.md)。

| Adapter 方法 | agent-browser CLI |
|--------------|-------------------|
| `open(url)` | `open <url>` |
| `snapshot(interactive=True)` | `snapshot -i --json` |
| `click(ref)` | `click @eN` |
| `fill(ref, text)` | `fill @eN <text>` |
| `screenshot(path)` | `screenshot <path>` |
| `console()` | `console --json` |

Cursor MCP 的 `browser_*` 前缀通过同一 Adapter 的 `McpBrowserBackend` 实现（Phase 3）。

## G6：iframe / 动态路由 / 登录态

**决策**：LangGraph 增加 **BLOCKED** 状态与人机接管协议。

触发条件：

- snapshot 检测到 iframe 且目标元素不可达
- 登录页 / CAPTCHA / 权限拦截
- clarify 超过最大次数（见 G8）

BLOCKED 状态持久化 checkpoint，等待 `POST /runs/{id}/resume` 人工确认后继续或 abort。

## G7：Registry 与 Planner 接口

**决策**：REST + 内存索引双模式，契约见 [appendix-d-registry-api.md](appendix-d-registry-api.md)。

```
GET /semantics?url=<pattern>&term=<keyword>
GET /semantics/synonyms?term=<keyword>
GET /semantics/pages?url=<pattern>
```

Planner 规划阶段**必须**查询 Registry 同义词与页面模板。

## G8：confidence 与 clarify 阈值

**决策**（写入 Page Resolver 默认配置）：

| 参数 | 默认值 |
|------|--------|
| `confidence_threshold` | 0.85 |
| `max_clarify_attempts` | 2 |
| `ambiguous_top_k` | 3 |

- `confidence >= 0.85`：自动执行
- `0.60 <= confidence < 0.85`：clarify（二次 snapshot + 区域约束）
- `confidence < 0.60`：失败，进入 RETRY 或 BLOCKED

## AST Snapshot 策略

**决策**：每个**需要 ref 的原子动作**执行前强制 `snapshot -i`；`open`/`wait` 后亦强制 snapshot。Checkpoint 仅存 snapshot **摘要**（URL + ref 列表 + 步骤 outcome），不全量落库。
