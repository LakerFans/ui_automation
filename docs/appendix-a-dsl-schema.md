# 附录 A：Action DSL Schema 完整版

Schema 版本：`1.0.0`（Pydantic 实现见 `src/ui_test_platform/dsl/models.py`）

## 1. 动作白名单

| action | 必填字段 | 可选字段 | 说明 |
|--------|----------|----------|------|
| `open` | `url` | `intent` | 打开页面 |
| `click` | `target` | `intent`, `timeout` | 点击语义目标 |
| `fill` | `target`, `value` | `intent` | 输入文本 |
| `select` | `target`, `value` | `intent` | 下拉选择 |
| `search` | `target`, `value` | `intent` | 搜索（展开为 fill + submit） |
| `hover` | `target` | `intent` | 悬停 |
| `scroll` | `value` | `target`, `intent` | 滚动方向/像素 |
| `wait` | `value` | `intent` | 等待 ms 或 selector |
| `assert` | `assert_type`, `value` | `target`, `intent` | 断言 |
| `upload` | `target`, `value` | `intent` | 文件路径 |
| `snapshot` | — | `intent` | 强制页面快照 |
| `screenshot` | — | `value`(path), `intent` | 截图存证 |
| `console` | — | `intent` | 读取控制台 |

非法 `action` 在 Schema Validator 阶段拦截，不进入 AST。

## 2. assert 子类型

| assert_type | 字段 | 校验方式 |
|-------------|------|----------|
| `text_assert` | `value` 期望文本, `target` 可选区域 | snapshot 文本包含 |
| `visibility_assert` | `target` | ref 存在于 interactive tree |
| `url_assert` | `value` 期望 URL 片段 | 当前 URL 匹配 |
| `table_assert` | `target`, `value` | 表格行/列语义匹配 |
| `api_assert` | `value` URL 模式 | 网络监听或独立 HTTP（Phase 1+） |
| `console_assert` | `value` 错误模式 | console 无匹配 error |

## 3. Plan 输出 JSON

```json
{
  "schema_version": "1.0.0",
  "task": "管理员登录后台",
  "intents": [
    {"intent_id": "i1", "text": "打开登录页"},
    {"intent_id": "i2", "text": "输入账号"}
  ],
  "steps": [
    {
      "intent_id": "i1",
      "intent": "打开登录页",
      "action": "open",
      "url": "https://example.com/login"
    },
    {
      "intent_id": "i2",
      "intent": "输入账号",
      "action": "fill",
      "target": "用户名",
      "value": "admin"
    }
  ]
}
```

## 4. AST 节点

```json
{
  "type": "sequence",
  "schema_version": "1.0.0",
  "children": [
    {
      "type": "action",
      "action": "open",
      "url": "https://example.com/login",
      "retry": 3,
      "timeout_ms": 30000,
      "depends_on": [],
      "condition": null,
      "rollback": null
    }
  ]
}
```

- `condition`：MVP 仅支持 `url_contains` / `text_present`（求值上下文：最新 snapshot + URL）
- `rollback`：MVP 支持 `screenshot` + `snapshot` 序列
- MVP **禁止**宏动作节点；Planner 负责展开

## 5. 字段约束

- `url`：必须为 `http://` 或 `https://`，且匹配环境白名单（`ALLOWED_URL_PATTERNS`）
- `target` / `field`：非空字符串，最大 256 字符
- `value`：最大 4096 字符
- `timeout_ms`：100–120000，默认 30000
- `retry`：0–5，默认 2
