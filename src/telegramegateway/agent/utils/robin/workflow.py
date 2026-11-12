from langgraph.graph import StateGraph, START, END

from telegramegateway.agent.utils.state import AgentState
from telegramegateway.agent.utils.robin.nodes import (
    call_model,
    should_continue,
    prepare_tools
)


# =========================================================
# GRAPH INITIALIZATION
# =========================================================
def build_robin(tool_node):

    robin = StateGraph(AgentState)

    # =========================================================
    # NODES
    # =========================================================

    robin.add_node("agent", call_model)
    print(f"tool_node in subgraph: {tool_node}")
    robin.add_node("tools", tool_node)
    robin.add_node("prepare_tools", prepare_tools)
    # =========================================================
    # START EDGE
    # =========================================================

    robin.add_edge(
        START,
        "agent"
    )

    # =========================================================
    # AGENT ROUTING
    # =========================================================

    robin.add_conditional_edges(
        "agent",
        should_continue,
        {
            "prepare_tools": "prepare_tools",
            END: END,
        }
    )
    
    robin.add_edge("prepare_tools", "tools")
    robin.add_edge("tools", "agent")

    return robin
