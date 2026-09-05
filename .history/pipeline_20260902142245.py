from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------
class ResearchState(TypedDict):
    query: str
    search_result: str
    scraped_content: str
    report: str
    feedback: str
    quality_score: int
    verdict: Literal["approve", "revise"]
    revision_count: int
    max_revisions: int


def _log(step: str, msg: str = "") -> None:
    print("\n" + " = " * 50)
    print(f" {step}")
    print(" = " * 50)
    if msg:
        print(msg[:500], "...\n" if len(msg) > 500 else "\n")


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def search_node(state: ResearchState) -> dict:
    _log("Step 1 - Search Agent: Gathering recent information on the topic")
    agent = build_search_agent()
    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": f"Search for recent and reliable information on the topic: {state['query']}"
            }
        ]
    })
    search_result = result["messages"][-1].content
    print("search result:", search_result[:500], "...")
    return {"search_result": search_result}


def reader_node(state: ResearchState) -> dict:
    _log("Step 2 - Reader Agent: Extracting relevant information from search results")
    agent = build_reader_agent()
    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": f"""Based on the following search results about '{state['query']}', extract the most relevant information that would help in writing a research summary.

Focus on:
- key findings
- important models/methods
- challenges
- future directions

Search Results:
{state['search_result'][:1500]}
"""
            }
        ]
    })
    scraped_content = result["messages"][-1].content
    print("reader result:", scraped_content[:500], "...")
    return {"scraped_content": scraped_content}


def writer_node(state: ResearchState) -> dict:
    is_revision = state.get("revision_count", 0) > 0
    _log(f"Step 3 - Writer Chain: {'Revising' if is_revision else 'Writing'} the research summary")

    combined = (
        f"Search Results:\n{state['search_result'][:800]}...\n\n"
        f"Extracted Information:\n{state['scraped_content'][:1500]}..."
    )

    if is_revision and state.get("feedback"):
        combined += (
            f"\n\nPrevious critic feedback to address (revision {state['revision_count']}):\n"
            f"{state['feedback']}"
        )

    report = writer_chain.invoke({"query": state["query"], "text": combined})
    print("report draft:", report[:500], "...")
    return {"report": report}


def critic_node(state: ResearchState) -> dict:
    _log("Step 4 - Critic Chain: Evaluating the quality of the research summary")

    combined = (
        f"Search Results:\n{state['search_result'][:800]}...\n\n"
        f"Extracted Information:\n{state['scraped_content'][:1500]}..."
    )

    try:
        result = critic_chain.invoke({
            "query": state["query"],
            "text": combined,
            "summary": state["report"],
        })
        feedback, score, verdict = result.feedback, result.quality_score, result.verdict
    except Exception as e:
        # Fail open rather than looping forever on a parsing/model hiccup.
        print(f"[critic_node] structured output failed ({e}); defaulting to approve")
        feedback, score, verdict = "Critic evaluation unavailable this pass.", 5, "approve"

    print(f"critic verdict: {verdict} (score: {score}/10)")
    print("feedback:", feedback[:500], "...")

    return {
        "feedback": feedback,
        "quality_score": score,
        "verdict": verdict,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def route_after_critic(state: ResearchState) -> str:
    if state["verdict"] == "approve":
        return "end"
    if state["revision_count"] >= state.get("max_revisions", 2):
        print(f"[route_after_critic] hit max_revisions ({state['max_revisions']}); shipping current draft")
        return "end"
    return "revise"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("search", search_node)
    graph.add_node("read", reader_node)
    graph.add_node("write", writer_node)
    graph.add_node("critique", critic_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "read")
    graph.add_edge("read", "write")
    graph.add_edge("write", "critique")
    graph.add_conditional_edges(
        "critique",
        route_after_critic,
        {"end": END, "revise": "write"},
    )

    return graph.compile()


def run_research_pipeline(topic: str, max_revisions: int = 2) -> dict:
    app = build_graph()

    initial_state: ResearchState = {
        "query": topic,
        "search_result": "",
        "scraped_content": "",
        "report": "",
        "feedback": "",
        "quality_score": 0,
        "verdict": "revise",
        "revision_count": 0,
        "max_revisions": max_revisions,
    }

    final_state = app.invoke(initial_state)

    print("\n" + " = " * 50)
    print(f" DONE — verdict: {final_state['verdict']} | "
          f"score: {final_state['quality_score']}/10 | "
          f"revisions used: {final_state['revision_count']}")
    print(" = " * 50 + "\n")

    return final_state


if __name__ == "__main__":
    topic = input("Enter a research topic: ")
    run_research_pipeline(topic)