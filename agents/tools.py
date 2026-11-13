"""
Thin wrappers around the MCP tools that route every proposed call
through the TrajectoryMonitor first. This is where governance actually
happens: the wrapper asks "is this allowed?" before it ever reaches the
MCP client, and returns a structured result either way so the calling
agent (and the dashboard) can see exactly what happened.
"""
from agents.mcp_client import get_mcp_manager, server_identity

def _blocked_response(decision):
    return {
        "blocked": True,
        "decision": decision.to_dict(),
        "result": None,
    }


def _allowed_response(decision, result):
    return {
        "blocked": False,
        "decision": decision.to_dict(),
        "result": result,
    }


def _call(monitor, decision, tool_name, args):
    """Runs an allowed MCP call and registers what it returned with the
    monitor's provenance registry. The result itself is returned
    unchanged."""
    raw = get_mcp_manager().call_tool(tool_name, args)
    monitor.register_tool_result(decision, tool_name, args, raw)
    return raw


def _governed_call(monitor, agent_role, tool_name, action_type, data_sensitivity,
                    destination_category, mcp_args=None):
    """Lower-level primitive: evaluates governance using the EXACT feature
    values given (rather than inferring sensitivity/destination from the
    call arguments), then executes the real MCP call if allowed. Used by
    the attack scenario replay engine so live demo runs reproduce the
    exact patterns the risk models were trained and evaluated on."""
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name=tool_name, action_type=action_type,
        data_sensitivity=data_sensitivity, destination_category=destination_category,
    )
    if not decision.allowed:
        return _blocked_response(decision)
    if mcp_args is None:
        return _allowed_response(decision, None)
    raw = _call(monitor, decision, tool_name, mcp_args)
    return _allowed_response(decision, raw)


def search_documents(monitor, agent_role, query, domain="all"):
    sensitivity = 1 if domain in ("hr", "finance", "all") else 0
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name="search_documents", action_type="read",
        data_sensitivity=sensitivity, destination_category="internal",
    )
    if not decision.allowed:
        return _blocked_response(decision)
    raw = _call(monitor, decision, "search_documents", {"query": query, "domain": domain})
    return _allowed_response(decision, raw)


def retrieve_document(monitor, agent_role, doc_id):
    sensitivity = 1 if (doc_id.startswith("hr_") or doc_id.startswith("finance_")) else 0
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name="retrieve_document", action_type="read",
        data_sensitivity=sensitivity, destination_category="internal",
    )
    if not decision.allowed:
        return _blocked_response(decision)
    raw = _call(monitor, decision, "retrieve_document", {"doc_id": doc_id})
    return _allowed_response(decision, raw)


def query_database(monitor, agent_role, table, filters=""):
    sensitivity = 1 if table in ("employees", "transactions") else 0
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name="query_database", action_type="query",
        data_sensitivity=sensitivity, destination_category="internal",
    )
    if not decision.allowed:
        return _blocked_response(decision)
    raw = _call(monitor, decision, "query_database", {"table": table, "filters": filters})
    return _allowed_response(decision, raw)


def list_tables(monitor, agent_role):
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name="list_tables", action_type="read",
        data_sensitivity=0, destination_category="internal",
    )
    if not decision.allowed:
        return _blocked_response(decision)
    raw = _call(monitor, decision, "list_tables", {})
    return _allowed_response(decision, raw)


def search_web(monitor, agent_role, query):
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name="search_web", action_type="read",
        data_sensitivity=0, destination_category="internal",
    )
    if not decision.allowed:
        return _blocked_response(decision)
    raw = _call(monitor, decision, "search_web", {"query": query})
    return _allowed_response(decision, raw)


def send_result(monitor, agent_role, payload, destination="external",
                 contains_sensitive_data=False):
    """destination_category passed to the risk model is always 'external'
    for this tool, since send_result is the outbound transmission
    endpoint by definition. contains_sensitive_data is what the sending
    agent declares about the payload; the monitor checks it against
    provenance (see TrajectoryMonitor.evaluate)."""
    decision = evaluate_send(monitor, agent_role, contains_sensitive_data)
    if not decision.allowed:
        return _blocked_response(decision)
    raw = execute_send(monitor, decision, payload, destination)
    return _allowed_response(decision, raw)


def evaluate_send(monitor, agent_role, contains_sensitive_data):
    """The governance half of send_result. The approval workflow
    (governance/approval.py) evaluates first and executes only once a
    reviewer has approved."""
    return monitor.evaluate(
        agent_role=agent_role, tool_name="send_result", action_type="transmit",
        data_sensitivity=1 if contains_sensitive_data else 0,
        destination_category="external", check_sensitivity=True,
    )


class SendBindingError(RuntimeError):
    """v2: the send about to be made is not the one that was approved."""


def execute_send(monitor, decision, payload, destination="external", binding=None):
    """The MCP half of send_result. Callers must have checked that the
    decision (or a verified human approval) permits it.

    binding (v2, optional): (ApprovalService, pending action). The binding
    digest over tool, destination, server identity and payload is
    recomputed from THIS call's arguments and the client's current routing
    right before the MCP call; any mismatch raises SendBindingError and
    nothing is sent. Without it (v1), behaviour is unchanged."""
    if binding is not None:
        service, pending = binding
        ok, reason = service.verify_binding(pending, "send_result", destination,
                                            server_identity("send_result"), payload)
        if not ok:
            raise SendBindingError(reason)
    return _call(monitor, decision, "send_result", {"payload": payload, "destination": destination})


def get_transmission_log(monitor, agent_role):
    decision = monitor.evaluate(
        agent_role=agent_role, tool_name="get_transmission_log", action_type="read",
        data_sensitivity=0, destination_category="internal",
    )
    if not decision.allowed:
        return _blocked_response(decision)
    raw = _call(monitor, decision, "get_transmission_log", {})
    return _allowed_response(decision, raw)
