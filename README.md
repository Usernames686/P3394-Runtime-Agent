# P3394 Runtime Agent

本项目基于 [`Negai-ai/AgentClaw`](https://github.com/Negai-ai/AgentClaw) 二次开发。

P3394 Runtime Agent is a local general-purpose agent platform packaged on top of AgentClaw. It keeps AgentClaw's workflow runtime, tool execution, model configuration, knowledge base, scheduler, tracing, Admin API, and dashboard, while making the P3394 Runtime Agent the default main entry.

This project supports two deployment modes:

- Docker Compose: one command starts the app, PostgreSQL, Redis, Milvus, MinIO, and Adminer.
- Direct local deployment: run the Python service directly for Windows/local development.

## What You Get

- P3394 Runtime Agent as the default agent.
- AgentClaw dashboard and original workflow runtime.
- Local file, command, tool, and artifact execution paths.
- Local knowledge base and memory graph pages.
- Model configuration through `models.json` or dashboard settings.
- Docker Compose deployment and direct Python deployment.

## Quick Access

After startup, open:

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

Default Admin Token:

```text
admin
```

For any public or shared deployment, change `ADMIN_TOKEN` in `.env`.

## Deployment Option 1: Docker Compose

### Requirements

- Docker Desktop or Docker Engine with Compose v2.
- At least 4 GB available memory is recommended because Milvus and MinIO are included.

### 1. Create Environment Config

```bash
cp .env.example .env
```

Edit `.env` and fill in your model provider:

```env
ADMIN_TOKEN=admin
P3394_MODEL_NAME=gpt-4o-mini
P3394_MODEL_BASE_URL=https://api.openai.com/v1
P3394_MODEL_API_KEY=your-model-api-key
```

If your provider does not require a custom base URL, leave `P3394_MODEL_BASE_URL` empty.

### 2. Start

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f app
```

Open:

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

### 3. Stop, Restart, Upgrade

Stop:

```bash
docker compose down
```

Restart:

```bash
docker compose restart app
```

Upgrade after pulling new code:

```bash
git pull
docker compose up -d --build
```

Remove all Docker data volumes:

```bash
docker compose down -v
```

This deletes PostgreSQL, Redis, Milvus, MinIO, and app runtime data.

### Docker Services

| Service | Default URL / Port | Purpose |
| --- | --- | --- |
| P3394 App | `http://127.0.0.1:8000` | Dashboard and API |
| PostgreSQL | `127.0.0.1:5432` | State, tracing, task, and metadata storage |
| Redis | `127.0.0.1:6379` | Cache, locks, and hot updates |
| Milvus | `127.0.0.1:19530` | Vector knowledge base |
| MinIO API | `127.0.0.1:9000` | Object storage |
| MinIO Console | `http://127.0.0.1:9001` | Object storage UI |
| Adminer | `http://127.0.0.1:8080` | Database UI |

If a port is occupied, edit `.env`, for example:

```env
APP_PORT=18000
PG_PORT=15432
REDIS_PORT=16379
ADMINER_PORT=18080
```

## Deployment Option 2: Direct Local Deployment

### Windows One-Click Startup

From the repository root:

```powershell
.\start-p3394.cmd
```

Then open:

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

### Manual Windows Startup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Prepare model config if it does not exist:

```powershell
Copy-Item local-demo\models.example.json local-demo\models.json
```

Edit `local-demo\models.json`, or use the dashboard model settings after startup.

Start the service:

```powershell
$env:AGENTCLAW_PROJECT_DIR = "$PWD\local-demo"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -X utf8 -m agentclaw.cli serve -d local-demo --host 127.0.0.1 --port 8000
```

### macOS / Linux Startup

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e .
cp local-demo/models.example.json local-demo/models.json
AGENTCLAW_PROJECT_DIR="$PWD/local-demo" ./.venv/bin/python -X utf8 -m agentclaw.cli serve -d local-demo --host 127.0.0.1 --port 8000
```

## Model Configuration

The real model config lives at:

```text
local-demo/models.json
```

The committed template is:

```text
local-demo/models.example.json
```

Docker Compose uses these `.env` variables through `models.example.json`:

```env
P3394_MODEL_NAME=gpt-4o-mini
P3394_MODEL_BASE_URL=https://api.openai.com/v1
P3394_MODEL_API_KEY=your-model-api-key
```

Direct deployment can edit `local-demo/models.json` directly:

```json
{
  "default": "p3394_default",
  "models": [
    {
      "id": "p3394_default",
      "channel": "openai",
      "type": "chat",
      "model": "gpt-4o-mini",
      "base_url": "https://api.openai.com/v1",
      "api_key": "your-model-api-key"
    }
  ]
}
```

Do not commit real `.env`, `models.json`, databases, logs, or runtime folders.

## Project Structure

```text
.
|-- Dockerfile
|-- docker-compose.yml
|-- .env.example
|-- start-p3394.cmd
|-- scripts/start-p3394.ps1
|-- agentclaw/
|   |-- admin-dashboard/
|   |-- agent_square/p3394_runtime_agent/
|   |-- api/
|   |-- mcp/
|-- local-demo/
|   |-- agents/p3394_runtime_agent/
|   |-- models.example.json
|   |-- server.py
|-- docs/
|   |-- P3394-Agent-Platform.md
|   |-- P3394-Runtime-Agent.md
```

## Common Commands

Backend checks:

```powershell
.\.venv\Scripts\python.exe -m pytest agentclaw/test/unit/test_cli_init.py agentclaw/test/unit/test_docker_ports.py -q
```

Frontend checks:

```powershell
cd agentclaw\admin-dashboard
npm test -- src/__tests__/p3394-model-diagnostics.spec.js src/__tests__/agent-square.spec.js src/__tests__/memory-graph.spec.js
```

Build frontend:

```powershell
cd agentclaw\admin-dashboard
npm run build
```

Verify the P3394 API:

```bash
curl -H "Authorization: Bearer admin" http://127.0.0.1:8000/admin/p3394/artifacts
```

## Troubleshooting

### The dashboard asks for Admin Token

Use:

```text
admin
```

If you changed `.env`, use the value of `ADMIN_TOKEN`.

### The model does not respond

<<<<<<< HEAD
- 把 P3394 任务历史、工具记录和文件上下文做成简洁侧栏。
- 做一个初始化向导：检查模型、P3394 模板、命令工具、搜索工具是否可用。
- 把 P3394 内部 Planner / Researcher / Executor / Reviewer 从“记录轨迹”升级为更真实的多 Agent 协作。
=======
Check:

- `P3394_MODEL_API_KEY` or `local-demo/models.json` has a real key.
- `P3394_MODEL_BASE_URL` is an OpenAI-compatible `/v1` endpoint when needed.
- `P3394_MODEL_NAME` is available to your key.

Restart after editing config.

### Docker Compose says a port is already allocated

Edit `.env` and change the conflicting port, then run:

```bash
docker compose up -d
```

### Knowledge base is unavailable

For Docker Compose:

```bash
docker compose ps
```

Make sure `milvus`, `minio`, and `postgres` are running.

For direct Windows deployment, use Docker/remote Milvus and configure `MILVUS_URI`, or use Docker Compose for the full stack.

## Security Notes

The default `ADMIN_TOKEN=admin` is for local use. Before exposing this service, change:

```env
ADMIN_TOKEN=change-me
WORKFLOW_API_KEY=change-me
MCP_TOKEN=change-me
PG_PASSWORD=change-me
MINIO_ROOT_PASSWORD=change-me
```

Use a private network, VPN, or reverse proxy authentication for shared deployments.
>>>>>>> bdc9b72 (feat: add docker compose deployment)
