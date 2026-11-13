"""
Retriever agent. Executes the orchestrator's plan by calling the
governed MCP tool wrappers. Every call passes through the trajectory
monitor. If a call is blocked, the retriever records that fact and
continues with whatever it was able to gather rather than crashing the
whole run.
"""
from agents import tools


def run_retriever(state, monitor):
    plan = state["plan"] or {}
    agent_role = "retriever"

    for domain in plan.get("domains_to_search", ["all"]):
        query = plan.get("search_queries", [state["task"]])[0]
        result = tools.search_documents(monitor, agent_role, query, domain=domain)
        _record_governance_event(state, monitor, result)
        if not result["blocked"] and isinstance(result["result"], list):
            state["retrieved_documents"].extend(result["result"])

    if plan.get("check_database") and plan.get("database_table"):
        result = tools.query_database(monitor, agent_role, plan["database_table"])
        _record_governance_event(state, monitor, result)
        if not result["blocked"] and isinstance(result["result"], list):
            state["retrieved_records"].extend(result["result"])

    if plan.get("needs_web_search"):
        for query in plan.get("search_queries", [])[:2]:
            result = tools.search_web(monitor, agent_role, query)
            _record_governance_event(state, monitor, result)
            if not result["blocked"] and isinstance(result["result"], list):
                state["web_results"].extend(result["result"])

    state["messages"].append({
        "role": "retriever",
        "content": (
            f"Retrieved {len(state['retrieved_documents'])} documents, "
            f"{len(state['retrieved_records'])} database records, "
            f"{len(state['web_results'])} web results."
        ),
    })
    return state


def _record_governance_event(state, monitor, tool_result):
    decision = tool_result["decision"]
    event = {
        "step": len(state["governance_events"]) + 1,
        "agent_role": decision["action"]["agent_role"],
        "tool_name": decision["action"]["tool_name"],
        "decision": decision["decision"],
        "risk_score": decision["risk_score"],
        "source": decision["source"],
        "reason": decision["reason"],
        "blocked": tool_result["blocked"],
    }
    state["governance_events"].append(event)
    state["trajectory"] = list(monitor.trajectory)
