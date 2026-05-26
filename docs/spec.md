# 基于 Agent-Browser 的多 Agent UI 自动化测试平台 SPEC（Software Product/Project Specification）

## 1. 项目概述

### 1.1 项目名称

基于 Agent-Browser 的多 Agent UI 自动化测试平台

### 1.2 项目目标

构建一个面向复杂后台管理系统的、具备自主规划、自主页面理解、自主纠错、自主重试能力的 UI 自动化测试平台。

平台通过：

- 多 Agent 协作
- Action DSL（动作领域语言）
- 页面语义注册中心
- Runtime Page Resolver
- LangGraph 状态机
- Agent-browser CLI 执行层

实现从“自然语言测试用例”到“稳定可执行 UI 自动化流程”的自动转化。

## 2. 项目核心设计目标

### 2.1 核心能力

系统必须具备：

| 能力 | 描述 |
| --- | --- |
| 自然语言测试 | 用户直接输入自然语言测试用例 |
| 自动规划 | 自动生成执行步骤 |
| 页面理解 | 自动理解页面结构与元素语义 |
| 稳定执行 | 避免脆弱 xpath/css selector |
| 动态重规划 | 执行失败后自动纠错 |
| 状态持久化 | 支持中断恢复 |
| 断言验证 | 自动校验业务结果 |
| 可观测性 | 日志、截图、trace 全量记录 |
| DSL约束 | 避免 LLM 幻觉执行 |
| AST执行树 | 执行过程结构化 |
| 平台化扩展 | 支持不同业务系统接入 |

## 3. 总体技术架构

系统采用“四层架构 + 多 Agent 协同”模式。

### 3.1 四层架构

| 层级 | 名称 | 作用 |
| --- | --- | --- |
| Layer1 | DeepAgents 编排层 | 多Agent任务协同 |
| Layer2 | LangGraph 状态机层 | 执行流转与状态控制 |
| Layer3 | LangChain Tools封装层 | Tool能力标准化 |
| Layer4 | Agent-browser CLI执行层 | 浏览器真实执行 |

## 4. 核心架构模块

### 4.1 Orchestrator（总调度器）

#### 4.1.1 模块职责

负责：

- 多Agent协调
- 生命周期管理
- 执行上下文压缩
- Tool调度
- 执行链管理
- Checkpoint恢复
- Retry控制

#### 4.1.2 核心能力

**write_todos 规划**

将用户输入拆解为：

- 目标
- 子任务
- 步骤队列
- 断言列表

**上下文压缩**

避免 LLM 上下文爆炸，包括：

- snapshot压缩
- refs tree压缩
- 历史步骤摘要
- 页面状态摘要

**task 工具委派**

统一分发：

- Planner Agent
- Executor Agent
- Reporter Agent
- Page Resolver

### 4.2 Planner Agent

#### 4.2.1 模块目标

将自然语言测试用例转换为：

- 意图层
- Action DSL
- AST执行树
- 断言列表

Planner 不直接操作页面元素。

Planner 第一阶段禁止直接生成 CLI。

#### 4.2.2 输入

输入包括：

- 自然语言测试用例
- 历史执行状态
- 页面语义能力描述
- DSL Schema
- UI语义注册中心信息

#### 4.2.3 输出

```json
{
  "task": "管理员登录后台",
  "steps": [
    {
      "intent": "打开登录页",
      "action": "open",
      "url": "https://xxx/login"
    },
    {
      "intent": "输入账号",
      "action": "fill",
      "field": "用户名",
      "value": "admin"
    }
  ]
}
```

#### 4.2.4 双阶段生成机制

系统采用“双阶段生成”。

**阶段一：Intent Layer（语义意图层）**

```yaml
- 打开系统
- 输入用户名
- 输入密码
- 点击登录
- 验证登录成功
```

该阶段不涉及页面 ref。

**阶段二：Action DSL 生成**

```yaml
- act: open
  url: xxx

- act: fill
  field: 用户名
  value: admin

- act: click
  target: 登录按钮
```

### 4.3 Action DSL（动作领域语言）

#### 4.3.1 设计目标

Action DSL 是平台级统一动作协议，用于：

- 限制LLM输出
- 统一执行语义
- 防止幻觉
- 支持AST编译
- 支持执行恢复
- 支持可观测性

#### 4.3.2 DSL 白名单

系统仅允许以下动作：

