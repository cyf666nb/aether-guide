const state = {
  sessionId: null,
  socket: null,
};

const scenicId = document.querySelector("#scenicId");
const createSession = document.querySelector("#createSession");
const sendMessage = document.querySelector("#sendMessage");
const refreshLandmarks = document.querySelector("#refreshLandmarks");
const promptInput = document.querySelector("#prompt");
const messages = document.querySelector("#messages");
const statusBadge = document.querySelector("#status");
const traceId = document.querySelector("#traceId");
const landmarks = document.querySelector("#landmarks");

function setStatus(label, online) {
  statusBadge.textContent = label;
  statusBadge.className = `status ${online ? "online" : "offline"}`;
}

function addMessage(speaker, text, className) {
  const article = document.createElement("article");
  article.className = `message ${className}`;
  const speakerNode = document.createElement("span");
  speakerNode.className = "speaker";
  speakerNode.textContent = speaker;
  const textNode = document.createElement("p");
  textNode.textContent = text;
  article.append(speakerNode, textNode);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  traceId.textContent = payload.trace_id || response.headers.get("X-Trace-Id") || "missing";
  if (!response.ok) {
    throw new Error(payload.message || "Request failed");
  }
  return payload.data;
}

async function loadLandmarks() {
  const data = await requestJson(`/api/v1/landmarks?scenic_id=${encodeURIComponent(scenicId.value)}`);
  landmarks.innerHTML = "";
  for (const item of data.landmarks) {
    const node = document.createElement("article");
    node.className = "landmark";
    const title = document.createElement("h3");
    title.textContent = item.name;
    const summary = document.createElement("p");
    summary.textContent = item.summary;
    const tags = document.createElement("div");
    tags.className = "tags";
    for (const tag of item.tags) {
      const tagNode = document.createElement("span");
      tagNode.textContent = tag;
      tags.append(tagNode);
    }
    node.append(title, summary, tags);
    landmarks.append(node);
  }
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${protocol}://${location.host}/api/v1/sessions/${state.sessionId}/stream`);
  state.socket.addEventListener("open", () => {
    setStatus("ONLINE", true);
    sendMessage.disabled = false;
  });
  state.socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    traceId.textContent = payload.trace_id || "missing";
    addMessage("Guide", payload.data.content, "guide");
  });
  state.socket.addEventListener("close", () => {
    setStatus("OFFLINE", false);
    sendMessage.disabled = true;
  });
}

createSession.addEventListener("click", async () => {
  const data = await requestJson("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify({
      scenic_id: scenicId.value,
      user_id: "demo-visitor",
      locale: "zh-CN",
      idempotency_key: `demo-${Date.now()}`,
    }),
  });
  state.sessionId = data.id;
  addMessage("System", `Session ${data.id} created.`, "guide");
  connectSocket();
  await loadLandmarks();
});

sendMessage.addEventListener("click", () => {
  const text = promptInput.value.trim();
  if (!text || !state.socket || state.socket.readyState !== WebSocket.OPEN) {
    return;
  }
  addMessage("Visitor", text, "user");
  state.socket.send(JSON.stringify({ type: "user_text", text, locale: "zh-CN" }));
});

refreshLandmarks.addEventListener("click", loadLandmarks);
loadLandmarks().catch((error) => addMessage("System", error.message, "guide"));
