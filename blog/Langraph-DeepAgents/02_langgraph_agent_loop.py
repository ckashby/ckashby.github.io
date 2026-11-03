"""LangGraph example: a hand-wired agent loop (model <-> tools), with checkpointing.

This is what langchain.agents.create_agent builds for you, done manually,
so you can see the machinery underneath.

Run: python 02_langgraph_agent_loop.py
Deps: pip install -U langchain langgraph "langchain[openai]"
Env: OPENAI_API_KEY
"""

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


llm = init_chat_model("openai:gpt-5.5").bind_tools([multiply])


def call_model(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


def should_continue(state: MessagesState) -> str:
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END


builder = StateGraph(MessagesState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode([multiply]))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue)
builder.add_edge("tools", "agent")  # loop back to the model

# A checkpointer gives the graph memory + resumability per thread_id.
graph = builder.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "demo-1"}}

    result = graph.invoke(
        {"messages": [{"role": "user", "content": "What is 23 * 17?"}]},
        config,
    )
    print("Answer:", result["messages"][-1].content)

    for step in result["messages"]:
        step.pretty_print()
