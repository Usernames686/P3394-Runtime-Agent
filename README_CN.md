# P3394 Runtime Agent

这是你的 P3394 通用智能体平台，基于 AgentClaw 二次包装，默认入口是 P3394 Runtime Agent。

打开地址：

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

默认 Admin Token：

```text
admin
```

支持两种部署方式：

- Docker Compose：复制 `.env.example` 为 `.env`，填写模型配置，然后运行 `docker compose up -d --build`。
- 本机直接部署：Windows 运行 `.\start-p3394.cmd`，或用 Python 虚拟环境运行 `agentclaw.cli serve -d local-demo`。

详细部署、模型配置、端口说明和常见问题请看 [README.md](./README.md)。
