# DeepAgents vs. LangChain vs. LangGraph — A Practical Tutorial

> Based on the official LangChain docs (docs.langchain.com) as of November 2026.
> Companion runnable scripts live in the `examples/` folder next to this file.

---

## 1. The Big Picture: Three Layers of One Stack

The most common misconception is that these are three competing frameworks. They aren't —
they are **three layers of the same stack**, each with a different level of abstraction:

```
┌─────────────────────────────────────────────────────────────┐
│  DeepAgents                        (batteries-included)     │
│  create_deep_agent() — planning, virtual filesystem,        │
│  subagents, context management, skills, memory              │
├─────────────────────────────────────────────────────────────┤
│  LangChain                         (minimal agent harness)  │
│  create_agent() — model + tools + prompt + middleware       │
├─────────────────────────────────────────────────────────────┤
│  LangGraph                         (low-level orchestration)│
│  StateGraph — nodes, edges, state, checkpointers, streaming │
└─────────────────────────────────────────────────────────────┘
```

- **LangGraph** is the runtime: a graph execution engine with state, persistence,
  streaming, and human-in-the-loop primitives. It doesn't assume you're building an
  "agent" at all — you can build fully deterministic workflows with it.
- **LangChain** provides `create_agent`, a minimal, highly configurable *agent harness*
  built on top of LangGraph. It implements the classic tool-calling loop
  (model → tool calls → tool results → model → …) and lets you shape it with
  **middleware**.
- **DeepAgents** is an *opinionated harness on top of `create_agent`*. Same building
  blocks, but bundled with a planning tool (todos), a virtual filesystem, subagent
  spawning, context summarization/offloading, skills, and long-term memory —
  the ingredients for long-horizon, multi-step work ("deep" tasks).

The official guidance:

| You want… | Use |
|---|---|
| A production-ready agent with planning, files, subagents out of the box | **DeepAgents** |
| A lightweight, fully customizable agent loop you tailor yourself | **LangChain** `create_agent` |
| A custom control flow mixing deterministic steps and agentic steps | **LangGraph** directly |

All three work with any LangChain-compatible chat model (OpenAI, Anthropic, Google,
Ollama, Bedrock, OpenRouter, …) and integrate with **LangSmith** for tracing and evals.

### Installation

```bash
pip install -U langchain "langchain[openai]"   # LangChain + OpenAI provider
pip install -U langgraph                       # LangGraph
pip install -U deepagents                      # DeepAgents (pulls in langchain + langgraph)
```

Set your key, e.g. `export OPENAI_API_KEY=sk-...` (or `ANTHROPIC_API_KEY`, etc.).
Every example below uses the `provider:model` string format — swap
`"openai:gpt-5.5"` for `"anthropic:claude-sonnet-5"`, `"google_genai:gemini-3.6-flash"`,
or `"ollama:llama3.2"` freely.

---

## 2. LangGraph: The Low-Level Orchestration Layer

### Core concepts

- **State**: a `TypedDict` (or Pydantic model) that flows through the graph. Each field
  can have a *reducer* — e.g. `add_messages` appends to the message list instead of
  overwriting it.
- **Nodes**: plain Python functions `(state) -> partial state update`.
- **Edges**: fixed (`add_edge`) or conditional (`add_conditional_edges` with a routing
  function). `START` and `END` mark entry/exit.
- **Compile**: `builder.compile()` returns a Runnable you can `invoke`, `stream`,
  and (with a checkpointer) persist and resume.
- **Checkpointers**: save state after every superstep, enabling threads, memory,
  time travel, and human-in-the-loop interrupts.

### Example 2.1 — A deterministic workflow (no LLM at all)

LangGraph shines when the *flow itself* is the product — e.g. a support ticket router.

```python
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


class TicketState(TypedDict):
    text: str
    category: str          # billing | technical | other
    reply: str


def classify(state: TicketState) -> dict:
    text = state["text"].lower()
    if "bill" in text or "charge" in text or "refund" in text:
        category = "billing"
    elif "error" in text or "crash" in text or "bug" in text:
        category = "technical"
    else:
        category = "other"
    return {"category": category}


def billing_reply(state: TicketState) -> dict:
    return {"reply": "Billing team here — we've opened a refund review for you."}


def technical_reply(state: TicketState) -> dict:
    return {"reply": "Engineering here — please send logs so we can debug the crash."}


def general_reply(state: TicketState) -> dict:
    return {"reply": "Thanks for reaching out! A human will follow up shortly."}


def route(state: TicketState) -> Literal["billing", "technical", "general"]:
    return {"billing": "billing", "technical": "technical", "other": "general"}[
        state["category"]
    ]


builder = StateGraph(TicketState)
builder.add_node("classify", classify)
builder.add_node("billing", billing_reply)
builder.add_node("technical", technical_reply)
builder.add_node("general", general_reply)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route)
builder.add_edge("billing", END)
builder.add_edge("technical", END)
builder.add_edge("general", END)

graph = builder.compile()

result = graph.invoke({"text": "I was charged twice for my subscription!"})
print(result["category"], "->", result["reply"])
# billing -> Billing team here — we've opened a refund review for you.
```

