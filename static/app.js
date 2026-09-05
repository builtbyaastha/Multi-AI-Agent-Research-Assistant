const NODE_LABELS = {
  recall: "Recall",
  search: "Search",
  read: "Read",
  write: "Write",
  critique: "Critique",
  store: "Store",
};

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const promptForm = document.getElementById("promptForm");
const topicInput = document.getElementById("topicInput");
const submitBtn = document.getElementById("submitBtn");
const logPanel = document.getElementById("logPanel");
const log = document.getElementById("log");
const reportPanel = document.getElementById("reportPanel");
const reportEl = document.getElementById("report");

let ws = null;
let seenNodes = new Map(); // node name -> log line element, so revisions update in place for "write"/"critique"

function setConnectionStatus(online) {
  statusDot.classList.toggle("status__dot--online", online);
  statusDot.classList.toggle("status__dot--offline", !online);
  statusText.textContent = online ? "connected" : "offline";
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/research`);

  ws.onopen = () => setConnectionStatus(true);
  ws.onclose = () => setConnectionStatus(false);
  ws.onerror = () => setConnectionStatus(false);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleMessage(msg);
  };
}

function resetRun() {
  log.innerHTML = "";
  reportEl.innerHTML = "";
  seenNodes = new Map();
  logPanel.hidden = false;
  reportPanel.hidden = true;
}

function glyphFor(status) {
  if (status === "running") return { char: "●", cls: "log__glyph--running" };
  if (status === "revise") return { char: "●", cls: "log__glyph--revise" };
  if (status === "done") return { char: "✓", cls: "log__glyph--done" };
  return { char: "○", cls: "" };
}

function addOrUpdateLine(node, detail, status) {
  const key = node;
  const label = NODE_LABELS[node] || node;
  const glyph = glyphFor(status);

  let line = seenNodes.get(key);
  if (!line) {
    line = document.createElement("div");
    line.className = "log__line";
    line.innerHTML = `
      <span class="log__glyph"></span>
      <span class="log__node">${label}</span>
      <span class="log__detail"></span>
    `;
    log.appendChild(line);
    seenNodes.set(key, line);
  }

  line.querySelector(".log__glyph").textContent = glyph.char;
  line.querySelector(".log__glyph").className = `log__glyph ${glyph.cls}`;
  line.querySelector(".log__detail").textContent = detail;
  log.scrollTop = log.scrollHeight;
}

function renderReportMarkdownish(text) {
  // Lightweight structure for the report panel — not a full markdown
  // parser, just enough to make headers and bold text readable without
  // pulling in a dependency for a single panel.
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const withHeaders = escaped.replace(/^(#{1,3})\s+(.*)$/gm, (_, hashes, content) => {
    const level = hashes.length;
    return `<h${level}>${content}</h${level}>`;
  });

  const withBold = withHeaders.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  return withBold;
}

function handleMessage(msg) {
  if (msg.type === "start") {
    resetRun();
    addOrUpdateLine("recall", "checking memory...", "running");
    return;
  }

  if (msg.type === "node") {
    const status = msg.node === "critique" && msg.preview.includes("revise")
      ? "revise"
      : "done";
    addOrUpdateLine(msg.node, msg.preview, status);

    // Mark the next expected node as running, purely for a live feel —
    // the graph itself doesn't tell us "about to start," only "just
    // finished," so we infer the next step optimistically.
    const order = ["recall", "search", "read", "write", "critique", "store"];
    const idx = order.indexOf(msg.node);
    if (idx !== -1 && idx < order.length - 1) {
      const next = order[idx + 1];
      if (!seenNodes.has(next)) {
        addOrUpdateLine(next, "running...", "running");
      }
    }
    return;
  }

  if (msg.type === "complete") {
    // Clear any stray "running" line left over (e.g. store already done).
    seenNodes.forEach((line, key) => {
      const glyphEl = line.querySelector(".log__glyph");
      if (glyphEl.textContent === "●" && glyphEl.classList.contains("log__glyph--running")) {
        glyphEl.textContent = "✓";
        glyphEl.className = "log__glyph log__glyph--done";
      }
    });

    reportPanel.hidden = false;
    reportEl.innerHTML = renderReportMarkdownish(msg.report);
    submitBtn.disabled = false;
    submitBtn.textContent = "run";
    return;
  }

  if (msg.type === "error") {
    resetRun();
    logPanel.hidden = false;
    const line = document.createElement("div");
    line.className = "log__line error";
    line.textContent = `error: ${msg.message}`;
    log.appendChild(line);
    submitBtn.disabled = false;
    submitBtn.textContent = "run";
  }
}

promptForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  submitBtn.disabled = true;
  submitBtn.textContent = "running";
  ws.send(JSON.stringify({ topic }));
});

connect();