| 动作 | 描述 |
| --- | --- |
| open | 打开页面 |
| click | 点击元素 |
| fill | 输入文本 |
| select | 选择下拉项 |
| hover | 悬停 |
| scroll | 滚动 |
| wait | 等待 |
| assert | 断言 |
| upload | 上传文件 |
| snapshot | 页面快照 |
| screenshot | 截图 |
| console | 获取控制台日志 |

非法动作必须被拦截。

#### 4.3.3 DSL Schema

采用 Pydantic 强校验。

```python
class Action(BaseModel):
    action: Literal[
        "open",
        "click",
        "fill",
        "assert"
    ]

    target: Optional[str]
    value: Optional[str]
    url: Optional[str]
```

#### 4.3.4 Action AST

DSL 最终编译为 AST。

```json
{
  "type": "sequence",
  "children": [
    { "type": "open" },
    { "type": "fill" }
  ]
}
```

AST 节点支持：

- depends_on
- retry
- timeout
- rollback
- condition

### 4.4 DSL Compiler

#### 4.4.1 模块职责

负责：

- DSL解析
- Schema校验
- AST编译
- 非法动作拦截
- 执行树生成

#### 4.4.2 编译流程

```text
DSL
  ↓
Schema Validator
  ↓
Rule Engine
  ↓
AST Compiler
  ↓
Executable AST
```

### 4.5 LangGraph 状态机层

#### 4.5.1 模块目标

实现：

- 可恢复执行
- 状态流转
- Retry机制
- 多Agent编排
- 人机中断恢复

#### 4.5.2 状态节点

| 状态 | 描述 |
| --- | --- |
| INIT | 初始化 |
| PLAN | 规划 |
| RESOLVE | 页面解析 |
| EXECUTE | 执行 |
| ASSERT | 断言 |
| RETRY | 重试 |
| RECOVER | 恢复 |
| REPORT | 报告生成 |
| END | 结束 |

#### 4.5.3 Retry机制

执行失败时：

```text
EXECUTE FAILED
    ↓
采集失败上下文
    ↓
snapshot
    ↓
planner重规划
    ↓
重新执行
```

支持：

- 最大重试次数
- 指数退避
- 局部重规划
- 步骤级恢复

### 4.6 Executor Agent

#### 4.6.1 模块职责

负责：

- 执行 DSL
- 页面导航探索
- ref 映射
- snapshot 采集
- 页面语义理解

Executor 才允许操作页面 ref。

#### 4.6.2 执行流程

```text
执行前 snapshot
    ↓
Page Resolver
    ↓
解析 ref
    ↓
生成 click/fill
    ↓
agent-browser CLI
    ↓
采集结果
```

#### 4.6.3 Snapshot机制

系统执行前必须进行：

```bash
snapshot -i
```

返回：

- accessibility tree
- 页面refs
- DOM摘要
- 可交互元素

#### 4.6.4 页面执行动作

```bash
browser_click @ref
browser_fill
browser_console
screenshot png
```

### 4.7 Page Resolver

#### 4.7.1 模块定位

运行时页面语义推理引擎，系统核心模块之一。

#### 4.7.2 主要职责

负责：

- 页面元素语义理解
- ref动态映射
- 页面导航理解
- UI语义推理
- 歧义消解

#### 4.7.3 为什么需要 Page Resolver

复杂后台系统中：

- selector经常变化
- DOM结构复杂
- 动态渲染严重
- iframe层级深
- Ant Design / Element UI结构不稳定

因此不能直接依赖 xpath/css selector，必须基于页面语义、accessibility tree、refs 与 LLM 推理进行动态定位。

#### 4.7.4 输入

```json
{
  "dsl_action": "click 登录按钮",
  "snapshot": {},
  "refs_tree": {}
}
```

#### 4.7.5 输出

```json
{
  "resolved_ref": "@ref_382",
  "confidence": 0.94
}
```

#### 4.7.6 歧义消解机制

如果多个元素匹配，系统执行：

- 相似度排序
- 上下文推理
- 页面区域分析
- 业务语义分析

必要时进入 clarify。

### 4.8 UI Semantic Registry

#### 4.8.1 模块目标

页面语义注册中心，用于积累：

- 页面结构知识
- 组件知识
- 业务术语知识
- 常见按钮语义
- 表单字段语义

#### 4.8.2 示例

```json
{
  "新增": ["新建", "创建", "add"]
}
```

### 4.9 Reporter Agent

#### 4.9.1 模块职责

