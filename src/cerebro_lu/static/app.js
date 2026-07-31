const elements = {
  connection: document.querySelector("#connection-status"),
  sessionId: document.querySelector("#session-id"),
  messages: document.querySelector("#messages"),
  messageInput: document.querySelector("#message-input"),
  sendButton: document.querySelector("#send-message"),
  newSession: document.querySelector("#new-session"),
  copySession: document.querySelector("#copy-session"),
  scenarios: document.querySelectorAll("[data-message]"),
  orderScenario: document.querySelector("#order-scenario"),
  orderScenarioLabel: document.querySelector("#order-scenario-label"),
  httpStatus: document.querySelector("#http-status"),
  requestTime: document.querySelector("#request-time"),
  requestJson: document.querySelector("#request-json"),
  responseJson: document.querySelector("#response-json"),
  requestTab: document.querySelector("#request-tab"),
  responseTab: document.querySelector("#response-tab"),
  requestPanel: document.querySelector("#request-panel"),
  responsePanel: document.querySelector("#response-panel"),
  copyRequest: document.querySelector("#copy-request"),
  copyResponse: document.querySelector("#copy-response"),
  orderId: document.querySelector("#order-id"),
  orderState: document.querySelector("#order-state"),
  pixCode: document.querySelector("#pix-code"),
  copyPix: document.querySelector("#copy-pix"),
  toast: document.querySelector("#toast"),
};

let busy = false;
let lastOrderId = "";
let lastPixCode = "";
let toastTimer;

function makeSessionId() {
  if (window.crypto && window.crypto.randomUUID) {
    return `demo-${window.crypto.randomUUID().slice(0, 8)}`;
  }
  return `demo-${Date.now().toString(36)}`;
}

function loadSession() {
  const saved = window.localStorage.getItem("cerebro-lu-session");
  elements.sessionId.value = saved || makeSessionId();
  persistSession();
  updateRequestPreview();
}

function persistSession() {
  const value = elements.sessionId.value.trim() || makeSessionId();
  elements.sessionId.value = value;
  window.localStorage.setItem("cerebro-lu-session", value);
}

function updateRequestPreview(message = "...") {
  elements.requestJson.textContent = JSON.stringify(
    {
      session_id: elements.sessionId.value.trim() || "...",
      message,
    },
    null,
    2,
  );
}

function appendMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "VO" : "LU";

  const content = document.createElement("div");
  const author = document.createElement("span");
  author.className = "message-author";
  author.textContent = role === "user" ? "Voce" : "Lu";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;

  content.append(author, paragraph);
  article.append(avatar, content);
  elements.messages.append(article);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return article;
}

function appendLoading() {
  const article = document.createElement("article");
  article.className = "message assistant loading";
  article.innerHTML = `
    <div class="avatar" aria-hidden="true">LU</div>
    <div>
      <span class="message-author">Lu</span>
      <p aria-label="Processando">
        <span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>
      </p>
    </div>
  `;
  elements.messages.append(article);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return article;
}

function setBusy(value) {
  busy = value;
  elements.sendButton.disabled = value;
  elements.messageInput.disabled = value;
  elements.scenarios.forEach((button) => {
    button.disabled = value;
  });
  elements.orderScenario.disabled = value || !lastOrderId;
  elements.sendButton.querySelector("span").textContent = value ? "Enviando" : "Enviar";
}

function switchTab(name) {
  const requestActive = name === "request";
  elements.requestTab.classList.toggle("active", requestActive);
  elements.responseTab.classList.toggle("active", !requestActive);
  elements.requestTab.setAttribute("aria-selected", String(requestActive));
  elements.responseTab.setAttribute("aria-selected", String(!requestActive));
  elements.requestPanel.hidden = !requestActive;
  elements.responsePanel.hidden = requestActive;
}

function extractOrderData(responseText) {
  const orderMatch = responseText.match(/PED-\d{8}-[0-9A-F]{6}/i);
  const pixMatch = responseText.match(/PIX copia-e-cola:\s*([^.]+(?:\.[^.]+)*?)(?:\.\s+Esvaziei|$)/i);

  if (orderMatch) {
    lastOrderId = orderMatch[0].toUpperCase();
    elements.orderId.textContent = lastOrderId;
    elements.orderState.textContent = "Criado";
    elements.orderScenario.disabled = false;
    elements.orderScenario.dataset.message = `Qual e o status do pedido ${lastOrderId}?`;
    elements.orderScenarioLabel.textContent = lastOrderId;
  }

  if (pixMatch) {
    lastPixCode = pixMatch[1].trim();
    elements.pixCode.textContent = lastPixCode;
    elements.copyPix.disabled = false;
  }

  const statusMatch = responseText.match(/status:\s*(Processando|Enviado)/i);
  if (statusMatch) {
    elements.orderState.textContent = statusMatch[1];
  }
}

