"""
Evaluation harness for the research pipeline.

Runs a fixed set of "golden" queries end-to-end through run_research_pipeline,
then scores each resulting report against explicit criteria using an LLM judge
that is *separate* from the in-pipeline Critic agent. This is deliberate:
the Critic already approved everything that reaches this script (it's part of
the pipeline's own revise loop), so using it again here would just be
re-checking its own homework. The judge here is an independent, offline pass
over a fixed dataset, run outside the pipeline, on your own criteria — closer
to what "eval" means in interview terms.

Usage:
    python eval.py                 # run full golden set
    python eval.py --limit 3       # quick smoke test on first 3 queries
    python eval.py --save results.json
"""

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from pipeline import run_research_pipeline


# ---------------------------------------------------------------------------
# Golden dataset
# ---------------------------------------------------------------------------
# Each entry is a query plus the criteria a *good* report on that topic
# should satisfy. Keep criteria specific and checkable, not vague ("is good").
# Start small (10-20) and grow it as you find failure modes worth locking in
# as regression tests.
GOLDEN_QUERIES = [
    {
        "id": "q1",
        "query": "Recent advances in retrieval-augmented generation (RAG)",
        "criteria": [
            "Mentions at least one specific technique or paper, not just generic RAG concepts",
            "Distinguishes retrieval quality from generation quality as separate concerns",
            "Notes at least one limitation or open problem",
        ],
    },
    {
        "id": "q2",
        "query": "How do vector databases handle approximate nearest neighbor search",
        "criteria": [
            "Names at least one concrete algorithm (e.g. HNSW, IVF, LSH)",
            "Explains the accuracy/speed tradeoff, not just that a tradeoff exists",
            "Does not claim exact search is used when the topic is approximate search",
        ],
    },
    {
        "id": "q3",
        "query": "Current state of multi-agent orchestration frameworks",
        "criteria": [
            "Names at least two real frameworks (e.g. LangGraph, CrewAI, AutoGen)",
            "Distinguishes between them rather than treating them as interchangeable",
            "Mentions a real limitation of multi-agent systems (coordination overhead, cost, debugging difficulty, etc.)",
        ],
    },
    {
        "id": "q4",
        "query": "What is prompt injection and how is it mitigated",
        "criteria": [
            "Correctly distinguishes prompt injection from jailbreaking",
            "Names at least one concrete mitigation technique",
            "Does not claim any mitigation is 100% effective",
        ],
    },
    {
        "id": "q5",
        "query": "Benchmarks used to evaluate large language model reasoning",
        "criteria": [
            "Names at least two real, specific benchmarks",
            "Notes a known weakness of benchmark-based evaluation (contamination, saturation, etc.)",
            "Does not present benchmark scores as a complete measure of reasoning ability",
        ],
    },
]


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------
class JudgeResult(BaseModel):
    criteria_met: list[bool] = Field(
        description="One True/False per criterion, in the same order as given."
    )
    verdict: Literal["pass", "fail"] = Field(
        description="'pass' only if all criteria are met, otherwise 'fail'."
    )
    reasoning: str = Field(
        description="One or two sentences on why, referencing the specific criteria."
    )


judge_llm = ChatOllama(model="mistral:latest", temperature=0)
judge_structured = judge_llm.with_structured_output(JudgeResult)

judge_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a strict evaluator grading a research report against a fixed
checklist. Judge only what is written in the report — do not give credit for
things a good report on this topic *could* say, only what it *does* say.
Be skeptical: if a criterion is ambiguous or only partially met, mark it False."""
    ),
    (
        "user",
        """Topic: {query}

Criteria (evaluate each independently):
{criteria_list}

Report to evaluate:
{report}

Evaluate each criterion and give your verdict."""
    )
])

judge_chain = judge_prompt | judge_structured


def judge_report(query: str, criteria: list[str], report: str) -> JudgeResult:
    criteria_list = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    return judge_chain.invoke({
        "query": query,
        "criteria_list": criteria_list,
        "report": report,
    })


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_eval(limit: int | None = None) -> dict:
    dataset = GOLDEN_QUERIES[:limit] if limit else GOLDEN_QUERIES
    results = []

    for item in dataset:
        print(f"\n[eval] running {item['id']}: {item['query']}")
        start = time.time()

        try:
            final_state = run_research_pipeline(item["query"])
            report = final_state["report"]
            pipeline_ok = True
            pipeline_error = None
        except Exception as e:
            report = ""
            pipeline_ok = False
            pipeline_error = str(e)

        elapsed = time.time() - start

        if pipeline_ok:
            try:
                judgment = judge_report(item["query"], item["criteria"], report)
                judge_ok = True
                judge_error = None
            except Exception as e:
                judgment = None
                judge_ok = False
                judge_error = str(e)
        else:
            judgment = None
            judge_ok = False
            judge_error = "skipped - pipeline failed"

        result = {
            "id": item["id"],
            "query": item["query"],
            "criteria": item["criteria"],
            "pipeline_ok": pipeline_ok,
            "pipeline_error": pipeline_error,
            "pipeline_revisions": final_state.get("revision_count") if pipeline_ok else None,
            "pipeline_internal_score": final_state.get("quality_score") if pipeline_ok else None,
            "judge_ok": judge_ok,
            "judge_error": judge_error,
            "judge_verdict": judgment.verdict if judgment else "error",
            "judge_criteria_met": judgment.criteria_met if judgment else None,
            "judge_reasoning": judgment.reasoning if judgment else None,
            "elapsed_seconds": round(elapsed, 1),
        }
        results.append(result)

        status = result["judge_verdict"]
        print(f"[eval] {item['id']} -> {status} ({elapsed:.1f}s)")

    passed = sum(1 for r in results if r["judge_verdict"] == "pass")
    total = len(results)

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 2) if total else 0,
        "results": results,
    }

    print("\n" + "=" * 60)
    print(f" EVAL SUMMARY: {passed}/{total} passed ({summary['pass_rate']*100:.0f}%)")
    print("=" * 60)
    for r in results:
        marker = "PASS" if r["judge_verdict"] == "pass" else "FAIL"
        print(f"  [{marker}] {r['id']}: {r['query']}")
        if r["judge_verdict"] == "fail" and r["judge_reasoning"]:
            print(f"          reason: {r['judge_reasoning']}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the golden-query eval suite.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N queries.")
    parser.add_argument("--save", type=str, default=None, help="Path to save results as JSON.")
    args = parser.parse_args()

    summary = run_eval(limit=args.limit)

    if args.save:
        with open(args.save, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSaved results to {args.save}")