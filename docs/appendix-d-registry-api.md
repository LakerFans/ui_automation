# 附录 D：UI Semantic Registry API

实现：`src/ui_test_platform/registry/store.py`, `registry/api.py`

## 1. 数据模型

```json
{
  "version": "1.0.0",
  "synonyms": {
    "新增": ["新建", "创建", "add", "Add"],
    "删除": ["移除", "delete", "Delete"],
    "用户名": ["账号", "username", "user name"]
  },
  "pages": [
    {
      "url_pattern": "*/users*",
      "name": "用户管理",
      "components": ["Table", "Form", "Modal"],
      "fields": {
        "用户名": {"type": "input", "required": true},
        "手机号": {"type": "input", "required": true},
        "部门": {"type": "select", "required": false}
      },
      "actions": {
        "新增": {"type": "button", "region": "toolbar"},
        "提交": {"type": "button", "region": "modal"}
      }
    }
  ],
  "risk_keywords": ["删除", "批量", "覆盖", "清空"]
}
```

## 2. HTTP API（FastAPI 挂载于 `/registry`）

### GET /registry/semantics

查询同义词与页面语义。

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| `url` | 否 | 当前页面 URL，用于匹配 `pages[].url_pattern` |
| `term` | 否 | 语义关键词（按钮名、字段名） |

**Response 200**

```json
{
  "term": "新增",
  "synonyms": ["新建", "创建", "add"],
  "page": {
    "name": "用户管理",
    "fields": ["用户名", "手机号", "部门"],
    "actions": ["新增", "提交", "删除"]
  },
  "region_hint": "toolbar"
}
```

### GET /registry/synonyms

**Query**: `term`（必填）

**Response**: `{ "term": "...", "synonyms": [...] }`

### GET /registry/pages

**Query**: `url`（必填）

**Response**: 匹配的 page 对象或 404。

## 3. 内存索引

`SemanticRegistry` 启动时加载 `data/registry/*.json`，构建：

- `synonym_index: dict[str, set[str]]`（双向）
- `page_index: list[PageTemplate]`（fnmatch URL）

## 4. 平台接入 SDK（新业务系统）

1. 在 `data/registry/` 新增 `{system_name}.json`
2. 定义 `url_pattern`、`fields`、`actions` 同义词
3. 设置 `ALLOWED_URL_PATTERNS` 环境变量包含测试域
4. （可选）贡献 `risk_keywords` 供 RiskGate 使用

## 5. 版本化

- Registry 文件带 `"version"` 字段
- Git 管理；运行时热加载：`POST /registry/reload`（开发模式）

## 6. Resolver 融合

Page Resolver 评分公式（MVP）：

```
score = 0.5 * name_similarity(target, ref.name)
      + 0.3 * synonym_boost(registry, target, ref.name)
      + 0.2 * region_match(page_template, ref)
```

`confidence = min(1.0, score)`；见 G8 阈值。
