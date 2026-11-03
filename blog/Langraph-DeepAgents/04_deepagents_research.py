"""DeepAgents example: a research agent with planning and a specialized subagent.

The main agent gets, out of the box:
  - write_todos / read_todos   (planning; opt-in via TodoListMiddleware since v0.7)
  - ls, read_file, write_file, edit_file, glob, grep  (virtual filesystem)
  - task                       (delegate to subagents in isolated contexts)
  - automatic summarization / context offloading

Run: python 04_deepagents_research.py
Deps: pip install -U deepagents "langchain[openai]"
Env: OPENAI_API_KEY
"""

from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware


def internet_search(query: str) -> str:
    """Search the internet for a query (stub - plug in a real search API)."""
    return (
        f"[stub results for '{query}'] "
        "LangGraph is a low-level orchestration runtime for stateful agents. "
        "LangChain create_agent is a minimal agent harness built on LangGraph. "
        "DeepAgents adds planning, a filesystem, and subagents on top."
    )


research_subagent = {
    "name": "research-agent",
    "description": "Used to research in-depth questions on the web",
    "prompt": (
        "You are an expert researcher. Search thoroughly, save notes to files, "
        "and return a compact, well-organized report."
    ),
    "tools": [internet_search],
    # "model": "openai:gpt-5.5",  # optional; defaults to the main agent's model
}

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[internet_search],
    subagents=[research_subagent],
    system_prompt=(
        "You coordinate research tasks. For multi-step work, write a todo list, "
        "delegate deep research to the research-agent subagent, keep notes in "
        "files, and finish with a polished summary."
    ),
    middleware=[TodoListMiddleware()],  # planning is opt-in since deepagents v0.7
)


if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Research how LangGraph, LangChain, and DeepAgents relate, "
                        "save notes to notes.md, and write a 3-paragraph summary."
                    ),
                }
            ]
        }
    )

    print("=== final answer ===")
    print(result["messages"][-1].content)

    # The agent's virtual filesystem lives in state - inspect what it wrote:
    files = result.get("files", {})
    print("\n=== files written by the agent ===")
    for path, content in files.items():
        print(f"\n--- {path} ---\n{content[:500]}")
