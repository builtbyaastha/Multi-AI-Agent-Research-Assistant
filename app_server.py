"""
FastAPI backend for the research assistant — replaces the Streamlit app.py.

Serves the static frontend and exposes a WebSocket endpoint that runs the
LangGraph pipeline via .stream() instead of .invoke(), so the frontend gets
a message the moment each node finishes rather than waiting for the whole
run to complete. This is a real LangGraph feature (streaming node updates),
not a custom hack — it's the natural way to show live execution progress
for a graph-based agent pipeline.

LangGraph's .stream() is a synchronous generator, and it blocks on real
work (LLM calls, HTTP requests) for tens of seconds at a time. Running it
directly inside an async websocket handler would freeze the event loop for
that whole duration. Instead, it runs in a background thread that pushes
each step into a queue, and the async handler drains that queue and forwards
each step to the browser over the websocket — this keeps the server
responsive and lets updates reach the browser the instant each node
finishes, not in one batch at the end.

Run:
    uvicorn app_server:app --reload
Then open http://localhost:8000
"""

import asyncio
import queue
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pipeline import build_graph

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


def _preview_for_node(node: str, update: dict, state_acc: dict) -> str:
    """
    Short, human-readable one-liner for the live log, per node type. Keeps
    the frontend from needing to know anything about the pipeline's
    internal state shape.
    """
    if node == "recall":
        ctx = update.get("related_context", "")
        return "found related prior research" if ctx else "no related prior research found"
    if node == "search":
        result = update.get("search_result", "")
        count = result.count("URL:")
        return f"{count} source(s) found" if count else "search returned no clear sources"
    if node == "read":
        content = update.get("scraped_content", "")
        return f"extracted {len(content)} chars of key information"
    if node == "write":
        is_revision = state_acc.get("revision_count", 0) > 0
        return "revised draft based on feedback" if is_revision else "drafted initial report"
    if node == "critique":
        score = update.get("quality_score", "?")
        verdict = update.get("verdict", "?")
        return f"verdict: {verdict} (score {score}/10)"
    if node == "store":
        return "saved to memory"
    return ""


async def _run_pipeline_streaming(topic: str, websocket: WebSocket) -> dict:
    initial_state = {
        "query": topic,
        "related_context": "",
        "search_result": "",
        "scraped_content": "",
        "report": "",
        "feedback": "",
        "quality_score": 0,
        "verdict": "revise",
        "revision_count": 0,
        "max_revisions": 2,
    }

    q: "queue.Queue" = queue.Queue()

    def worker():
        try:
            graph = build_graph()
            for step in graph.stream(initial_state):
                q.put(("step", step))
        except Exception as e:
            q.put(("error", str(e)))
        finally:
            q.put(("done", None))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    loop = asyncio.get_event_loop()
    state_acc = dict(initial_state)

    while True:
        kind, payload = await loop.run_in_executor(None, q.get)

        if kind == "done":
            break

        if kind == "error":
            await websocket.send_json({"type": "error", "message": payload})
            break

        if kind == "step":
            for node_name, update in payload.items():
                # LangGraph can emit internal completion markers (e.g. a
                # dunder-prefixed key with a None value) alongside real node
                # updates once the graph reaches END. Skip those — they're
                # not one of our actual pipeline nodes and update would be
                # None, which dict.update() can't handle.
                if update is None or node_name.startswith("__"):
                    continue
                state_acc.update(update)
                await websocket.send_json({
                    "type": "node",
                    "node": node_name,
                    "revision_count": state_acc.get("revision_count", 0),
                    "preview": _preview_for_node(node_name, update, state_acc),
                })

    return state_acc


@app.websocket("/ws/research")
async def research_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        topic = (data.get("topic") or "").strip()

        if not topic:
            await websocket.send_json({"type": "error", "message": "Enter a topic to research."})
            await websocket.close()
            return

        await websocket.send_json({"type": "start", "topic": topic})

        final_state = await _run_pipeline_streaming(topic, websocket)

        await websocket.send_json({
            "type": "complete",
            "report": final_state.get("report", ""),
            "quality_score": final_state.get("quality_score", 0),
            "revision_count": final_state.get("revision_count", 0),
            "verdict": final_state.get("verdict", "unknown"),
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass