# P3394 Runtime Agent

本项目基于 [`Negai-ai/AgentClaw`](https://github.com/Negai-ai/AgentClaw) 二次开发。

这是一个在 AgentClaw 底座上包装出来的 P3394 通用智能体平台，不是从 0 重写框架。它保留 AgentClaw 的工作流、模型调用、工具执行、知识库、调度器、追踪、Admin API 和 Dashboard，同时新增 P3394 主智能体、本地知识库、记忆图谱、每日记忆、执行记录和 Docker Compose 部署。

## 新增内容

| 模块 | 新增内容 |
| --- | --- |
| P3394 主智能体 | 默认入口是 `P3394 Runtime Agent`，参考 P3394 文档里的 manifest、UMF、session、capability router、audit trail 思路 |
| AgentClaw 风格聊天页 | 入口改为 `/dashboard/p3394-agent`，保留接近原版 AgentClaw 的聊天体验 |
| P3394 工作台 | 右侧可折叠工作台，包含文件产物、本地知识库、执行记录 |
| 本地知识库 | 支持导入 Markdown、文本、PDF、DOCX 等文件 |
| 记忆图谱 | 新增独立页面，用 Sigma.js + Graphology 展示本地记忆网络 |
| 每日记忆 Markdown | 可以生成每日 `.md` 记忆文件，并展示在记忆图谱 |
| 执行记录 | 记录任务历史、角色轨迹、工具调用、文件上下文和执行摘要 |
| 命令和文件工具 | 支持读目录、读写文件、分析代码、执行命令、查看 Git 状态 |
| Docker 打包 | 新增 `Dockerfile`、`docker-compose.yml`、`.env.example` |

## 打开地址

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

默认 Admin Token：

```text
admin
```

## 部署方式

Docker Compose：

```bash
cp .env.example .env
docker compose up -d --build
```

Windows 本机直接启动：

```powershell
.\start-p3394.cmd
```

详细部署、模型配置、端口说明和常见问题请看 [README.md](./README.md)。
