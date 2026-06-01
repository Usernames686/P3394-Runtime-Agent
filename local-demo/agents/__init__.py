"""
工作流注册模块

在此文件中导入所有工作流，确保它们被注册到 WorkflowRegistry。
添加新工作流时，只需在此文件中添加导入语句即可。
"""

# 导入所有工作流（确保它们被注册）
from .hello_world import workflow as hello_world_workflow

# 导出所有工作流（可选，方便外部访问）
__all__ = [
    "hello_world_workflow",
]
# AgentClaw template import: p3394_runtime_agent
from .p3394_runtime_agent.agents.p3394_runtime_agent import workflow as p3394_runtime_agent_workflow  # noqa: F401
# AgentClaw template import: tool_agent
from .tool_agent.agents.tool_agent import workflow as tool_agent_workflow  # noqa: F401
# AgentClaw template import: doc_analyzer
from .doc_analyzer.agents.doc_analyzer import workflow as doc_analyzer_workflow  # noqa: F401
# AgentClaw template import: router
from .router.agents.router import workflow as router_workflow  # noqa: F401
# AgentClaw template import: parallel
from .parallel.agents.parallel import workflow as parallel_workflow  # noqa: F401
# AgentClaw template import: approval
from .approval.agents.approval import workflow as approval_workflow  # noqa: F401
# AgentClaw template import: custom_demo
from .custom_demo.agents.custom_demo import workflow as custom_demo_workflow  # noqa: F401
# AgentClaw template import: kb_rag
from .kb_rag.agents.kb_rag import workflow as kb_rag_workflow  # noqa: F401
