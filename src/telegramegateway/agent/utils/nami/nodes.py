from langgraph.graph import END
from agent.utils.state import AgentState
from agent.utils.models.llm import model
from agent.utils.accounting_agent.prompt import accountant_agent_prompt
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
import agent.startup.mcp_accountant as mcp


# 3. Define the Node Functions
def call_model(state: AgentState):
    agent_chain = accountant_agent_prompt | mcp.accounting_model_with_tools

    response = agent_chain.invoke({
        "messages": state["messages"],
        "instruction": state.get("supervisor_instruction"),  # <-- the sub-query, not raw user msg
        "summary": state.get("summary", "No previous summary available."),
    })

    updates = {"messages": [response]}

    # Only write the final answer once the model is done calling tools
    if not (isinstance(response, AIMessage) and response.tool_calls):
        updates["nami"] = response.content

    return updates


def should_continue(state: AgentState):
    """Determines if the LLM wants to call a tool or finish."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END

