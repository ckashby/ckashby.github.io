"""LangChain example: create_agent with tools, structured output, and middleware.

Run: python 03_langchain_agent.py
Deps: pip install -U langchain "langchain[openai]"
Env: OPENAI_API_KEY
"""

from pydantic import BaseModel

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    fake_db = {
        "lisbon": "sunny, 24C",
        "oslo": "cloudy, 9C",
        "san francisco": "foggy, 16C",
    }
    return fake_db.get(city.lower(), f"unknown city: {city}")


class Comparison(BaseModel):
    """Structured comparison of two cities' weather."""

    warmer_city: str
    cooler_city: str
    summary: str


agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    system_prompt=(
        "You are a concise weather assistant. Call get_weather for each city "
        "before answering."
    ),
    response_format=Comparison,
    middleware=[
        # Keep long conversations cheap by summarizing older history.
        SummarizationMiddleware(model="openai:gpt-5.5", trigger={"tokens": 2000}),
    ],
)


if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Compare the weather in Lisbon and Oslo.",
                }
            ]
        }
    )

    structured = result["structured_response"]
    print("Warmer:", structured.warmer_city)
    print("Cooler:", structured.cooler_city)
    print("Summary:", structured.summary)

    print("\n--- full message trace ---")
    for msg in result["messages"]:
        msg.pretty_print()