async function sendMessage(message) {
  const trimmed = message.trim();
  if (!trimmed || busy) {
    return;
  }

  persistSession();
  const payload = {
    session_id: elements.sessionId.value,
    message: trimmed,
  };

  elements.messageInput.value = "";
  resizeTextarea();
  appendMessage("user", trimmed);
  updateRequestPreview(trimmed);
  elements.responseJson.textContent = "Processando...";
  elements.httpStatus.textContent = "Enviando";
  elements.httpStatus.className = "http-status";
  elements.requestTime.textContent = "--";
  switchTab("request");
  setBusy(true);

  const loading = appendLoading();
  const startedAt = performance.now();

  try {
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const elapsed = Math.round(performance.now() - startedAt);
    const data = await response.json();

    loading.remove();
    elements.requestTime.textContent = `${elapsed} ms`;
    elements.httpStatus.textContent = `${response.status} ${response.ok ? "OK" : "Erro"}`;
    elements.httpStatus.className = `http-status ${response.ok ? "success" : "error"}`;
    elements.responseJson.textContent = JSON.stringify(data, null, 2);
    switchTab("response");

    if (!response.ok) {
      throw new Error(data.detail ? JSON.stringify(data.detail) : "A API recusou a solicitacao.");
    }

    appendMessage("assistant", data.response);
    extractOrderData(data.response);
  } catch (error) {
    loading.remove();
    const elapsed = Math.round(performance.now() - startedAt);
    elements.requestTime.textContent = `${elapsed} ms`;
    elements.httpStatus.textContent = "Falha";
    elements.httpStatus.className = "http-status error";
    const messageText =
      error instanceof Error ? error.message : "Nao foi possivel acessar a API.";
    elements.responseJson.textContent = JSON.stringify({ error: messageText }, null, 2);
    appendMessage(
      "assistant",
      "Nao consegui concluir essa chamada. Confira se a API esta ativa e tente novamente.",
    );
    switchTab("response");
  } finally {
    setBusy(false);
    elements.messageInput.focus();
  }
}

function resizeTextarea() {
  elements.messageInput.style.height = "auto";
  elements.messageInput.style.height = `${Math.min(elements.messageInput.scrollHeight, 120)}px`;
}

async function copyText(value, successMessage) {
  if (!value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(value);
    showToast(successMessage);
  } catch {
    showToast("Nao foi possivel copiar automaticamente.");
  }
}

function showToast(message) {
  window.clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  toastTimer = window.setTimeout(() => elements.toast.classList.remove("visible"), 2200);
}

function resetSession() {
  const welcome = elements.messages.querySelector(".message.assistant");
  elements.messages.replaceChildren(welcome);
  elements.sessionId.value = makeSessionId();
  persistSession();
  lastOrderId = "";
  lastPixCode = "";
  elements.orderId.textContent = "--";
  elements.orderState.textContent = "Nenhum";
  elements.pixCode.textContent = "--";
  elements.copyPix.disabled = true;
  elements.orderScenario.disabled = true;
  elements.orderScenario.removeAttribute("data-message");
  elements.orderScenarioLabel.textContent = "Finalize uma compra antes";
  elements.httpStatus.textContent = "Aguardando";
  elements.httpStatus.className = "http-status";
  elements.requestTime.textContent = "--";
  elements.responseJson.textContent = "A resposta aparecera aqui.";
  updateRequestPreview();
  switchTab("request");
  showToast("Nova sessao criada.");
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("offline");
    }
    elements.connection.classList.add("online");
    elements.connection.classList.remove("offline");
    elements.connection.lastChild.textContent = " API online";
  } catch {
    elements.connection.classList.add("offline");
    elements.connection.classList.remove("online");
    elements.connection.lastChild.textContent = " API indisponivel";
  }
}

elements.sendButton.addEventListener("click", () => sendMessage(elements.messageInput.value));
elements.messageInput.addEventListener("input", resizeTextarea);
elements.messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(elements.messageInput.value);
  }
});
elements.sessionId.addEventListener("change", () => {
  persistSession();
  updateRequestPreview();
});
elements.scenarios.forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.message || ""));
});
elements.orderScenario.addEventListener("click", () => {
  sendMessage(elements.orderScenario.dataset.message || "");
});
elements.newSession.addEventListener("click", resetSession);
elements.copySession.addEventListener("click", () =>
  copyText(elements.sessionId.value, "Session ID copiado."),
);
elements.copyRequest.addEventListener("click", () =>
  copyText(elements.requestJson.textContent, "Request copiado."),
);
elements.copyResponse.addEventListener("click", () =>
  copyText(elements.responseJson.textContent, "Response copiado."),
);
elements.copyPix.addEventListener("click", () => copyText(lastPixCode, "Codigo PIX copiado."));
elements.requestTab.addEventListener("click", () => switchTab("request"));
elements.responseTab.addEventListener("click", () => switchTab("response"));

loadSession();
checkHealth();
