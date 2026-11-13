"""Page 4: Human Approval. Lists runs paused for review in the persistent
approval store (runtime/approvals) and lets a reviewer approve or reject
each pending external transmission. Decisions go through the backend
approval workflow unchanged: the page only says approve or reject for
the request exactly as presented.

Everything here is rendered with Streamlit's escaping widgets (text,
code, dataframes), never as raw HTML, because the payload and the
evidence come from agents and tools."""
import streamlit as st

from dashboard import review_queue
from dashboard.components import page_header


@st.cache_resource(show_spinner=False)
def _store():
    return review_queue.open_store()


def _evidence_rows(request):
    rows = []
    for rule, evidence in request["flow_rules_fired"].items():
        for ref in evidence.get("crossed_refs", []):
            rows.append({"rule": rule, "source": ref["source"],
                         "sensitivity": ref["sensitivity"]["value"],
                         "basis": ref["sensitivity"]["basis"], "obtained by": ref["produced_by"]})
        if not evidence.get("crossed_refs"):
            rows.append({"rule": rule, "source": evidence.get("reason"), "sensitivity": None,
                         "basis": None, "obtained by": None})
    return rows


def _pending_card(thread_id, request, reviewer):
    gov = request["governance"]
    sens = gov.get("sensitivity") or {}
    with st.container(border=True):
        st.markdown(f"**{request['tool']}** to destination `{request['destination']}`")
        st.text(f"Run {request['run_id']}  ·  action {request['action_id']}  ·  agent {request['agent_role']}")
        st.text(f"Why review: {request['decided_by']} ({request['final_decision']}). "
                f"Risk model: {gov['decision']} at {gov['risk_score']:.3f}. {gov['reason']}")
        if sens:
            st.text(f"Sensitivity: declared by agent {sens.get('declared')}, "
                    f"provenance {sens['provenance'].get('value')} ({sens['provenance'].get('basis')}), "
                    f"authoritative {sens.get('authoritative')}")
        if gov.get("flags"):
            st.warning("Flags: " + ", ".join(gov["flags"]))
        rows = _evidence_rows(request)
        if rows:
            st.caption("Provenance: data from other agents that this transmission traces back to")
            st.dataframe(rows, hide_index=True, width="stretch")
        if not request["payload_matches_gated_action"]:
            st.error("The payload no longer matches the one that was gated. "
                     "An approval of it will be rejected.")
        st.caption("Exact payload to be sent")
        st.code(request["payload"], language=None)

        c1, c2, _ = st.columns([1, 1, 4])
        disabled = not reviewer
        if c1.button("Approve", key=f"approve-{request['action_id']}", type="primary", disabled=disabled):
            st.session_state["review_result"] = review_queue.decide(_store(), thread_id, "approve", reviewer)
            st.rerun()
        if c2.button("Reject", key=f"reject-{request['action_id']}", disabled=disabled):
            st.session_state["review_result"] = review_queue.decide(_store(), thread_id, "reject", reviewer)
            st.rerun()


def _show_last_result():
    result = st.session_state.pop("review_result", None)
    if not result:
        return
    if result["status"] == "no_pending":
        st.info("That request had already been decided; nothing was submitted.")
    elif result["executed"]:
        st.success(f"Approved: action {result['action_id'][:8]} was sent once "
                   f"(ledger: {result['ledger']}).")
    else:
        st.warning(f"Action {result['action_id'][:8]} was not sent: {result['approval']} "
                   f"({result['reason']}). {result['halt_reason'] or ''}")


def render():
    page_header(
        "Human Approval",
        "External transmissions that governance sent for review. Nothing below "
        "has been sent: approve to send it once, or reject to stop it.",
    )
    _show_last_result()

    reviewer = st.text_input("Reviewer name (recorded in the audit log)",
                             key="reviewer_name").strip()
    if not reviewer:
        st.caption("Enter a reviewer name to enable Approve and Reject.")

    pending = review_queue.list_pending(_store())
    st.markdown(f"#### Pending ({len(pending)})")
    if not pending:
        st.caption("No runs are waiting for review.")
    for thread_id, request in pending:
        _pending_card(thread_id, request, reviewer)

    st.markdown("#### Start a demo run")
    st.caption("Synthetic data and a scripted LLM; no API key needed. "
               "Runs that need review appear in the list above.")
    labels = {k: v[0] for k, v in review_queue.DEMO_SCENARIOS.items()}
    key = st.selectbox("Demo scenario", options=list(labels), format_func=labels.get)
    if st.button("Start run"):
        with st.spinner("Running..."):
            outcome = review_queue.start_demo(_store(), key)
        if outcome["paused"]:
            st.session_state["review_result"] = None
            st.rerun()
        elif outcome["halted"]:
            st.warning(f"Run finished without review and was stopped: {outcome['halt_reason']}")
        else:
            st.success("Run finished without needing review.")

    st.markdown("#### Recent decisions")
    rows = review_queue.recent_decisions()
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.caption("No decisions yet.")

    with st.expander("External server (synthetic): transmissions received"):
        sent = review_queue.external_transmissions()
        st.text(f"{len(sent)} transmission(s) received in this session")
        if sent:
            st.dataframe(sent, hide_index=True, width="stretch")
