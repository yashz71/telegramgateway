from langgraph.graph import StateGraph, START, END

from agent.utils.state import AgentState
from agent.utils.nami.nodes import (
    call_model,
    should_continue
)


# =========================================================
# GRAPH INITIALIZATION
# =========================================================
def build_nami(tool_node):

    nami = StateGraph(AgentState)

    # =========================================================
    # NODES
    # =========================================================

    nami.add_node("agent", call_model)
    print(f"tool_node in subgraph: {tool_node}")
    nami.add_node("tools", tool_node)

    # =========================================================
    # START EDGE
    # =========================================================

    nami.add_edge(
        START,
        "agent"
    )

    # =========================================================
    # AGENT ROUTING
    # =========================================================

    nami.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        }
    )

    return nami.compile()
