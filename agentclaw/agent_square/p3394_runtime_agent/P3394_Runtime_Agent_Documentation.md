# P3394 Runtime Agent 说明文档

## 1. 概述

**P3394 Runtime Agent** 是 AgentClaw 内置的一个 P3394 风格运行时智能体模板。它保留 AgentClaw 原有的 Workflow 执行模型，同时在外层增加了一层 P3394 运行时契约，用于规范智能体清单、消息格式、会话管理、权限关系、审计记录、任务路由和工作流委派。

该智能体并不是单纯的聊天机器人，而是一个具备工具调用能力、会话上下文能力和治理边界的 AgentClaw 编排型智能体。配置好 LLM 模型后，它可以通过 AgentClaw 的内置工具和技能完成文件检查、命令运行、代码修改、测试验证、资料搜索、文档分析等任务。

## 2. 基本信息

| 项目 | 内容 |
| --- | --- |
| 工作流 ID | `p3394_runtime_agent` |
| 名称 | `P3394 Runtime Agent` |
| 入口文件 | `agents/p3394_runtime_agent.py` |
| 类型 | AgentClaw 内置标准智能体 |
| 分类 | `standard` |
| 推荐输入 | `task.route: run tests and explain the result` |
| 默认关系 | `owner` |
| 运行方式 | AgentClaw Workflow + Agentic LLMNode |

## 3. 设计目标

P3394 Runtime Agent 的核心目标是把 P3394 草案中的运行时治理思想落地到 AgentClaw 中，形成一个可执行、可审计、可路由、可委派的智能体运行时。

主要设计目标包括：

1. **清单化描述智能体能力**：通过 Manifest 声明智能体身份、输入形式、通道、安全边界和能力列表。
2. **统一消息入口**：支持普通 `user_input`，也支持 UMF 风格的 `umf_message`。
3. **会话生命周期管理**：支持创建、读取和关闭 P3394 会话上下文。
4. **基于关系的权限控制**：根据 `owner`、`administrator`、`peer`、`client`、`anonymous` 等关系限制可用能力。
5. **任务路由与工作流委派**：根据任务类型选择本地 agentic runtime 或委派到其他 AgentClaw 工作流。
6. **审计与符合性检查**：记录运行事件，并提供审计摘要和 P3394 符合性报告。
7. **工具型智能体执行**：通过 AgentClaw LLMNode 调用内置工具、技能和本地项目操作能力。

## 4. 输入参数

该工作流定义了以下输入：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `user_input` | `string` | 是 | 无 | 用户任务输入，或直接要求智能体运行命令、检查文件、修改代码等 |
| `umf_message` | `object` | 否 | `None` | 可选的 UMF 风格消息信封 |
| `relationship` | `string` | 否 | `owner` | 调用者与智能体的关系，例如 `owner`、`administrator`、`client`、`anonymous` |
| `model` | `string` | 否 | 空字符串 | 可选模型 ID，由调用者指定 |

## 5. 核心能力

P3394 Runtime Agent 在 Manifest 中声明了多类能力：

### 5.1 协议与消息能力

- `manifest.describe`：返回 P3394 风格智能体清单。
- `message.normalize`：将用户输入规范化为 UMF 风格消息信封。
- `conformance.check`：返回 P3394 运行时符合性报告。

### 5.2 会话管理能力

- `session.create`：创建 P3394 会话上下文。
- `session.fetch`：读取当前活跃会话上下文。
- `session.close`：关闭会话上下文。

### 5.3 智能体执行能力

- `chat`：通过 AgentClaw LLM Agent 处理普通用户请求。
- `command_execution`：在授权条件下使用内置工具执行命令、文件和代码操作。
- `local_project_tooling`：使用本地项目工具进行文件、Shell、Git、文档和 Web 搜索等操作。

### 5.4 P3394 扩展能力

- `p3394.architecture_reference`：使用本地 P3394 v0.9.0 草案作为架构参考。
- `p3394.multi_agent_roles`：在单一智能体界面背后规划 Planner、Researcher、Executor、Reviewer 等内部角色。
- `p3394.task_history`：查询 P3394 任务历史。
- `p3394.file_context`：记录和查询运行中涉及的文件上下文。
- `p3394.tool_records`：记录和查询工具调用、命令输出、工作目录、错误信息和退出码。

### 5.5 编排能力

- `task.route`：识别用户任务并选择目标执行路径。
- `agent.delegate`：将授权请求委派给已注册的 AgentClaw 工作流。
- `audit.summary`：返回可审计的执行摘要。

## 6. 任务路由机制

P3394 Runtime Agent 使用 `route_then_execute` 的编排模式。普通请求会先被分类，再选择执行目标。

内置路由包括：

| 路由族 | 目标 | 执行模式 | 适用场景 |
| --- | --- | --- | --- |
| `p3394_architecture` | `agentic_runtime` | 本地 agentic runtime | P3394 架构分析、项目改造、协议参考任务 |
| `code_command` | `agentic_runtime` | 本地 agentic runtime | 命令运行、代码检查、测试执行、本地项目操作 |
| `document_analysis` | `doc_analyzer` | 条件满足时委派工作流 | PDF、DOCX、合同、报告等文档分析 |
| `knowledge_search` | `tool_agent` | 可用时委派工作流 | 搜索资料、GitHub、Web 查询等任务 |
| `general_chat` | `agentic_runtime` | 本地 agentic runtime | 普通对话与通用问答 |

