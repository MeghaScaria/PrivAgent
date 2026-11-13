"""
The shared state object that flows through every node in the LangGraph
graph. Every agent reads from and writes to this single structure, which
is how LangGraph tracks progress through the pipeline.
"""
from typing import TypedDict, List, Dict, Any, Optional


class GovernanceEvent(TypedDict):
    step: int
    agent_role: str
    tool_name: str
    decision: str            # AUTONOMOUS / RESTRICTED / HUMAN_APPROVAL / BLOCKED
    risk_score: float
    source: str               # ml_model / policy_engine
    reason: str
    blocked: bool


class AgentState(TypedDict):
    # input
    task: str
    task_type: str             # multi_hop_research / comparative_analysis / data_retrieval / financial_research

    # working memory
    messages: List[Dict[str, str]]      # [{"role": "orchestrator", "content": "..."}]
    plan: Optional[Dict[str, Any]]      # orchestrator's decomposition of the task
    retrieved_documents: List[Dict[str, Any]]
    retrieved_records: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    analysis: Optional[str]
    analysis_contains_sensitive_data: bool
    final_output: Optional[str]

    # governance
    run_id: str
    trajectory: List[Dict[str, Any]]        # executed actions, mirrors TrajectoryMonitor.trajectory
    governance_events: List[GovernanceEvent]  # every decision, including blocked ones
    task_halted: bool                        # True if governance blocked something critical
    halt_reason: Optional[str]

    # human approval (only used by the approval graph, see governance/approval.py)
    transmission_request: Optional[Dict[str, Any]]  # what the writer asked to send
    pending_action: Optional[Dict[str, Any]]        # the gated action, as presented for review
    approval: Optional[Dict[str, Any]]              # the reviewer's validated response


def new_state(task: str, task_type: str = "multi_hop_research", run_id: str = "") -> AgentState:
    return AgentState(
        task=task,
        task_type=task_type,
        messages=[],
        plan=None,
        retrieved_documents=[],
        retrieved_records=[],
        web_results=[],
        analysis=None,
        analysis_contains_sensitive_data=False,
        final_output=None,
        run_id=run_id,
        trajectory=[],
        governance_events=[],
        task_halted=False,
        halt_reason=None,
        transmission_request=None,
        pending_action=None,
        approval=None,
    )
