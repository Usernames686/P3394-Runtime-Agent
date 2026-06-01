# P3394 Runtime Agent

## 当前状态

P3394 Runtime Agent 现在是基于 AgentClaw 包装出来的本地通用智能体平台主入口。

它不是从 0 新写的系统，而是在 AgentClaw 的工作流、模型调用、工具调用、前端聊天页、管理 API 和本地持久化能力上，加了一层 P3394 风格的运行时协议和智能体组织方式。

当前阶段可以理解为：

- 已经能本地运行。
- 已经能接入模型正常对话。
- 已经能执行本地命令和工具。
- 已经有 P3394 任务历史、执行记录、文件上下文、工具记录。
- 已经有 Planner / Researcher / Executor / Reviewer 四个内部角色轨迹。
- 已经接入本地 `P3394-v0.9.0-combined(2).md` 作为架构参考。
- 还不是完全成熟的独立多智能体集群，四个角色目前主要是内部流程分工和记录，真正执行仍然由 AgentClaw 的 agentic LLM runtime 完成。

## 本地打开方式

本地页面：

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

Admin Token：

```text
ac-admin-bc137b7f19f110bfdc0859ad6c1b0c5a
```

如果服务没启动，在项目根目录运行：

```powershell
.venv\Scripts\agentclaw.exe serve -d local-demo -p 8000 -h 127.0.0.1
```

建议启动时带 UTF-8 环境变量，避免 Windows 控制台中文乱码：

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
.venv\Scripts\agentclaw.exe serve -d local-demo -p 8000 -h 127.0.0.1
```

## 它现在能做什么

### 1. 正常模型对话

P3394 Runtime Agent 可以像普通 AgentClaw 智能体一样和模型对话。

普通问题会尽量输出正常语言，而不是默认展示一堆 P3394 manifest、UMF、audit、route JSON。

P3394 协议细节默认作为内部上下文使用，只有用户明确问 P3394 内部机制时才展开。

### 2. 本地命令执行

已经接入本地命令工具：

- `shell`
- `powershell`
- `python`
- `javascript`

其中 `powershell` 是单独的一等工具，不再只依赖 `shell` 包一层 PowerShell。

PowerShell 工具会尽量使用 UTF-8 输出，避免中文和 JSON 内容在 Windows 下被命令行编码破坏。

### 3. 文件和项目工具

已经接入：

- `read_file`
- `write_file`
- `write_code`
- `list_files`
- `project_overview`
- `search_code`
- `read_code`
- `replace_in_file`
- `update_code`
- `syntax_check`

可以读项目文件、看目录结构、分析代码、修改代码并做基础验证。

### 4. Git 工具

已经接入：

- `git_status`
- `git_diff`
- `git_commit_suggestions`

用途：

- 查看当前工作区改动。
- 查看 diff。
- 给提交信息建议。

默认不会自动执行 `git commit`，除非用户明确要求。

### 5. 文档读取

`read_file` 支持常见文本和文档类型：

- Markdown
- TXT
- 代码文件
- JSON / YAML
- PDF
- DOCX
- PPTX
- XLSX

文档类文件会尝试转换成 Markdown 形式供模型阅读。

### 6. 网页搜索

已经接入：

- `search_web`

优先使用 `SEARXNG_BASE_URL`，如果没配置则回退 DuckDuckGo HTML 搜索。

用途：

- 查外部资料。
- 查开源项目。
- 查文档。
- 查 GitHub 相关信息。

## 前端入口

P3394 页面现在使用 AgentClaw 原生聊天界面，保持界面简洁，默认作为平台首页。

页面结构：

- 左侧：P3394 主智能体、底座助手、模板库和设置入口。
- 中间：原生 AgentClaw 聊天和执行结果。
- 工具调用过程默认不打扰主对话，结果会尽量以清楚的消息形式呈现。

## 命令结果卡片

命令和工具记录会被整理成结构化结果。

核心字段：

- command
- cwd
- stdout
- stderr
- exit_code
- status
- duration_ms

前端有 `CommandResultCard` 组件负责展示这些结果。

这样用户看到的是清楚的命令结果，而不是一大坨难读的原始工具输出。

## 本地持久化

P3394 Runtime Agent 增加了 SQLite 本地持久化。

本地 demo 不依赖 PostgreSQL 也能保存运行记录。

默认 SQLite 路径优先级：

1. `AGENTCLAW_SQLITE_PATH`
2. `AGENTCLAW_DATA_DIR/agentclaw-local.db`
3. `AGENTCLAW_PROJECT_DIR/.agentclaw/agentclaw-local.db`

当前本地 demo 常见路径：

```text
local-demo/.agentclaw/agentclaw-local.db
```

主要表：

- `agent_conversations`
- `p3394_task_history`
- `p3394_execution_records`
- `p3394_file_contexts`
- `p3394_tool_records`

## P3394 内部角色

表面上仍然是一个 P3394 Runtime Agent。

内部现在有四个角色：

### P3394 Planner

负责：

- 拆任务。
- 判断任务边界。
- 选择路线。
- 确认需要哪些工具和验证。

### P3394 Researcher

负责：

- 查资料。
- 读本地 P3394 文档。
- 读项目文件。
- 读 Markdown / PDF / 文档。
- 必要时做网页搜索。

### P3394 Executor

负责：

- 执行命令。
- 调用工具。
- 修改代码。
- 运行测试。
- 产出实际结果。

### P3394 Reviewer

负责：

- 检查结果。
- 看命令是否失败。
- 看文件是否真的改了。
- 看测试是否通过。
- 记录风险和缺口。

## 当前多智能体成熟度

当前版本不是完全独立的多 Agent 集群。

更准确地说：

- 已经有四个 P3394 内部角色。
- 已经有角色计划和角色执行状态记录。
- 已经能在任务历史里看到每个角色的状态、结果和 artifact。
- 真正的模型与工具执行仍由一个 AgentClaw `LLMNode(agent_style="agentic")` 完成。

也就是说，它现在是：

```text
单 Agent 表面
  +