负责：

- 汇总执行结果
- 生成测试报告
- 输出Verdict
- 失败原因分析
- 截图归档

#### 4.9.2 输出内容

| 内容 | 描述 |
| --- | --- |
| 用例名称 | 测试标题 |
| 执行状态 | success/fail |
| 执行耗时 | 总耗时 |
| 执行步骤 | 每一步日志 |
| 错误原因 | 异常详情 |
| 截图 | PNG存证 |
| Console日志 | JS错误 |
| AST执行树 | 最终执行链 |

### 4.10 Checkpointer

#### 4.10.1 模块职责

负责状态持久化，支持：

- 中断恢复
- 崩溃恢复
- Retry恢复
- 分布式恢复

#### 4.10.2 持久化内容

```json
{
  "current_step": 12,
  "dsl": [],
  "snapshot": {},
  "browser_state": {}
}
```

## 5. 系统执行主流程

### 5.1 主流程

```text
用户输入自然语言
    ↓
Orchestrator
    ↓
Planner Agent
    ↓
Intent Layer
    ↓
Action DSL
    ↓
Schema Validator
    ↓
AST Compiler
    ↓
Executable AST
    ↓
Executor Agent
    ↓
snapshot
    ↓
Page Resolver
    ↓
agent-browser CLI
    ↓
validate/assert
    ↓
Reporter
```

## 6. 示例执行链

### 6.1 新增用户

```yaml
- open url
- click 新增
- fill 用户名
- fill 手机号
- select 部门
- click 提交
- assert 新增成功
```

### 6.2 删除数据

```yaml
- open url
- search keyword
- click checkbox
- click 删除
- click 确认
- assert 删除成功
```

## 7. 断言系统

### 7.1 支持类型

| 类型 | 描述 |
| --- | --- |
| text_assert | 文本断言 |
| visibility_assert | 可见性断言 |
| url_assert | URL断言 |
| table_assert | 表格断言 |
| api_assert | 接口断言 |
| console_assert | JS错误断言 |

## 8. 可观测性系统

### 8.1 日志系统

采集：

- Tool调用日志
- DSL日志
- AST日志
- 页面日志
- Console日志
- Retry日志

### 8.2 Trace系统

每个步骤生成：

```json
{
  "step_id": "xxx",
  "action": "click",
  "ref": "@ref_123",
  "duration": 1220
}
```

## 9. 安全机制

### 9.1 DSL 白名单

禁止：

- 任意shell执行
- 任意JS执行
- 文件删除
- 系统命令执行

### 9.2 风险动作确认

高风险操作（删除、批量提交、数据覆盖）需要额外确认。

## 10. 技术栈

### 10.1 后端

| 技术 | 用途 |
| --- | --- |
| Python | 主语言 |
| FastAPI | API层 |
| LangChain | Tools封装 |
| LangGraph | 状态机 |
| Pydantic | Schema校验 |
| Playwright | 浏览器控制 |
| Agent-browser | CLI执行 |

### 10.2 存储

| 技术 | 用途 |
| --- | --- |
| PostgreSQL | 状态存储 |
| Redis | 缓存 |
| MinIO | 截图与报告 |

## 11. 部署架构

### 11.1 微服务划分

| 服务 | 描述 |
| --- | --- |
| orchestrator-service | 总调度 |
| planner-service | 规划Agent |
| executor-service | 执行Agent |
| resolver-service | 页面解析 |
| report-service | 报告服务 |
| browser-worker | 浏览器执行节点 |

## 12. 未来扩展方向

### 12.1 AI增强

未来支持：

- UI视觉识别
- OCR
- 视频回放
- 自愈定位
- 自动生成测试用例
- MCP工具生态

## 13. 项目关键设计原则

### 13.1 Planner 不直接操作页面

必须通过：

```text
Planner → DSL → Executor → Page Resolver → Browser
```

避免 ref污染、幻觉定位与不稳定执行。

### 13.2 Snapshot First

任何动作执行前必须 snapshot。

### 13.3 Runtime Resolve

ref 必须运行时动态解析，禁止静态selector。

### 13.4 强约束优于自由Agent

系统必须使用 DSL约束、Schema约束、AST约束、状态机约束，避免纯 AutoGPT 模式失控。

## 14. 项目最终目标

构建一个企业级、高稳定性、可恢复、可观测、多Agent协同、自愈型、面向复杂后台系统的下一代 AI UI 自动化测试平台。
