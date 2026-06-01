# P3394 Agent Platform

P3394 Agent Platform 是基于 AgentClaw 包装出来的本地通用智能体平台。它把 AgentClaw 的工作流、模型调用、工具执行、模板库、管理 API 和前端聊天界面作为底座，把 P3394 Runtime Agent 作为默认主智能体。

## 当前定位

- 默认入口：P3394 Runtime Agent。
- 底层框架：AgentClaw。
- 本地项目：`local-demo`。
- 主智能体目录：`local-demo/agents/p3394_runtime_agent`。
- 管理前端：`agentclaw/admin-dashboard`。

## 本地启动

在仓库根目录运行：

```powershell
.\start-p3394.cmd
```

或直接运行 PowerShell 脚本：

```powershell
.\scripts\start-p3394.ps1
```

打开：

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

Admin Token：

```text
ac-admin-bc137b7f19f110bfdc0859ad6c1b0c5a
```

## 已包装内容

- 浏览器标题改为 `P3394 Agent Platform`。
- 管理台默认首页改为 `/dashboard/p3394-agent`。
- 侧边栏品牌改为 `P3394`。
- 侧边栏第一项改为 `P3394 主智能体`。
- AgentClaw 原版内置智能体保留为 `底座助手`。
- 模板库保留，用于继续导入和扩展智能体。
- P3394 首次启用页改为你的项目文案。

## P3394 主智能体能力

P3394 Runtime Agent 现在可以作为普通本地智能体使用：

- 模型对话。
- 命令执行。
- 文件读取和代码分析。
- 项目文件修改。
- 文档分析。
- 网页搜索。
- P3394 内部任务历史、工具记录、文件上下文和执行记录。

默认情况下，它会用正常模型语言输出，不会把 UMF、manifest、session、audit、route JSON 等内部协议细节直接甩给用户。

## 后续包装方向

下一步更像“真正自己的产品”的升级可以继续做：

- 统一环境变量前缀和启动命令别名。
- 增加自己的 logo 和应用图标。
- 加一个项目设置页，显示平台名称、工作区路径、P3394 文档路径和模型状态。
- 把 P3394 的任务历史、工具记录和文件上下文做成原生侧栏，但保持界面简洁。
- 加“项目初始化向导”，自动复制 P3394 模板、配置模型、检查工具可用性。
