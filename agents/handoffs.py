"""
Handoff instrumentation for the LangGraph pipeline. Agents pass data to
each other only through the shared state; HandoffTracker records each of
those transfers with the monitor (TrajectoryMonitor.record_handoff),
including which data refs moved, what the receiver actually reads, and
where that data originally came from.

The tracker runs after each node returns, from the wrappers in
agents/graph.py. It only reads the state, never changes it, so agents
behave exactly as without it. Events are shadow-mode: logged, never
scored or enforced.

What each handoff carries (and what the receiver reads):
  user -> orchestrator      the task
  orchestrator -> retriever the retrieval plan (+ task)
  retriever -> analyst      retrieved documents, records, web results;
                            the analyst reads only the first
                            ANALYST_INPUT_LIMITS of each (+ task)
  analyst -> writer         the analysis, built from what the analyst
                            read, and its self-reported sensitivity (+ task)
  writer -> external_server the final answer, via the governed
                            send_result call, when the writer transmits
  writer -> user            the final answer

If an earlier hook failed and left no ref for something (the task, the
analysis), later hooks fall back to an "unregistered" ref with unknown
sensitivity, so the handoff is still recorded and flagged rather than
dropped or assumed safe.
"""
from agents.analyst import ANALYST_INPUT_LIMITS, analyst_inputs
from governance.sensitivity import assess_text

# The declared pipeline. A handoff on any other edge is recorded with
# authorized=False (shadow mode: flagged, never blocked).
PIPELINE_HANDOFFS = {
    ("user", "orchestrator"),
    ("orchestrator", "retriever"),
    ("retriever", "analyst"),
    ("analyst", "writer"),
    ("writer", "external_server"),
    ("writer", "user"),
}
SENSITIVE_DOMAINS = {"hr", "finance", "all"}


class HandoffTracker:
    def __init__(self, monitor):
        self.monitor = monitor
        self.enabled = monitor.handoff_mode != "off"
        self.task_ref = None
        self.analysis_ref = None
        self._decisions_before_writer = 0

    def _handoff(self, event_type, sender, receiver, payload, **kwargs):
        return self.monitor.record_handoff(
            event_type, sender, receiver, payload,
            authorized=(sender, receiver) in PIPELINE_HANDOFFS, **kwargs)

    def _task(self, state):
        if self.task_ref is None:
            self.task_ref = self.monitor.provenance.lookup(state["task"])
        return self.task_ref

    def _analyst_read(self, state):
        reg = self.monitor.provenance
        read = [reg.lookup(item) for items in analyst_inputs(state).values() for item in items]
        return read + [self._task(state)]

    def task_received(self, state):
        if not self.enabled:
            return
        reg = self.monitor.provenance
        self.task_ref = reg.register_root("task", "user", assess_text(state["task"], "user_input"),
                                          content=state["task"])
        self._handoff("input", "user", "orchestrator", {"task": [self.task_ref]})

    def after_orchestrator(self, state):
        if not self.enabled:
            return
        plan = state["plan"] or {}
        task_ref = self._task(state)
        plan_ref = self.monitor.provenance.derive("plan", "orchestrator", [task_ref], content=plan)
        requests_sensitive = bool(
            SENSITIVE_DOMAINS & set(plan.get("domains_to_search", []))
            or (plan.get("check_database") and plan.get("database_table")))
        self._handoff(
            "handoff", "orchestrator", "retriever",
            {"plan": [plan_ref], "task": [task_ref]}, produced_ref=plan_ref,
            details={"requests_sensitive_access": requests_sensitive,
                     "domains": plan.get("domains_to_search", []),
                     "database_table": plan.get("database_table") if plan.get("check_database") else None,
                     "web_search": plan.get("needs_web_search", False)})

    def after_retriever(self, state):
        if not self.enabled:
            return
        reg = self.monitor.provenance
        payload = {field: [reg.lookup(item) for item in state[field]]
                   for field in ANALYST_INPUT_LIMITS}
        read = self._analyst_read(state)
        payload["task"] = [self._task(state)]
        self._handoff(
            "handoff", "retriever", "analyst", payload, consumed=read,
            details={"handed_over": {f: len(r) for f, r in payload.items()},
                     "read_by_receiver": len(read) - 1,
                     "input_limits": ANALYST_INPUT_LIMITS})

    def after_analyst(self, state):
        if not self.enabled:
            return
        reg = self.monitor.provenance
        # The retrieved lists are unchanged by the analyst, so what it read
        # can be recomputed here rather than relying on the earlier hook.
        self.analysis_ref = reg.derive("analysis", "analyst", self._analyst_read(state),
                                       content=state["analysis"])
        inherited = reg.refs[self.analysis_ref]["sensitivity"]["value"]
        self_report = bool(state["analysis_contains_sensitive_data"])
        flags = []
        if inherited is not None and int(self_report) != inherited:
            flags.append("self_report_disagrees_with_provenance")
        self._handoff(
            "handoff", "analyst", "writer",
            {"analysis": [self.analysis_ref], "task": [self._task(state)]},
            produced_ref=self.analysis_ref, flags=flags,
            details={"self_reported_sensitive": self_report,
                     "provenance_sensitive": inherited})

    def remember_analysis(self, state):
        """Makes sure the analysis has a ref before the approval graph drops
        its text from state (normally after_analyst has done this)."""
        if self.enabled and self.analysis_ref is None and state.get("analysis") is not None:
            self.analysis_ref = self.monitor.provenance.lookup(state["analysis"])

    def before_writer(self):
        self._decisions_before_writer = len(self.monitor.decisions)

    def after_writer(self, state):
        if not self.enabled:
            return
        reg = self.monitor.provenance
        analysis_ref = self.analysis_ref or reg.lookup(state["analysis"])
        answer_ref = reg.derive("final_answer", "writer", [analysis_ref, self._task(state)],
                                content=state["final_output"])
        provenance_sensitive = reg.refs[answer_ref]["sensitivity"]["value"]
        for d in self.monitor.decisions[self._decisions_before_writer:]:
            if d.action["tool_name"] != "send_result":
                continue
            declared = d.action["data_sensitivity"]
            flags = []
            if provenance_sensitive == 1 and declared == 0:
                flags.append("declared_sensitivity_lower_than_provenance")
            self._handoff(
                "transmission", "writer", "external_server", {"payload": [answer_ref]},
                flags=flags,
                details={"tool_event_id": d.event_id, "decision": d.decision,
                         "executed": getattr(d, "execution", {}).get("executed", d.allowed),
                         "approval": getattr(d, "execution", {}).get("approval"),
                         "declared_sensitivity": declared,
                         "provenance_sensitive": provenance_sensitive})
        self._handoff("delivery", "writer", "user", {"final_output": [answer_ref]})