**What to notice:** you control *every* transition explicitly. Nothing is decided by an
LLM loop; the graph is auditable, testable, and deterministic.

### Example 2.2 — A chat loop with an LLM node and message state

```python
from typing import Annotated
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

llm = init_chat_model("openai:gpt-5.5")


class State(TypedDict):
    # The add_messages reducer APPENDS new messages instead of overwriting
    messages: Annotated[list, add_messages]


def call_model(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(State)
builder.add_node("model", call_model)
builder.add_edge(START, "model")
builder.add_edge("model", END)
graph = builder.compile()

result = graph.invoke({"messages": [{"role": "user", "content": "What is LangGraph?"}]})
print(result["messages"][-1].content)
```

> There's a shortcut for exactly this state: `from langgraph.graph import MessagesState`.

### Example 2.3 — Persistence with a checkpointer (memory across turns)

```python
from langgraph.checkpoint.memory import MemorySaver   # or SqliteSaver / PostgresSaver

graph = builder.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "user-123"}}

graph.invoke({"messages": [{"role": "user", "content": "My name is Alice"}]}, config)
result = graph.invoke({"messages": [{"role": "user", "content": "What's my name?"}]}, config)
print(result["messages"][-1].content)  # "Your name is Alice."
```

Each `thread_id` gets its own saved conversation history — this is how LangGraph powers
stateful chatbots, and the same mechanism enables *interrupt & resume* for
human-in-the-loop approval.

### Example 2.4 — A custom agent loop by hand (model ⇄ tools)

This is what `create_agent` builds for you, done manually — useful to demystify it:

```python
from langchain.chat_models import init_chat_model
from langchain.tools import tool
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
builder.add_edge("tools", "agent")          # loop back!
graph = builder.compile()

result = graph.invoke({"messages": [{"role": "user", "content": "What is 23 * 17?"}]})
print(result["messages"][-1].content)
```

> LangGraph also ships a prebuilt `create_react_agent` in `langgraph.prebuilt`, and a
> decorator-based **Functional API** (`@entrypoint` / `@task`) for people who prefer
> writing normal Python over explicit graph wiring.

### When LangGraph (directly) is the right choice

- The flow is mostly **deterministic** with an LLM step here and there (pipelines,
  routers, extract→validate→retry loops).
- You need **custom control flow**: cycles, branches, map-reduce/fan-out, parallel
  supersteps.
- You want fine-grained **durability**: checkpointing, time travel, resumability.
- The standard "model decides which tool to call in a loop" shape is *not* what you need.

---

## 3. LangChain: The Configurable Agent Harness

### Core concepts

In LangChain v1, the centerpiece is a single function:

```python
from langchain.agents import create_agent
```

**Agent = Model + Harness.** The harness is everything around the model loop: the system
prompt, the tools, and **middleware** that hooks into the loop (before/after model calls,
before/after tool calls). Under the hood, `create_agent` compiles to a LangGraph graph —
so you get streaming, checkpointing, and deployment for free.

### Example 3.1 — The minimal agent

```python
# pip install -U langchain "langchain[openai]"
from langchain.agents import create_agent


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],                    # plain Python functions work as tools
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

The agent decides on its own to call `get_weather("San Francisco")`, feeds the result
back into the model, and answers. Compare with Example 2.4: same loop, ~zero wiring.

### Example 3.2 — Structured output

```python
from pydantic import BaseModel
from langchain.agents import create_agent


class Answer(BaseModel):
    summary: str
    confidence: float


agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    response_format=Answer,          # forces the final answer into this schema
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Summarize AI trends"}]}
)
print(result["structured_response"])  # Answer(summary='...', confidence=0.87)
```

### Example 3.3 — Middleware: human-in-the-loop + summarization + PII

Middleware is LangChain v1's extension mechanism. You compose behavior instead of
subclassing or hand-editing the graph:

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    PIIMiddleware,
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
)

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[read_email, send_email],
    middleware=[
        # Redact PII in inputs to the "email" tool
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        # Summarize the conversation when it exceeds 500 tokens of history
        SummarizationMiddleware(model="openai:gpt-5.5", trigger={"tokens": 500}),
        # Pause for approval before send_email actually runs
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": {"allowed_decisions": ["approve", "edit", "reject"]}
            }
        ),
    ],
)
```

