"""
Long-term memory layer for the research pipeline.

Stores completed reports in a local Chroma collection, keyed by topic, so
future related queries can retrieve prior research as extra context instead
of starting cold every time. Uses sentence-transformers for embeddings
(already a dependency) rather than an API-based embedding model, so this
doesn't add cost or a new external dependency.

This is intentionally simple: one collection, one embedding function, no
chunking. For a research-summary use case the reports are short enough that
whole-document embedding is fine; chunking would be the next step if reports
get long enough to blow past a single embedding's useful context.
"""

import os
from datetime import datetime, timezone

import chromadb
from chromadb.utils import embedding_functions

_PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".chroma_memory")
_COLLECTION_NAME = "research_reports"

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

_client = chromadb.PersistentClient(path=_PERSIST_DIR)
_collection = _client.get_or_create_collection(
    name=_COLLECTION_NAME,
    embedding_function=_embedding_fn,
)


def store_report(topic: str, report: str, quality_score: int) -> None:
    """
    Save a completed report to memory. Called once the pipeline's revise
    loop has finished (approved or hit max_revisions) — we don't want
    half-finished drafts polluting future retrieval.
    """
    doc_id = f"{topic}::{datetime.now(timezone.utc).isoformat()}"
    _collection.add(
        ids=[doc_id],
        documents=[report],
        metadatas=[{
            "topic": topic,
            "quality_score": quality_score,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }],
    )


def find_related_reports(topic: str, n_results: int = 2, max_distance: float = 0.6) -> list[dict]:
    """
    Look up past reports on similar topics. Returns an empty list if the
    collection is empty or nothing is close enough — a cold start is not
    an error, it's the expected state for a fresh project or a genuinely
    novel query.

    max_distance is a cosine-distance cutoff (lower = more similar). 0.6 is
    a deliberately conservative default — better to miss a borderline match
    than to feed the writer a barely-related past report as if it were
    relevant context.
    """
    if _collection.count() == 0:
        return []

    results = _collection.query(
        query_texts=[topic],
        n_results=min(n_results, _collection.count()),
    )

    related = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        if dist <= max_distance:
            related.append({
                "topic": meta.get("topic"),
                "report": doc,
                "quality_score": meta.get("quality_score"),
                "stored_at": meta.get("stored_at"),
                "distance": round(dist, 3),
            })

    return related


def format_related_context(related: list[dict]) -> str:
    """
    Turns retrieved past reports into a short context block for the writer
    prompt. Kept brief (truncated) since this is supplementary context, not
    the primary source material — the point is to avoid contradicting or
    duplicating prior work, not to replace fresh research.
    """
    if not related:
        return ""

    blocks = []
    for r in related:
        blocks.append(
            f"- Prior research on \"{r['topic']}\" (from {r['stored_at'][:10]}):\n"
            f"  {r['report'][:400]}..."
        )
    return (
        "Related prior research exists in memory. Use it to avoid contradicting "
        "earlier findings and to note what's changed if relevant, but treat the "
        "current search results as the primary source of truth:\n\n"
        + "\n\n".join(blocks)
    )