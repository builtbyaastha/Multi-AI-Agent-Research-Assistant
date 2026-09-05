from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from agents import critic_chain, run_reader, run_search, writer_chain
from memory import find_related_reports, format_related_context, store_report


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------
class ResearchState(TypedDict):
    query: str
    related_context: str
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
def recall_node(state: ResearchState) -> dict:
    _log("Step 0 - Memory: Checking for related prior research")
    try:
        related = find_related_reports(state["query"])
    except Exception as e:
        print(f"[recall_node] memory lookup failed ({e}); continuing without it")
        related = []

    context = format_related_context(related)
    if related:
        print(f"found {len(related)} related past report(s): "
              f"{[r['topic'] for r in related]}")
    else:
        print("no related prior research found (cold start or novel topic)")

    return {"related_context": context}


def search_node(state: ResearchState) -> dict:
    _log("Step 1 - Search: Gathering recent information on the topic")
    search_result = run_search(state["query"])
    print("search result:", search_result[:500], "...")
    return {"search_result": search_result}


def reader_node(state: ResearchState) -> dict:
    _log("Step 2 - Reader: Extracting relevant information from scraped sources")
    scraped_content = run_reader(state["query"], state["search_result"])
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

    if state.get("related_context"):
        combined += f"\n\n{state['related_context']}"

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
        feedback, score = result.feedback, result.quality_score
        # Derive verdict from the (validator-normalized) score in code rather
        # than trusting the model's own verdict field — two independently
        # generated fields from the same model call can disagree, and the
        # score is the one we've already sanity-checked.
        verdict = "approve" if score >= 7 else "revise"
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


def store_node(state: ResearchState) -> dict:
    _log("Step 5 - Memory: Storing finished report for future recall")
    try:
        store_report(state["query"], state["report"], state["quality_score"])
        print("stored to memory")
    except Exception as e:
        print(f"[store_node] failed to store report ({e}); continuing anyway")
    return {}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("recall", recall_node)
    graph.add_node("search", search_node)
    graph.add_node("read", reader_node)
    graph.add_node("write", writer_node)
    graph.add_node("critique", critic_node)
    graph.add_node("store", store_node)

    graph.set_entry_point("recall")
    graph.add_edge("recall", "search")
    graph.add_edge("search", "read")
    graph.add_edge("read", "write")
    graph.add_edge("write", "critique")
    graph.add_conditional_edges(
        "critique",
        route_after_critic,
        {"end": "store", "revise": "write"},
    )
    graph.add_edge("store", END)

    return graph.compile()


def run_research_pipeline(topic: str, max_revisions: int = 2) -> dict:
    app = build_graph()

    initial_state: ResearchState = {
        "query": topic,
        "related_context": "",
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