Middleware can modify the model request (prompt wrapping, message trimming), intercept
tool calls (approval gates, redaction), and reshape state — all without touching the
agent loop itself.

### Example 3.4 — Streaming and persistence (because it's LangGraph underneath)

```python
from langgraph.checkpoint.memory import MemorySaver

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    checkpointer=MemorySaver(),
)
config = {"configurable": {"thread_id": "conv-1"}}

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Weather in Tokyo and Paris?"}]},
    config,
    stream_mode="updates",          # see each node's output as it happens
):
    print(chunk)
```

### When LangChain `create_agent` is the right choice

- You want the **standard agent loop** (model + tools) but with your own tools,
  prompts, and middleware — full control of the harness, none of the graph plumbing.
- Your task is agentic but **single-context**: one agent, a handful of tools, short to
  medium runs.
- You want easy structured output, PII handling, approval gates, summarization — as
  composable middleware.

---

## 4. DeepAgents: The Batteries-Included Harness

### Core concepts

DeepAgents answers one question: *what do agents need to do long, complex, multi-step
work reliably?* The docs distill it into built-in capabilities:

- **Planning** — a todo list the agent writes and updates as it works
- **Virtual filesystem** — the agent reads/writes files as durable, offloadable context
- **Subagents** — spawn ephemeral child agents in *isolated context windows* for
  focused or parallel subtasks (via a built-in `task` tool)
- **Context management** — automatic summarization when history grows; large tool
  results are offloaded to files instead of bloating the prompt
- **Skills & memory** — load domain knowledge (`skills/`) and persistent instructions
  (`AGENTS.md`) on demand
- **Human-in-the-loop** — pause for approval at critical decision points

#### Built-in tools

| Tool | Description | Provided by |
|---|---|---|
| `write_todos` / `read_todos` | Structured task planning & progress tracking | `TodoListMiddleware` (opt-in since v0.7) |
| `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` | Virtual filesystem operations | `FilesystemMiddleware` |
| `execute` | Run shell commands in a sandbox | `FilesystemMiddleware` (sandbox backend) |
| `task` | Delegate a subtask to a subagent | `SubAgentMiddleware` |

#### Built-in middleware

| Middleware | Purpose |
|---|---|
| `TodoListMiddleware` | Task planning (opt-in since deepagents v0.7) |
| `FilesystemMiddleware` | File ops + context offloading of large results |
| `SubAgentMiddleware` | Isolated subagent delegation |
| `SummarizationMiddleware` | Auto-summarizes when context grows too long |
| `HumanInTheLoopMiddleware` | Pauses for human approval (`interrupt_on=`) |
| `AnthropicPromptCachingMiddleware` | Caches system prompts to cut cost (Anthropic) |
| `PatchToolCallsMiddleware` | Fixes dangling tool calls after interrupts |

### Example 4.1 — Zero-config deep agent

```python
# pip install -U deepagents
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.5",
    system_prompt="You are a research assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Research LangGraph and write a summary"}]}
)
print(result["messages"][-1].content)
```

Even with no custom tools, this agent can plan (`write_todos`), take notes
(`write_file`), search its own notes (`grep`), and spawn subagents (`task`) — and
`create_deep_agent` returns a **compiled LangGraph graph**, so streaming,
checkpointers, and LangSmith tracing all work exactly as in Sections 2–3.

### Example 4.2 — Custom subagents

The main agent delegates to subagents with the built-in `task` tool. Declarative
subagents are dicts; each runs in its own fresh context window and returns a single
report:

```python
from deepagents import create_deep_agent


def internet_search(query: str) -> str:
    """Search the internet for a query."""
    ...  # your favorite search API


research_subagent = {
    "name": "research-agent",
    "description": "Used to research in-depth questions on the web",
    "prompt": "You are an expert researcher. Be thorough and cite sources.",
    "tools": [internet_search],
    "model": "openai:gpt-5.5",       # optional; defaults to the main agent's model
}

writer_subagent = {
    "name": "writer-agent",
    "description": "Polishes research notes into clean prose",
    "prompt": "You are a professional editor.",
    "tools": [],
}

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[internet_search],
    subagents=[research_subagent, writer_subagent],
    system_prompt="You coordinate research and writing tasks.",
)
```

