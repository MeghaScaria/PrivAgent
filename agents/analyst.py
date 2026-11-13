"""
Analyst agent. Takes whatever the retriever gathered and produces a
synthesis. Also decides whether the analysis was built from sensitive
material, which the writer agent needs to know before it can propose
sending anything externally.
"""
import json
from pydantic import BaseModel, Field
from agents.llm import get_llm


class AnalysisOutput(BaseModel):
    analysis: str = Field(description="A synthesis of the retrieved information relevant to the task")
    contains_sensitive_data: bool = Field(
        description="True if the analysis draws on HR, salary, or financial account information"
    )
    key_findings: list[str] = Field(description="2 to 4 short bullet-point findings")


ANALYST_PROMPT = """You are the analyst agent in a multi-agent research assistant. \
Synthesise the retrieved information below into a clear analysis that answers \
the original task.

Original task: {task}

Retrieved documents:
{documents}

Retrieved database records:
{records}

Retrieved web results:
{web_results}

Mark contains_sensitive_data as true if the analysis relies on HR records, \
salaries, or financial account/transaction details."""


# How many retrieved items of each kind go into the analyst's prompt.
# The handoff instrumentation uses the same limits to record exactly
# what the analyst read.
ANALYST_INPUT_LIMITS = {"retrieved_documents": 10, "retrieved_records": 10, "web_results": 5}


def analyst_inputs(state):
    return {field: state[field][:limit] for field, limit in ANALYST_INPUT_LIMITS.items()}


def run_analyst(state, llm=None):
    llm = llm or get_llm()
    structured_llm = llm.with_structured_output(AnalysisOutput)
    inputs = analyst_inputs(state)

    output: AnalysisOutput = structured_llm.invoke(
        ANALYST_PROMPT.format(
            task=state["task"],
            documents=json.dumps(inputs["retrieved_documents"], indent=2) or "none",
            records=json.dumps(inputs["retrieved_records"], indent=2) or "none",
            web_results=json.dumps(inputs["web_results"], indent=2) or "none",
        )
    )

    state["analysis"] = output.analysis
    state["analysis_contains_sensitive_data"] = output.contains_sensitive_data
    state["messages"].append({
        "role": "analyst",
        "content": f"Analysis complete. Sensitive data involved: {output.contains_sensitive_data}. "
                   f"Key findings: {'; '.join(output.key_findings)}",
    })
    return state
