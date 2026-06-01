# P3394 Runtime Agent

This built-in AgentClaw template is a runnable, P3394-inspired agent runtime.
It keeps AgentClaw's original workflow model, but adds a thin runtime layer that
models the ideas from the local P3394 v0.9.0 draft:

- agent manifest
- channel adapter boundary
- UMF-style message envelope
- session create and context fetch
- session close
- relationship-based capability access
- audit event recording and summary
- task routing and explicit workflow delegation
- AgentClaw agentic LLM execution
- built-in command/file/code tools and skills
- conformance checklist

The runtime keeps deterministic handlers for protocol-level commands such as
`manifest.describe`, `message.normalize`, `session.create`,
`session.fetch`, `session.close`, `task.route`, `agent.delegate`,
`audit.summary`, and `conformance.check`. Ordinary user requests are first
routed to an AgentClaw target family, then passed to an AgentClaw `LLMNode`
configured like the built-in AgentClaw assistant when local agentic execution is
the selected route:
`agent_style="agentic"`, `tools="*"`, `skills="*"`,
`enable_builtin_tools=True`, `enable_builtin_skills=True`, and memory enabled.

That means the P3394 layer is not only a chat interface. With a configured LLM
model, it can use AgentClaw's built-in tools to inspect files, run shell
commands, edit code, call MCP tools, and verify work.

## Example Inputs

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

You can also pass an optional `umf_message` object when invoking the workflow
through the API. The agent will preserve caller-supplied session identity fields
when building its normalized envelope.

For explicit delegation, pass a UMF-style body with:

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
