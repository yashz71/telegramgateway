from typing import List
from langgraph.types import Send  # or `from langgraph.constants import Send` on older versions
from langgraph.graph import END

from agent.utils.state import AgentState, SubTask
from agent.utils.models.llm import model
from agent.utils.prompts import supervisor_agent_prompt
from pydantic import BaseModel


class RouterDecision(BaseModel):
    plan: List[SubTask]
    parallel: bool = True
    reasoning: str


router_model = supervisor_agent_prompt | model.with_structured_output(RouterDecision)


def supervisor_router(state: AgentState):
    """
    Runs the planning LLM ONCE per request. On subsequent visits
    (after a research agent returns), the plan already exists —
    we don't want to re-plan, just re-evaluate what's left.
    """
    if state.get("plan"):
        return {}  # no-op, routing handled in route_supervisor

    decision = router_model.invoke({"messages": state["messages"]})

    return {
        "plan": [
            {
                "agent": task["agent"],
                "instruction": task["instruction"],
            }
            for task in decision.plan
        ],
        "parallel": decision.parallel,
        "reasoning": decision.reasoning,
    }


def route_supervisor(state: AgentState):

    plan = state.get("plan") or []

    if not plan:
        return END

    def is_done(task: SubTask) -> bool:

        if task["agent"] == "robin":
            return state.get("robin") is not None

        if task["agent"] == "nami":
            return state.get("nami") is not None

        

        return True

    remaining = [
        task
        for task in plan
        if not is_done(task)
    ]

    if not remaining:
        return END

    research = [
        task
        for task in remaining
        if task["agent"] in (
            "robin",
            "nami",
        )
    ]

    if research:
        return [
            Send(
                task["agent"],
                {
                    "messages": state["messages"],
                    "supervisor_instruction": task["instruction"],
                }
            )
            for task in research
        ]

    return END
