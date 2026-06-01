# P3394 Local Workspace

`local-demo` is the default runtime workspace for P3394 Runtime Agent.

Start from the repository root:

```powershell
.\start-p3394.cmd
```

Open:

```text
http://127.0.0.1:8000/dashboard/p3394-agent
```

Default Admin Token:

```text
admin
```

## Files

```text
local-demo/
|-- agents/
|   |-- p3394_runtime_agent/   # Main P3394 agent
|   |-- __init__.py            # Workflow registration
|-- models.example.json        # Safe model template
|-- models.json                # Real local model config, ignored by git
|-- mcp.json                   # MCP config
|-- server.py                  # Service entry
|-- .env                       # Local runtime config, ignored by git
|-- .agentclaw/                # Runtime data, ignored by git
|-- logs/                      # Logs, ignored by git
```

For first-time direct deployment:

```powershell
Copy-Item local-demo\models.example.json local-demo\models.json
```

Then edit `local-demo\models.json`, or configure models in the dashboard.
