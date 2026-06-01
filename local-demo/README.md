# P3394 Local Workspace

这是 P3394 Agent Platform 的本地工作区。平台底座来自 AgentClaw，默认主智能体是 `p3394_runtime_agent`。

## 打开平台

从仓库根目录运行：

```powershell
.\start-p3394.cmd
```

然后访问：

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

## 目录结构

```text
local-demo/
|-- agents/
|   |-- p3394_runtime_agent/   # P3394 主智能体
|   |-- __init__.py            # 工作流注册入口
|-- .agentclaw/                # 本地 SQLite 和运行时数据
|-- logs/                      # 运行日志
|-- models.json                # 模型配置
|-- mcp.json                   # MCP 配置
|-- server.py                  # 服务入口
|-- .env                       # 端口、Token、运行时配置
```

## 常用文件

- `agents/p3394_runtime_agent/agents/p3394_runtime_agent.py`：P3394 主智能体定义。
- `.env`：本地服务配置和 Admin Token。
- `models.json`：模型供应商、模型名、API Key 和 Base URL。
- `.agentclaw/agentclaw-local.db`：P3394 任务历史、工具记录和文件上下文。

## 增加新智能体

可以继续从模板库导入，也可以在 `agents/` 下增加新的工作流包，然后在 `agents/__init__.py` 注册。

P3394 主智能体会保留为默认入口，新智能体可以作为模板、子工作流或独立工作流逐步接入。
