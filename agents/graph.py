"""
Builds the LangGraph StateGraph connecting orchestrator -> retriever ->
analyst -> writer. The TrajectoryMonitor (and, for testing, a fake LLM)
are captured via closures rather than stored in state, since state is
meant to stay plain data that the dashboard can display and serialise.

Each node wrapper also tells a HandoffTracker (agents/handoffs.py) what
the agent just handed to the next one. The tracker only reads state,
and any error inside it is caught and recorded on the monitor, so
instrumentation can never change or interrupt the agents' work.
"""
import logging
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.orchestrator import run_orchestrator
from agents.retriever import run_retriever
from agents.analyst import run_analyst
from agents.writer import run_writer
from agents.handoffs import HandoffTracker
from agents.approval_flow import make_nodes as make_approval_nodes

log = logging.getLogger(__name__)


def build_graph(monitor, llm=None, approvals=None, checkpointer=None):
    """monitor: a governance.trajectory_monitor.TrajectoryMonitor for this run.
    llm: optional injectable chat model, for testing without a real API key.
    approvals: optional governance.approval.ApprovalService. When given,
      the writer's transmission goes through the human-approval workflow
      (agents/approval_flow.py), which needs a checkpointer and a
      thread_id in every invoke. Without it the graph is unchanged."""
    if approvals is not None and checkpointer is None:
        raise ValueError("The approval workflow needs a checkpointer to pause and resume")
    tracker = HandoffTracker(monitor)
    monitor.instrumentation_errors = []

    def observe(hook, *args):
        try:
            hook(*args)
        except Exception as e:
            log.warning("Handoff instrumentation failed in %s: %s", hook.__name__, e)
            monitor.instrumentation_errors.append(f"{hook.__name__}: {e!r}")

    def orchestrator_node(state: AgentState) -> AgentState:
        observe(tracker.task_received, state)
        state = run_orchestrator(state, llm=llm)
        observe(tracker.after_orchestrator, state)
        return state

    def retriever_node(state: AgentState) -> AgentState:
        state = run_retriever(state, monitor)
        observe(tracker.after_retriever, state)
        return state

    def analyst_node(state: AgentState) -> AgentState:
        state = run_analyst(state, llm=llm)
        observe(tracker.after_analyst, state)
        return state

    def writer_node(state: AgentState) -> AgentState:
        observe(tracker.before_writer)
        state = run_writer(state, monitor, llm=llm)
        observe(tracker.after_writer, state)
        return state

    graph = StateGraph(AgentState)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("analyst", analyst_node)

    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "retriever")
    graph.add_edge("retriever", "analyst")

    if approvals is None:
        graph.add_node("writer", writer_node)
        graph.add_edge("analyst", "writer")
        graph.add_edge("writer", END)
        return graph.compile()

    nodes = make_approval_nodes(monitor, approvals, tracker, observe, llm=llm)
    previous = "analyst"
    for name, fn in nodes.items():
        graph.add_node(name, fn)
        graph.add_edge(previous, name)
        previous = name
    graph.add_edge(previous, END)
    app = graph.compile(checkpointer=checkpointer)
    app.approval_service = approvals
    return app


def run_task(task: str, run_id: str = None, llm=None):
    """Top-level convenience function: runs one full task through the
    governed multi-agent pipeline and returns the final state."""
    import uuid
    from governance.trajectory_monitor import TrajectoryMonitor
    from agents.state import new_state

    run_id = run_id or str(uuid.uuid4())[:8]
    monitor = TrajectoryMonitor(model_type="trajectory", run_id=run_id)
    app = build_graph(monitor, llm=llm)

    state = new_state(task=task, run_id=run_id)
    final_state = app.invoke(state)
    return final_state, monitor
