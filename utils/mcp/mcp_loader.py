import json
import asyncio

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ModuleNotFoundError:
    MultiServerMCPClient = None

async def load_mcp_tools(agent_name=None, max_retries=3, delay=2):
    if MultiServerMCPClient is None:
        return []
    with open("mcp_config.json", "r") as f:
        config = json.load(f)

    if agent_name:
        selected_agents = {agent: config[agent] for agent in agent_name if agent in config}
    else:
        selected_agents = config

    tools = []

    for agent_name, servers in selected_agents.items():
        if not servers:
            continue

        for server_name, server_config in servers.items():
            if "transport" not in server_config:
                server_config["transport"] = "streamable_http" if "url" in server_config else "stdio"

            client = MultiServerMCPClient({server_name: server_config})
            
            for attempt in range(max_retries):
                try:
                    current_tools = await client.get_tools() if client else []
                    if current_tools:
                        tools.extend(current_tools)
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        # Optionally re-raise the exception or handle the final failure
                        pass # Failed to connect after all retries

    return tools if tools else []