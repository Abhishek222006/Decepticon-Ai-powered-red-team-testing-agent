from langgraph.prebuilt import create_react_agent
try:
    from langmem import create_manage_memory_tool, create_search_memory_tool
except ModuleNotFoundError:
    create_manage_memory_tool = None
    create_search_memory_tool = None
from src.prompts.prompt_loader import load_prompt
from src.tools.handoff import handoff_to_planner, handoff_to_reconnaissance, handoff_to_summary
from src.utils.llm.config_manager import get_current_llm
from src.utils.memory import get_store 
from src.utils.mcp.mcp_loader import load_mcp_tools

async def make_initaccess_agent():
    llm = get_current_llm()
    
    # None 체크 추가 (주석 해제 권장)
    if llm is None:
        try:
            from langchain_anthropic import ChatAnthropic
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "No LLM is configured and Anthropic provider is not installed. "
                "Install 'langchain-anthropic' or select a different model/provider."
            ) from e
        llm = ChatAnthropic(model_name="claude-3-5-sonnet-latest", temperature=0, timeout=60, stop=None)
        print("Warning: Using default LLM model (Claude 3.5 Sonnet)")
    
    # 중앙 집중식 store 사용
    store = get_store()
    
    mcp_tools = await load_mcp_tools(agent_name=["initial_access"])

    swarm_tools = [
        handoff_to_reconnaissance,
        handoff_to_planner,
        handoff_to_summary,
    ]

    if create_manage_memory_tool is None or create_search_memory_tool is None:
        mem_tools = []
    else:
        mem_tools = [
            create_manage_memory_tool(namespace=("memories",), store=store),
            create_search_memory_tool(namespace=("memories",), store=store)
        ]

    tools = mcp_tools + swarm_tools + mem_tools

    agent = create_react_agent(
        llm,
        tools=tools,
        store=store,
        name="Initial_Access",
        prompt=load_prompt("initial_access", "swarm"),
    )
    return agent