"""
Writer agent. Produces the final natural-language answer from the
analyst's synthesis. If the writer decides the result should also be
sent to an external destination (simulating, e.g., emailing a report
out), that call goes through send_result — the governed transmission
endpoint — carrying forward whether the underlying analysis touched
sensitive data. This is typically the step where governance actually
intervenes.
"""
from pydantic import BaseModel, Field
from agents.llm import get_llm
from agents import tools


class WriterOutput(BaseModel):
    final_answer: str = Field(description="The final answer to present to the user")
    should_transmit_externally: bool = Field(
        description="True only if the task explicitly asks to send, export, email, or share the result externally"
    )


WRITER_PROMPT = """You are the writer agent in a multi-agent research assistant. \
Produce the final answer to the user's original task, based on the analyst's \
synthesis below.

Original task: {task}

Analyst synthesis: {analysis}

Only set should_transmit_externally to true if the task itself asked to send, \
export, email, or share the result somewhere external. Otherwise leave it false \
-- most tasks just want an answer, not a transmission."""


def compose_answer(state, llm=None):
    """The writer's LLM step: the final answer and whether to transmit it.
    No tool calls, so it's safe to run in a node of its own before the
    approval workflow."""
    llm = llm or get_llm()
    structured_llm = llm.with_structured_output(WriterOutput)
    output: WriterOutput = structured_llm.invoke(
        WRITER_PROMPT.format(task=state["task"], analysis=state["analysis"] or "No analysis available.")
    )
    state["final_output"] = output.final_answer
    return output


def run_writer(state, monitor, llm=None):
    output = compose_answer(state, llm)

    if output.should_transmit_externally:
        result = tools.send_result(
            monitor, "writer", output.final_answer,
            contains_sensitive_data=state.get("analysis_contains_sensitive_data", False),
        )
        decision = result["decision"]
        event = {
            "step": len(state["governance_events"]) + 1,
            "agent_role": "writer",
            "tool_name": "send_result",
            "decision": decision["decision"],
            "risk_score": decision["risk_score"],
            "source": decision["source"],
            "reason": decision["reason"],
            "blocked": result["blocked"],
        }
        state["governance_events"].append(event)
        state["trajectory"] = list(monitor.trajectory)

        if result["blocked"]:
            state["task_halted"] = True
            state["halt_reason"] = (
                f"Governance blocked the external transmission step: {decision['reason']}"
            )

    state["messages"].append({"role": "writer", "content": "Final answer produced."})
    return state