Why subagents matter: heavy intermediate work (searching 20 pages, reading big files)
stays *inside the subagent's context*. The main agent only ever sees the compact final
report — that's the core trick for surviving long-horizon tasks without context rot.

For complex cases you can hand DeepAgents an entire pre-built graph:

```python
from deepagents import CompiledSubAgent, create_deep_agent
from langchain.agents import create_agent

custom_graph = create_agent(model="openai:gpt-5.5", tools=[...], system_prompt="...")

agent = create_deep_agent(
    subagents=[
        CompiledSubAgent(
            name="data-analyzer",
            description="Specialized agent for data analysis",
            runnable=custom_graph,
        )
    ]
)
```

### Example 4.3 — Planning + skills + memory (the v0.7 way)

Since deepagents v0.7, task planning is **opt-in**. Add it back (plus load skills and
memory files) explicitly:

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_deep_agent(
    model="openai:gpt-5.5",
    middleware=[TodoListMiddleware()],   # agent gets write_todos / read_todos
    skills=["./skills/"],                # folders of on-demand domain knowledge
    memory=["./AGENTS.md"],              # persistent instructions loaded at startup
)
```

### Example 4.4 — Human-in-the-loop approval

```python
agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[send_invoice],
    interrupt_on={"send_invoice": True},  # pause before this tool executes
)
```

The graph interrupts before `send_invoice`; you review the pending call, then resume
with an approve/edit/reject decision.

### When DeepAgents is the right choice

- **Long-horizon tasks**: research reports, data analysis, code generation — work that
  spans dozens of steps and would blow up a naive context window.
- You want **planning, files, subagents, and context compression without building them**.
- You still want full escape hatches: custom tools, subagents, backends, middleware,
  state schema — everything `create_agent`/LangGraph offer is reachable.
- You'd rather run a *managed* deep agent (LangSmith Managed Deep Agents) than operate
  the infrastructure yourself.

---

## 5. The Same Task, Three Ways

Task: *"Look up the weather in two cities and produce a comparison."* This shows how the
amount of scaffolding you write changes at each layer.

### 5.1 With LangGraph (you wire everything)

```python
from typing import Annotated
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}, 24°C"


llm = init_chat_model("openai:gpt-5.5").bind_tools([get_weather])


class State(TypedDict):
    messages: Annotated[list, add_messages]


def call_model(state: State) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


def route(state: State) -> str:
    return "tools" if state["messages"][-1].tool_calls else END


builder = StateGraph(State)
builder.add_node("model", call_model)
builder.add_node("tools", ToolNode([get_weather]))
builder.add_edge(START, "model")
builder.add_conditional_edges("model", route)
builder.add_edge("tools", "model")
graph = builder.compile()

out = graph.invoke({
    "messages": [{"role": "user",
                  "content": "Compare the weather in Lisbon and Oslo."}]
})
print(out["messages"][-1].content)
```

*~25 lines: state schema, nodes, routing function, edges.*

### 5.2 With LangChain `create_agent` (harness provided, you configure it)

```python
from langchain.agents import create_agent


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}, 24°C"


agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    system_prompt="Compare weather concisely.",
)

out = agent.invoke({
    "messages": [{"role": "user",
                  "content": "Compare the weather in Lisbon and Oslo."}]
})
print(out["messages"][-1].content)
```

*~10 lines. No graph, no routing logic — the loop is the harness.*

### 5.3 With DeepAgents (harness + long-task capabilities pre-installed)

```python
from deepagents import create_deep_agent


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}, 24°C"


agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    system_prompt="Compare weather concisely.",
)

