"""
Orchestrator agent. Reads the user's task and produces a short retrieval
plan: which document domains to search, whether to query the structured
database, whether a web search is needed. This plan drives the retriever
agent. The orchestrator itself does not call any governed tools — it
only reasons over the task text.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from agents.llm import get_llm

TASK_TYPES = ["multi_hop_research", "comparative_analysis", "data_retrieval", "financial_research"]


class RetrievalPlan(BaseModel):
    task_type: Literal[
        "multi_hop_research", "comparative_analysis", "data_retrieval", "financial_research"
    ] = Field(description="Which of the four task categories this request falls into")
    domains_to_search: List[Literal["hr", "finance", "research", "all"]] = Field(
        description="Which document domains are relevant to this request"
    )
    check_database: bool = Field(description="Whether structured database records are needed")
    database_table: Optional[Literal["employees", "transactions"]] = Field(
        default=None, description="Which table to query, if check_database is true"
    )
    needs_web_search: bool = Field(description="Whether external web context would help")
    search_queries: List[str] = Field(
        description="1 to 3 short search queries capturing what to look for", max_length=3
    )


ORCHESTRATOR_PROMPT = """You are the orchestrator agent in a multi-agent research \
assistant. A user has asked a question. Decide what information needs to be \
gathered to answer it well.

User question: {task}

Produce a retrieval plan. Only request database access if the question is \
plausibly about employees, salaries, transactions, or financial records. \
Only request web search if the question needs current or general knowledge \
not likely to be in the internal documents. Keep search queries short, \
specific, and directly derived from the question."""


def run_orchestrator(state, llm=None):
    """llm is injectable for testing; defaults to the real Gemini client."""
    llm = llm or get_llm()
    structured_llm = llm.with_structured_output(RetrievalPlan)

    plan: RetrievalPlan = structured_llm.invoke(
        ORCHESTRATOR_PROMPT.format(task=state["task"])
    )

    state["task_type"] = plan.task_type
    state["plan"] = plan.model_dump()
    state["messages"].append({
        "role": "orchestrator",
        "content": (
            f"Classified as '{plan.task_type}'. Plan: search domains "
            f"{plan.domains_to_search}, database={plan.check_database}"
            f"({plan.database_table or 'n/a'}), web_search={plan.needs_web_search}."
        ),
    })
    return state
