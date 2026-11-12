from langgraph.graph import END
from telegramegateway.agent.utils.state import AgentState
from telegramegateway.agent.utils.robin.prompt import robin_agent_prompt
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
import telegramegateway.agent.startup.mcp_robin as mcp
from langchain_core.messages import HumanMessage


def extract_image_from_messages(messages):
    # Only inspect the latest human message.
    for message in reversed(messages):
        if not isinstance(message, HumanMessage):
            continue

        content = message.content

        if isinstance(content, list):
            for block in content:
                if block.get("type") == "image_url":
                    image_url = block.get("image_url", {}).get("url")

                    if image_url and image_url.startswith("data:"):
                        return image_url

        # Don't reuse an image from an older message.
        return None

    return None

# 3. Define the Node Functions
def call_model(state: AgentState):
    agent_chain = robin_agent_prompt | mcp.robin_model_with_tools

    response = agent_chain.invoke({
        "messages": state["messages"],
        "summary": state.get("summary", "No previous summary available."),
    })

    updates = {"messages": [response]}

    # Only write the final answer once the model is done calling tools
    if not (isinstance(response, AIMessage) and response.tool_calls):
        updates["robin_answer"] = response.content

    return updates


def prepare_tools(state: AgentState):
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        return {}

    image_url = extract_image_from_messages(state["messages"])

    if not image_url:
        return {}

    updated_tool_calls = []
    modified = False

    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "hybrid_search":
            args = dict(tool_call["args"])

            args["image_url"] = image_url
            args["modalities"] = (
                "both" if args.get("query", "").strip() else "image"
            )

            updated_tool_calls.append({
                **tool_call,
                "args": args,
            })

            modified = True
        else:
            updated_tool_calls.append(tool_call)

    if not modified:
        return {}

    updated_message = last_message.model_copy(
        update={"tool_calls": updated_tool_calls}
    )

    print("PREPARED TOOL CALLS:", updated_message.tool_calls)

    return {"messages": [updated_message]}



def should_continue(state: AgentState):
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "prepare_tools"

    return END