默认目标是 `agentic_runtime`。

## 7. 权限与关系模型

该智能体根据调用者关系限制能力访问：

| 关系 | 权限特点 |
| --- | --- |
| `owner` | 拥有全部能力访问权限，可执行所有能力 |
| `administrator` | 可访问大多数管理、执行、路由、委派和审计能力 |
| `peer` | 可查询 Manifest、创建/读取会话、聊天、路由和查看部分 P3394 上下文 |
| `client` | 可使用会话、聊天、命令执行、本地工具、P3394 上下文和任务路由等能力，但受更严格语义限制 |
| `anonymous` | 仅可访问 `manifest.describe`、`message.normalize`、`task.route` |

安全策略中还包含非升级原则：默认安全级别为 `normal`，提升权限需要 `owner` 或 `administrator` 关系，并且提升范围限定在会话内。

## 8. 会话模型

P3394 Runtime Agent 支持 P3394 风格的会话生命周期：

- `created`
- `open`
- `closing`
- `closed`
- `failed`
- `aborted`
- `expired`

会话上下文可包含以下隔离区：

- `context_variables`
- `participants`
- `budgets`
- `memory_pointers`
- `child_sessions`

这使智能体可以在多轮任务中维护上下文，同时保留清晰的生命周期边界。

## 9. AgentClaw 执行层

在执行层，P3394 Runtime Agent 使用 AgentClaw 的 `LLMNode`，并配置为 agentic 模式：

```text
agent_style = "agentic"
tools = "*"
skills = "*"
enable_builtin_tools = true
enable_builtin_skills = true
memory = enabled
```

因此它具备以下能力：

- 读取和分析项目文件；
- 执行 Shell 或 PowerShell 命令；
- 修改代码并运行验证；
- 使用 Git 工具检查变更；
- 调用内置技能；
- 搜索外部资料；
- 分析文档；
- 生成简洁的执行结果说明。

## 10. 常用示例输入

```text
manifest.describe
session.create: create a contract review session for the legal team.
session.fetch
session.close
task.route: analyze this PDF contract
task.route: search GitHub for agent protocol examples
agent.delegate
message.normalize: analyze Q2 supplier risk.
audit.summary
conformance.check
list the current project files and explain what you found
run tests for this AgentClaw project
```

## 11. UMF 委派示例

如果要显式委派给其他工作流，可以传入类似下面的 UMF 风格消息：

```json
{
  "capability": "agent.delegate",
  "message_type": "agent.command",
  "body": {
    "input": {
      "target_workflow_id": "some_registered_workflow",
      "delegation_inputs": {
        "user_input": "work to delegate"
      }
    }
  }
}
```

## 12. 适用场景

P3394 Runtime Agent 适合以下场景：

1. **项目级智能体执行**：检查代码、运行测试、修改文件、总结结果。
2. **P3394 协议实验**：验证 Manifest、UMF、Session、Relationship、Audit 等运行时概念。
3. **多工作流编排**：根据任务类型把请求路由到本地 agentic runtime 或其他已注册工作流。
4. **文档与资料分析**：分析合同、报告、PDF、DOCX 或搜索外部资料。
5. **审计型任务执行**：需要记录执行过程、工具调用和结果摘要的任务。
6. **权限边界演示**：根据不同 relationship 展示能力裁剪和访问控制。

## 13. 与普通 AgentClaw Agent 的区别

| 对比项 | 普通 AgentClaw Agent | P3394 Runtime Agent |
| --- | --- | --- |
| 消息入口 | 通常是简单用户输入 | 支持 `user_input` 和 UMF 风格信封 |
| 能力描述 | 由工作流和节点隐式体现 | 通过 Manifest 显式声明 |
| 会话治理 | 依赖平台或工作流自行处理 | 内置 P3394 会话生命周期 |
| 权限控制 | 通常按平台级权限处理 | 增加 relationship-based capability access |
| 路由机制 | 由工作流逻辑决定 | 内置任务分类与目标路由 |
| 审计能力 | 可选 | 内置 audit summary 与事件记录 |
| 工具执行 | 取决于节点配置 | 默认面向 agentic 工具执行场景 |

## 14. 总结

P3394 Runtime Agent 是一个把 P3394 运行时治理思想和 AgentClaw 执行能力结合起来的智能体。它通过 Manifest、UMF、Session、Relationship、Audit、Routing 和 Delegation 等机制，为 AgentClaw 智能体提供了更清晰的协议边界和运行时结构。

从使用者角度看，它既可以像普通助手一样对话，也可以作为项目执行型智能体运行命令、检查文件、修改代码和分析文档；从架构角度看，它提供了一个可扩展、可审计、可委派的 P3394 风格智能体运行时样例。
