# Multi-Agent AI Research Assistant

An agentic research pipeline that searches the web, reads and synthesizes sources, writes a structured report, and critiques its own output — revising itself when the critique falls short — built on a real [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph` with conditional routing, persistent memory, and a live execution view.

> Live demo: `[add your Render URL here once deployed]`

---

## Screenshots

<!-- Replace these with real screenshots once you have them. Suggested shots:
     1. The FastAPI terminal-style UI mid-run (a node glowing/active)
     2. The same UI with a finished report rendered
     3. A revise-loop moment (critic verdict: revise, second write pass visible)
     4. The Streamlit UI, if you keep it as a secondary interface
     5. A terminal screenshot of `python eval.py` showing pass/fail results
     6. GitHub Actions tab showing a green CI run
-->

**Live pipeline execution**
`<img width="1896" height="1074" alt="image" src="https://github.com/user-attachments/assets/59c4e88d-9a01-4e3c-9599-3db3d3ba8b04" />
`

**Finished report**
`<img width="1899" height="1066" alt="image" src="https://github.com/user-attachments/assets/bcc0cb50-07e1-478b-b2a9-f4627f6b3c8f" />
`

---

## Overview

This project automates end-to-end research: given a topic, it searches the web, extracts and synthesizes information from real sources, writes a structured report, and evaluates its own output for quality — sending the draft back for revision when it falls short, up to a capped number of retries. Past reports are stored in a vector memory store so related future queries can build on prior research instead of starting cold.

It started as a linear, tutorial-style pipeline (Search → Reader → Writer → Critic, called in sequence) and was rebuilt into a real graph-based agent system with actual conditional branching, a genuine self-revision loop, structured/validated model output, prompt-injection defenses, automated evaluation, and CI/CD — the things that separate a working demo from a system that's actually been hardened.

## What makes this different from a typical multi-agent tutorial project

- **An actual LangGraph `StateGraph`, not a disguised list of function calls.** The graph has a real conditional edge: the Critic node can route back to the Writer node (capped at a configurable number of revisions) instead of always ending after one pass.
- **A found-and-fixed real bug, not just a feature list.** The local model backing the critic occasionally scored quality on a 0–100 scale despite being told 1–10 — caught via a Pydantic `field_validator`, normalized instead of silently accepted, with the routing decision then derived deterministically from the corrected score rather than trusted from a second model-generated field.
- **A real prompt-injection surface, actually guarded.** Scraped web content is sanitized against common injection patterns and wrapped in explicit untrusted-content delimiters before it ever reaches the LLM — because arbitrary scraped text is untrusted input, not a detail to overlook.
- **Evaluation that isn't circular.** A golden-query dataset is scored by an LLM judge that is *separate* from the in-pipeline Critic — the Critic already approved everything that reaches the eval script, so re-using it there would just be checking its own homework.
- **CI/CD that reflects a real cost tradeoff.** Fast, deterministic checks (lint + unit tests) run on every push. The full LLM-dependent eval suite is gated behind a manual/scheduled workflow instead, since running a live model on every commit is slow, costly, and flaky — a deliberate choice, not a missing feature.
- **A configurable LLM backend.** Local (Ollama/Mistral — free, private, offline, but CPU-bound and slow without a GPU) or cloud (Gemini free tier — fast, needs an API key) via a single environment variable, so the same code runs in both a fully offline dev setup and a deployed demo.

## System architecture

```
                          ┌─────────────┐
                          │   recall    │  check memory for related past research
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                          │   search    │  Exa API — real web search, no LLM call
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                          │    read     │  scrape top sources, extract key info
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                    ┌────►│    write    │  draft or revise the report
                    │     └──────┬──────┘
                    │            │
                    │     ┌──────▼──────┐
                    │     │  critique   │  structured verdict: approve / revise
                    │     └──────┬──────┘
                    │            │
              revise│      ┌─────┴─────┐
                    └──────┤  approve? ├──── yes ──► store ──► END
                           └───────────┘
                    (capped at max_revisions)
```

Six nodes: **recall → search → read → write → critique → (revise loop back to write, or) → store**.

### Node responsibilities

**Recall** — checks Chroma vector memory for related prior research before doing any new work. Cold start ("no related research found") is expected and correct on a first run.

**Search** — a direct call to the Exa search API. No LLM reasoning involved: this step always searches, so there's no decision for a model to make, and skipping the agent-reasoning wrapper here removes an unnecessary inference pass.

**Read** — extracts the actual URLs from search results, scrapes each one directly, and uses an LLM to extract key findings from the *real page content* — not a re-summary of a 200-character search snippet, which is what the original agent-based version risked doing without any guarantee it ever actually scraped anything.

**Write** — drafts the report from search + extracted content (+ prior memory context, if any). On a revision pass, it's given the critic's specific feedback and instructed to address it directly rather than producing a fresh, unrelated draft.

**Critique** — evaluates the draft against factual consistency, hallucination risk, completeness, and clarity, returning a **structured** `quality_score` (1–10, normalized), `verdict` (approve/revise), and specific `feedback` — not free-text commentary the graph would have to parse.

**Store** — once the loop ends (approved, or `max_revisions` reached), the finished report is saved to memory for future recall.

## Evaluation

A golden-query dataset (topics + explicit, checkable criteria — not vague "is this good") is scored by an independent LLM judge, separate from the in-pipeline Critic:

```bash
python eval.py --limit 2          # quick smoke test
python eval.py --save results.json   # full run, saves results
```

`[Add your actual pass rate here once you have a clean run, e.g. "4/5 golden queries pass (80%)" — real numbers, not a placeholder, are what make this section credible.]`

## Tech stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph (`StateGraph`, conditional edges, streaming) |
| LLM framework | LangChain |
| LLM backends | Ollama (Mistral, local) / Google Gemini (cloud, free tier) — configurable |
| Structured output | Pydantic (validators, normalization) |
| Web search | Exa API |
| Web scraping | BeautifulSoup, Requests |
| Long-term memory | ChromaDB (ONNX-based embeddings, no PyTorch dependency) |
| Backend / API | FastAPI, WebSockets, Uvicorn |
| Frontend | Custom HTML/CSS/JS (live pipeline view) + Streamlit (secondary UI) |
| Tool protocol | MCP (Model Context Protocol) — search/scrape tools exposed as an MCP server |
| Testing | pytest |
| Linting | ruff |
| CI/CD | GitHub Actions (fast deterministic checks on every push; full LLM eval as a manual/scheduled workflow) |
| Package management | uv |
| Deployment | Render (free tier) |

## Project structure

```
Multi-AI-Agent-Research-Assistant/
│
├── pipeline.py          # LangGraph StateGraph, node logic, revise loop
├── agents.py             # LLM backend config, search/reader functions, writer/critic chains
├── tools.py               # Exa search, web scraping, prompt-injection guard
├── memory.py             # ChromaDB-backed long-term memory
├── eval.py                # Golden-query eval harness with independent LLM judge
├── mcp_server.py          # MCP server exposing search/scrape tools
│
├── app.py                 # Streamlit UI (secondary)
├── app_server.py          # FastAPI + WebSocket backend (primary UI)
├── static/                # Frontend: index.html, style.css, app.js
│
├── tests/
│   └── test_guards.py     # Fast, deterministic unit tests (no LLM/network calls)
│
├── .github/workflows/
│   ├── ci.yml              # Lint + unit tests, every push
│   └── eval-manual.yml    # Full LLM eval, manual/scheduled trigger
│
├── requirements.txt         # Full local dev environment
├── requirements-deploy.txt  # Minimal deployment footprint (no torch/jupyter/streamlit)
├── pyproject.toml / uv.lock
└── README.md
```

## Installation (local development)

### Clone the repository
```bash
git clone https://github.com/builtbyaastha/Multi-AI-Agent-Research-Assistant.git
cd Multi-AI-Agent-Research-Assistant
```

### Set up the environment
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Configure environment variables
Create a `.env` file:
```env
EXA_API_KEY=your_exa_api_key

# Optional: switch to Gemini instead of local Ollama
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=your_gemini_api_key
```

### Pull the local model (if using Ollama, the default)
```bash
ollama pull mistral
```

### Run it

**FastAPI UI (primary — live pipeline view):**
```bash
uvicorn app_server:app --reload
```
Open `http://localhost:8000`.

**Streamlit UI (secondary):**
```bash
streamlit run app.py
```

**Pipeline directly, from the terminal:**
```bash
python pipeline.py
```

**MCP server** (exposes search/scrape as standard MCP tools):
```bash
python mcp_server.py
```

## Testing

```bash
pytest tests/test_guards.py -v
```

Fast, deterministic, no LLM or network calls — covers the score-normalization validator and the prompt-injection guard.

## CI/CD

- **`ci.yml`** — runs on every push/PR: `ruff` lint + the deterministic unit tests. Fast, free, can't be flaky.
- **`eval-manual.yml`** — the full LLM-dependent eval suite, gated behind a manual trigger or weekly schedule, since it needs a live model and real API calls, which don't belong in a check that runs on every single commit.

## Deployment

Deployed on Render's free tier using Gemini as the LLM backend (`LLM_PROVIDER=gemini`) — free hosting can't run a local model, so the deployed instance and the local dev setup deliberately use different backends via the same configurable switch. See `requirements-deploy.txt` for the minimal dependency set used in production (no PyTorch, Jupyter, or Streamlit — see the note in that file for why).

## Known limitations

- The prompt-injection guard is pattern-matching on common phrasings, not a robust classifier — a rephrased or obfuscated injection could still slip through. It's a first line of defense, not a complete one.
- Structured LLM output (score, verdict) is more reliable with cloud models than with the local Mistral backend; a `field_validator` and fail-open fallback handle the cases where it doesn't come back clean.
- Chroma memory has no persistent disk on the free-tier deployment, so it resets on restart/redeploy there (it does persist locally).
- The MCP server is built and functional but not yet wired into the deployed app — currently a standalone, locally runnable component.

## What I learned

Building and hardening this project involved:
- Designing real conditional graph logic (not just sequential chaining) with LangGraph
- Debugging and fixing a live structured-output bug in a local LLM (score scale confusion) with Pydantic validators
- Building and reasoning about a genuine prompt-injection attack surface
- Designing an evaluation methodology that avoids circularity (independent judge vs. in-pipeline critic)
- Making and defending a CI/CD cost/reliability tradeoff for LLM-dependent testing
- Diagnosing a production memory/dependency issue (PyTorch bloat causing an OOM crash) and fixing it at the architecture level, not just increasing resources
- Building a real-time streaming UI over LangGraph's native `.stream()` API via FastAPI WebSockets

## Author

Aastha Sinha
