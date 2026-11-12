# agent/startup/mcp_robin.py

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode
from telegramegateway.agent.utils.models.llm import model
from telegramegateway.agent.utils.config import mcp_server_url_robin
mcp_client = MultiServerMCPClient(
    {
        "mcp_server": {
            "transport": "streamable_http",
            "url": mcp_server_url_robin,
        }
    }
)

tools = None
tool_node = None
robin_model_with_tools = None


async def initialize_mcp_robin():

    global tools
    global tool_node
    global robin_model_with_tools
    tools = await mcp_client.get_tools()

    tool_node = ToolNode(tools,
                         handle_tool_errors=True
                         )
    robin_model_with_tools = model.bind_tools(tools)

    print("TOOL NODE:", tool_node)
    print("--- MCP TOOLS INITIALIZED ---")

    return {
        "tools": tools,
        "tool_node": tool_node,
        "robin_model_with_tools": robin_model_with_tools
    }