P3394 角色化运行时
  +
AgentClaw agentic 工具执行
```

还不是：

```text
Planner 独立模型
Researcher 独立模型
Executor 独立模型
Reviewer 独立模型
多个子 Agent 并行/串行协作
```

## P3394 文档能力

本地 P3394 文档：

```text
D:\codex\ui\P3394-v0.9.0-combined(2).md
```

已经作为架构参考注入到 P3394 Runtime Agent。

它会影响这些任务：

- 按 P3394 架构分析项目。
- 按 P3394 改造 AgentClaw 智能体。
- 解释 manifest、channel adapter、UMF、session、relationship、capability、audit、conformance。
- 设计 P3394 风格的 agent runtime。

## 模型诊断

页面顶部有模型健康检查。

能显示：

- 当前模型是否可用。
- 是否缺少 key。
- 是否认证失败。
- 是否超时。
- base_url 是否不可达。
- 模型名是否错误。

也支持一键测试模型。

这样用户看到失败时，不会误以为是 P3394 本身坏了。

## 已验证内容

已经做过的验证包括：

- 后端 P3394 / 工具测试通过。
- 前端 P3394 / 聊天状态测试通过。
- 前端生产构建通过。
- 页面访问返回 200。
- 模型 smoke test 通过。
- PowerShell 工具真实执行通过。
- P3394 工具记录能落库。
- P3394 任务历史能看到四个角色状态。

示例真实执行结果：

```text
tool_name: powershell
command: Write-Output "P3394_PS_OK"
stdout: P3394_PS_OK
status: succeeded
```

## 现在怎么用

可以直接在 P3394 页面输入：

```text
帮我分析这个项目结构
```

```text
运行 powershell：Get-Location
```

```text
查看 git 状态并总结改动
```

```text
读取 README.md，告诉我这个项目怎么启动
```

```text
按 P3394 架构分析这个 AgentClaw 项目
```

```text
搜索 GitHub 上 agent protocol / P3394 相关资料并总结
```

## 当前限制

### 1. 多 Agent 还不是真独立子智能体

现在四个角色是运行时角色轨迹，真正模型执行还是一个 agentic LLM runtime。

后续可以升级成真正独立的 Planner / Researcher / Executor / Reviewer 子 Agent。

### 2. 前端还可以继续简化

当前已经比原管理台更聚焦，但还可以继续压缩：

- 更像一个纯工作台。
- 更少管理配置入口。
- 更清楚地区分聊天、工具结果、文件上下文。

### 3. 网页搜索依赖外部网络

`search_web` 如果没有配置 SearXNG，会使用 DuckDuckGo HTML。

外部网络不可用时，搜索会失败。

### 4. 文档读取依赖转换库

PDF / DOCX / PPTX / XLSX 的读取依赖本地转换能力。

复杂版式可能无法完全保真。

## 下一步升级建议

### 优先级 1：真正多 Agent

把四个角色升级成真正独立执行单元：

- Planner 独立模型调用。
- Researcher 独立工具调用。
- Executor 独立执行和修改。
- Reviewer 独立检查和总结。

### 优先级 2：任务模式

增加几个固定模式：

- 写代码
- 修 bug
- 查资料
- 分析项目
- 执行命令
- 生成方案

用户不用理解工具名，直接选模式或输入任务。

### 优先级 3：更强网页/GitHub 资料能力

增强：

- GitHub repo 搜索
- README 读取
- 文档站抓取
- 代码片段参考
- 来源引用

### 优先级 4：项目长期记忆

让 P3394 记住：

- 项目结构
- 已经改过什么
- 重要文件
- 上次任务进度
- 用户偏好

### 优先级 5：UI 视觉验收

用浏览器自动化截图检查：

- 页面是否空白
- 卡片是否重叠
- 移动端是否可用
- 工具记录是否展示正常

## 结论

P3394 Runtime Agent 现在已经是一个可以本地使用的 AgentClaw 风格智能体平台雏形。

它已经具备：

- 模型对话
- 本地命令执行
- PowerShell
- 文件读写
- Git
- 项目分析
- 文档读取
- 网页搜索
- SQLite 记录
- P3394 角色化运行轨迹
- P3394 文档参考
- 简化工作台页面

它下一阶段的核心目标，是从“单 Agent + P3394 角色轨迹”升级成“真正多 Agent 协作运行时”。
