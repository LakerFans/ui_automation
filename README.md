# UI Agent Test Platform

基于 Agent-Browser 的多 Agent UI 自动化测试平台（Phase 0–2 实现）。

## 架构

```
Planner → DSL Compiler → LangGraph → Executor → Page Resolver → BrowserAdapter → agent-browser CLI
```

- **Orchestrator**：跨用例调度与上下文压缩（`orchestrator/context.py`）
- **LangGraph**：单用例状态机（`graph/workflow.py`）
- **Registry**：UI 语义注册中心（`registry/`）

详见 [docs/SPC-AMENDMENTS.md](docs/SPC-AMENDMENTS.md) 与附录 A–D。

## 快速开始

```bash
cd ui-agent-test-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Mock 浏览器模式（默认，无需真实浏览器）
pytest

# 启动 API
uvicorn ui_test_platform.api.main:app --reload --app-dir src
```

### 提交测试用例

```bash
curl -X POST http://localhost:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{"natural_language": "管理员登录后台", "base_url": "https://example.com"}'
```

### 使用真实 agent-browser

```bash
export BROWSER_BACKEND=agent-browser
# 需已安装: npm i -g agent-browser && agent-browser install
```

## Phase 1 基础设施（可选）

```bash
docker compose up -d
export USE_POSTGRES_CHECKPOINTER=true
export USE_MINIO=true
export REQUIRE_RISK_CONFIRMATION=true
```

## 项目结构

```
src/ui_test_platform/
├── agents/          # Planner, Executor, Resolver, Reporter
├── api/             # FastAPI
├── browser/         # BrowserAdapter
├── dsl/             # Pydantic DSL + Compiler
├── graph/           # LangGraph workflow
├── orchestrator/    # 上下文压缩
├── registry/        # 语义注册中心
├── safety/          # 高风险动作 gate
└── storage/         # Checkpointer + MinIO
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `BROWSER_BACKEND` | `mock` | `mock` 或 `agent-browser` |
| `USE_POSTGRES_CHECKPOINTER` | `false` | 启用 Postgres 持久化 |
| `USE_MINIO` | `false` | 截图上传 MinIO |
| `REQUIRE_RISK_CONFIRMATION` | `true` | 高风险动作需确认 |
| `CONFIDENCE_THRESHOLD` | `0.85` | Page Resolver 自动执行阈值 |

## 文档

- [SPC 修订 (G1–G8)](docs/SPC-AMENDMENTS.md)
- [附录 A: DSL Schema](docs/appendix-a-dsl-schema.md)
- [附录 B: BrowserAdapter](docs/appendix-b-browser-adapter.md)
- [附录 C: LangGraph State](docs/appendix-c-langgraph-state.md)
- [附录 D: Registry API](docs/appendix-d-registry-api.md)
