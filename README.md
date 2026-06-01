# P3394 Agent Platform

P3394 Agent Platform 是一个本地通用智能体平台。它基于 AgentClaw 二次包装，把 P3394 Runtime Agent 作为默认主智能体，保留 AgentClaw 的工作流、模型调用、工具执行、模板库、管理 API 和原生聊天界面。

当前目标不是从 0 重写一个 Agent 框架，而是在已经跑通的 AgentClaw 底座上，包装成你自己的 P3394 智能体项目。

## 快速打开

在仓库根目录运行：

```powershell
.\start-p3394.cmd
```

打开：

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

Admin Token：

```text
ac-admin-bc137b7f19f110bfdc0859ad6c1b0c5a
```

## 现在有什么

- `P3394 主智能体`：默认入口，像 AgentClaw 原版聊天页一样使用。
- `底座助手`：保留 AgentClaw 原版内置 Agent，方便对照和兜底。
- `模板库`：继续导入其他 Agent 模板。
- `P3394 Runtime`：内置 P3394 路由、角色轨迹、任务历史、工具记录、文件上下文。
- `本地命令执行`：通过 AgentClaw 工具和 agentic runtime 执行命令、读写文件、分析代码。
- `模型接入`：通过 `local-demo/models.json` 配置模型。

## 项目结构

```text
.
|-- agentclaw/                         # AgentClaw 底座框架和管理前端
|   |-- admin-dashboard/               # P3394 包装后的前端
|   |-- agent_square/p3394_runtime_agent/
|-- local-demo/                        # 本地运行工作区
|   |-- agents/p3394_runtime_agent/    # 默认主智能体
|   |-- models.json                    # 模型配置
|   |-- .env                           # 端口、Token、运行配置
|-- docs/
|   |-- P3394-Agent-Platform.md        # 项目包装说明
|   |-- P3394-Runtime-Agent.md         # P3394 Runtime 详细说明
|-- scripts/start-p3394.ps1            # Windows 启动脚本
|-- start-p3394.cmd                    # 一键启动入口
```

## 常用命令

启动本地平台：

```powershell
.\start-p3394.cmd
```

手动启动：

```powershell
$env:AGENTCLAW_PROJECT_DIR = "D:\codex\ui\agentclaw\local-demo"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -X utf8 -m agentclaw.cli serve -d local-demo --host 127.0.0.1 --port 8000
```

构建前端：

```powershell
cd agentclaw\admin-dashboard
npm run build
```

运行 P3394 相关测试：

```powershell
.\.venv\Scripts\python.exe -m pytest agentclaw/test/unit/test_dashboard_template_import.py agentclaw/test/api/test_admin_api_contracts.py::test_admin_template_library_repair_uses_service_dependency -q
cd agentclaw\admin-dashboard
npm test -- src/__tests__/p3394-model-diagnostics.spec.js src/__tests__/agent-square.spec.js
```

## 配置模型

编辑：

```text
local-demo/models.json
```

也可以在前端的系统配置里填写模型。模型配置修改后建议重启本地服务。

## 后续方向

- 把 P3394 任务历史、工具记录和文件上下文做成简洁侧栏。
- 做一个初始化向导：检查模型、P3394 模板、命令工具、搜索工具是否可用。
- 把 P3394 内部 Planner / Researcher / Executor / Reviewer 从“记录轨迹”升级为更真实的多 Agent 协作。
