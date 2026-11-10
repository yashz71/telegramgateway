from langgraph.graph import StateGraph, END, START
from agent.utils.nodes import supervisor_router, route_supervisor
from agent.utils.state import AgentState


def build_workflow(robin, nami):
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_router)
    workflow.add_node("robin", robin)
    workflow.add_node("nami", nami)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "robin": "robin",
            "nami": "nami",
            END: END,
        },
    )

    workflow.add_edge("robin", "supervisor")
    workflow.add_edge("nami", "nami")
    return workflow
