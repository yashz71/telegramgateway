from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing import Literal


class SubTask(TypedDict):
    agent: Literal["robin", "nami"]
    instruction: str  # agent-specific sub-query, not the raw user message


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # plan produced once by the supervisor LLM
    plan: List[SubTask] | None
    parallel: bool
    reasoning: str | None
    # per-agent instruction for the CURRENT dispatch (set by Send payload)
    supervisor_instruction: str | None
    # per-agent outputs — kept separate so document_agent gets clean inputs
    robin_answer: str | None
    nami_answer: str | None
    summary: str