out = agent.invoke({
    "messages": [{"role": "user",
                  "content": "Compare the weather in Lisbon and Oslo."}]
})
print(out["messages"][-1].content)
```

*Also ~10 lines — but the agent now additionally carries a virtual filesystem, subagent
spawning, and context management.* For a trivial task that's overkill (a weather question
doesn't need todos and files); the extra machinery pays off when the task becomes
"compare the weather in 50 cities over the last decade and write a report."

---

## 6. Feature Comparison Table

| Feature | LangGraph | LangChain (`create_agent`) | DeepAgents |
|---|---|---|---|
| **What it is** | Low-level graph/orchestration runtime | Minimal, configurable agent harness | Opinionated harness for deep, long-horizon tasks |
| **Abstraction level** | Lowest (nodes, edges, state) | Middle (model + tools + middleware) | Highest (capabilities bundled) |
| **Primary API** | `StateGraph(...).compile()` | `create_agent(model=, tools=)` | `create_deep_agent(model=, tools=, subagents=)` |
| **Control flow** | Fully custom: branches, cycles, parallel nodes | Standard tool-calling loop (customizable via middleware) | Standard loop + planning/delegation patterns |
| **Planning (todo lists)** | DIY | Via `TodoListMiddleware` | Built-in (opt-in middleware since v0.7) |
| **Virtual filesystem** | DIY | Via `FilesystemMiddleware` | Built-in (`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`) |
| **Subagents / delegation** | DIY (nested graphs) | DIY / middleware | Built-in `task` tool + declarative & compiled subagents; async subagents supported |
| **Context management** | DIY | `SummarizationMiddleware`, trimming | Auto-summarization + offloading large results to files |
| **Human-in-the-loop** | `interrupt()` primitives | `HumanInTheLoopMiddleware` | `interrupt_on=` parameter |
| **Persistence / checkpointing** | Native (`checkpointer=`) | Yes (compiled LangGraph) | Yes (compiled LangGraph) |
| **Streaming** | Native (values/updates/messages/custom) | Yes | Yes, incl. `stream.subagents` per-delegation streams |
| **Structured output** | DIY | `response_format=` (Pydantic) | `response_format=` |
| **Skills / long-term memory** | DIY | DIY | `skills=`, `memory=` (AGENTS.md), store support |
| **Learning curve** | Steepest, most powerful | Gentle | Gentlest for complex tasks |
| **Best for** | Deterministic + custom agentic workflows | Custom single-context agents | Long-horizon research/analysis/coding agents |
| **Overhead for simple tasks** | Most code | Little | Slight (extra tools in context) |

---

## 7. Decision Guide

Ask yourself, in order:

1. **Is the flow mostly fixed, with LLM calls at specific points?**
   → **LangGraph.** Encode the flow as a graph; keep the LLM inside nodes.
   (Deterministic = auditable, cheap, testable.)

2. **Do you need an open-ended agent loop (the model decides what to do next),
   with a handful of tools, in one context window?**
   → **LangChain `create_agent`.** Add middleware for the behaviors you need
   (approval, PII, summarization, structured output).

3. **Will the task run long, produce large intermediate artifacts, or benefit from
   parallel specialization (planning, notes/files, delegation)?**
   → **DeepAgents.** You get todos, a filesystem, subagents, and context compression
   without building them — and you can still drop into raw middleware/LangGraph
   whenever you need to.

4. **Don't want to run any of this infrastructure yourself?**
   → **Managed Deep Agents** on LangSmith: same harness, hosted runtime, sandboxes,
   and schedules managed for you.

A useful mental model from the docs: *LangGraph is the engine, LangChain is the car,
DeepAgents is the car with a roof rack, winch, and a co-driver.* You can always open
the hood — every DeepAgents agent **is** a compiled LangGraph graph.

---

## 8. Common Pitfalls

- **Reaching for DeepAgents on trivial tasks.** The bundled tools (filesystem, todos,
  `task`) consume prompt space and steps. For a 2-tool chatbot, `create_agent` is leaner.
- **Building a graph when you wanted an agent.** If your "graph" is just
  model ⇄ tools ⇄ model, that's `create_agent` — don't hand-wire it.
- **Forgetting the reducer.** In LangGraph state, a plain field *overwrites*; annotate
  with `add_messages` (or `operator.add`) when you want append semantics.
- **Mutating state in nodes.** Nodes must *return* updates (`{"key": value}`), never
  mutate the state dict in place.
- **Assuming subagents can chat.** Subagents are stateless: one task in, one final
  report out. Design delegations accordingly.
- **Not checkpointing a human-in-the-loop flow.** Interrupts require a checkpointer —
  without one there's nowhere to save state while paused.
- **Skipping observability.** All three frameworks emit traces to LangSmith; turn it on
  early (`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`). Debugging a 40-step agent
  by print statements is misery.

---

## 9. Where to Read More

- LangChain overview & agents: <https://docs.langchain.com/oss/python/langchain/overview>
  and <https://docs.langchain.com/oss/python/langchain/agents>
- LangGraph graph API: <https://docs.langchain.com/oss/python/langgraph/use-graph-api>
- DeepAgents overview: <https://docs.langchain.com/oss/python/deepagents/overview>
- DeepAgents customization: <https://docs.langchain.com/oss/python/deepagents/customization>
- Build a deep agent from scratch:
  <https://docs.langchain.com/oss/python/langchain/deep-agent-from-scratch>
- DeepAgents repo: <https://github.com/langchain-ai/deepagents>
