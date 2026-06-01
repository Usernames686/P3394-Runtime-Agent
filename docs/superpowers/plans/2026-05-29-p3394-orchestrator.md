# P3394 Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing P3394 Runtime Agent from a protocol shell into an AgentClaw-native orchestrator that routes tasks, can delegate to registered workflows, and keeps P3394 audit/session metadata around those decisions.

**Architecture:** Keep `p3394_runtime_agent` as the only new agent. Add `task.route` for deterministic task classification and route planning, add `agent.delegate` for explicit workflow delegation through `WorkflowRegistry`, and keep normal user requests flowing into the existing `LLMNode(agent_style="agentic")` with the selected route embedded in the prompt.

**Tech Stack:** Python 3.11, AgentClaw `Workflow`, `CustomNode`, `WorkflowRegistry`, pytest, existing Vue dashboard tests.

---

### Task 1: Routing Tests

**Files:**
- Modify: `agentclaw/test/unit/test_example_agent_square_templates.py`
- Modify: `agentclaw/agent_square/p3394_runtime_agent/agents/p3394_runtime_agent.py`

- [ ] Write a failing test that `manifest.describe` includes `task.route`, `agent.delegate`, and an orchestration route catalog.
- [ ] Write a failing test that `task.route` maps document, search, code, and general requests to concrete AgentClaw targets or the local agentic runtime.
- [ ] Run the targeted pytest file and confirm the new tests fail for missing orchestration behavior.

### Task 2: Delegation Tests

**Files:**
- Modify: `agentclaw/test/unit/test_example_agent_square_templates.py`
- Modify: `agentclaw/agent_square/p3394_runtime_agent/agents/p3394_runtime_agent.py`

- [ ] Write a failing test that registers a tiny echo workflow, calls `agent.delegate`, and sees a delegated result.
- [ ] Assert the audit event records the selected route and target workflow.
- [ ] Assert unauthorized callers cannot delegate.

### Task 3: Runtime Implementation

**Files:**
- Modify: `agentclaw/agent_square/p3394_runtime_agent/agents/p3394_runtime_agent.py`
- Modify: `agentclaw/agent_square/p3394_runtime_agent/README.md`
- Modify: `agentclaw/agent_square/p3394_runtime_agent/claw_app.json`

- [ ] Add orchestration capabilities and route catalog to the P3394 manifest.
- [ ] Implement `_select_route()` and deterministic `task.route`.
- [ ] Implement explicit `agent.delegate` through `WorkflowRegistry.get(target_workflow_id).run(...)`.
- [ ] Include selected route in the LLM prompt for ordinary authorized tasks.
- [ ] Update README examples and copy the template into `local-demo`.

### Task 4: Verification

**Files:**
- Test: `agentclaw/test/unit/test_example_agent_square_templates.py`
- Test: `agentclaw/test/unit/test_llm_manager_reload.py`
- Test: `agentclaw/admin-dashboard/src/__tests__/agent-square.spec.js`

- [ ] Run Python tests for P3394 and model fallback.
- [ ] Run dashboard Vitest coverage for the P3394 page entry.
- [ ] Run a local API smoke check against `/dashboard/p3394-agent`.
