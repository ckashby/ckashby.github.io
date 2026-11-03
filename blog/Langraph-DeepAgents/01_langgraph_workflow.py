"""LangGraph example: a deterministic support-ticket router (no LLM required).

Run: python 01_langgraph_workflow.py
Deps: pip install -U langgraph
"""

from typing import Literal

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


class TicketState(TypedDict):
    text: str
    category: str  # billing | technical | other
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
    return {"reply": "Billing team here - we've opened a refund review for you."}


def technical_reply(state: TicketState) -> dict:
    return {"reply": "Engineering here - please send logs so we can debug the crash."}


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


if __name__ == "__main__":
    tickets = [
        "I was charged twice for my subscription!",
        "The app keeps crashing with a null pointer error",
        "Do you offer student discounts?",
    ]
    for ticket in tickets:
        result = graph.invoke({"text": ticket})
        print(f"[{result['category']:>9}] {ticket}\n            -> {result['reply']}\n")
