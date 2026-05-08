const STORAGE_KEY = "ai-db-chatbot-chats";
const ACTIVE_CHAT_KEY = "ai-db-chatbot-active-chat";

const state = {
  chats: [],
  activeChatId: null,
  sidebarOpen: false,
};

const elements = {
  sidebar: document.getElementById("sidebar"),
  sidebarBackdrop: document.getElementById("sidebarBackdrop"),
  chatHistoryList: document.getElementById("chatHistoryList"),
  chatTitle: document.getElementById("chatTitle"),
  emptyState: document.getElementById("emptyState"),
  messages: document.getElementById("messages"),
  chatContainer: document.getElementById("chatContainer"),
  chatForm: document.getElementById("chatForm"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
  newChatBtn: document.getElementById("newChatBtn"),
  exportChatBtn: document.getElementById("exportChatBtn"),
  clearChatBtn: document.getElementById("clearChatBtn"),
  mobileMenuBtn: document.getElementById("mobileMenuBtn"),
  mobileCloseBtn: document.getElementById("mobileCloseBtn"),
  typingIndicator: document.getElementById("typingIndicator"),
  charCount: document.getElementById("charCount"),
};

marked.setOptions({
  gfm: true,
  breaks: true,
});

document.addEventListener("DOMContentLoaded", () => {
  wireEvents();
  loadChats();
  void syncHistoryHints();
});

function wireEvents() {
  elements.chatForm.addEventListener("submit", onSubmit);
  elements.messageInput.addEventListener("input", autoResizeInput);
  elements.messageInput.addEventListener("input", updateCharCount);
  elements.messageInput.addEventListener("keydown", handleComposerKeys);
  elements.newChatBtn.addEventListener("click", () => void createNewChat());
  elements.exportChatBtn.addEventListener("click", exportActiveChat);
  elements.clearChatBtn.addEventListener("click", clearActiveChat);
  elements.mobileMenuBtn.addEventListener("click", () => toggleSidebar(true));
  elements.mobileCloseBtn.addEventListener("click", () => toggleSidebar(false));
  elements.sidebarBackdrop.addEventListener("click", () => toggleSidebar(false));

  document.querySelectorAll(".suggestion-pill").forEach((button) => {
    button.addEventListener("click", () => {
      elements.messageInput.value = button.dataset.suggestion || "";
      autoResizeInput();
      updateCharCount();
      elements.messageInput.focus();
    });
  });
}

function loadChats() {
  try {
    state.chats = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch (error) {
    state.chats = [];
  }

  state.activeChatId = localStorage.getItem(ACTIVE_CHAT_KEY);
  if (!state.chats.length) {
    void createNewChat();
    return;
  }

  if (!state.activeChatId || !state.chats.some((chat) => chat.id === state.activeChatId)) {
    state.activeChatId = state.chats[0].id;
  }

  render();
}

function saveChats() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.chats));
  if (state.activeChatId) {
    localStorage.setItem(ACTIVE_CHAT_KEY, state.activeChatId);
  }
}

function getActiveChat() {
  return state.chats.find((chat) => chat.id === state.activeChatId) || null;
}

async function createNewChat(title = "New chat") {
  try {
    const response = await fetch("/new-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error("Failed to create a chat session.");
    }

    const session = await response.json();
    const chat = {
      id: session.chat_id,
      title: session.title || title,
      createdAt: session.created_at,
      updatedAt: session.updated_at,
      messages: [],
    };

    state.chats.unshift(chat);
    state.activeChatId = chat.id;
    saveChats();
    render();
    toggleSidebar(false);
  } catch (error) {
    showToast(error.message || "Unable to create a new chat.");
  }
}

async function syncHistoryHints() {
  try {
    const response = await fetch("/history");
    if (!response.ok) {
      return;
    }

    const sessions = await response.json();
    const lookup = new Map(sessions.map((session) => [session.chat_id, session]));
    state.chats = state.chats.map((chat) => {
      const serverSession = lookup.get(chat.id);
      if (!serverSession) {
        return chat;
      }
      return {
        ...chat,
        title: chat.title === "New chat" ? serverSession.title : chat.title,
        updatedAt: serverSession.updated_at,
      };
    });
    saveChats();
    renderSidebar();
  } catch (error) {
    console.debug("History sync skipped:", error);
  }
}

async function onSubmit(event) {
  event.preventDefault();
  const message = elements.messageInput.value.trim();
  if (!message) {
    return;
  }

  const activeChat = getActiveChat();
  if (!activeChat) {
    await createNewChat();
  }

  const chat = getActiveChat();
  if (!chat) {
    return;
  }

  const userMessage = createMessage("user", message);
  chat.messages.push(userMessage);
  chat.updatedAt = new Date().toISOString();

  if (chat.title === "New chat") {
    chat.title = trimTitle(message);
  }

  const assistantMessage = createMessage("assistant", "");
  assistantMessage.streaming = true;
  assistantMessage.pending = true;
  chat.messages.push(assistantMessage);

  elements.messageInput.value = "";
  autoResizeInput();
  updateCharCount();
  elements.sendBtn.disabled = true;
  showTyping(true);
  saveChats();
  render();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chat.id,
        message,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "The assistant could not process your request.");
    }

    assistantMessage.summary = payload.summary;
    assistantMessage.markdown = payload.markdown;
    assistantMessage.tableData = payload.table_data || [];
    assistantMessage.rawData = payload.raw_data || [];
    assistantMessage.sqlUsed = payload.sql_used || "";
    assistantMessage.timestamp = payload.timestamp || new Date().toISOString();
    assistantMessage.pending = false;

    await streamAssistantMessage(chat.id, assistantMessage.id, payload.markdown || payload.summary);
  } catch (error) {
    assistantMessage.pending = false;
    assistantMessage.streaming = false;
    assistantMessage.error = true;
    assistantMessage.markdown = `**Request failed**\n\n${error.message || "An unexpected error occurred."}`;
    assistantMessage.timestamp = new Date().toISOString();
    render();
    showToast(error.message || "Request failed.");
  } finally {
    elements.sendBtn.disabled = false;
    showTyping(false);
    saveChats();
    renderSidebar();
  }
}

function createMessage(role, content) {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    markdown: content,
    timestamp: new Date().toISOString(),
    streaming: false,
    pending: false,
    tableData: [],
    rawData: [],
    sqlUsed: "",
  };
}

async function streamAssistantMessage(chatId, messageId, markdown) {
  const chat = state.chats.find((item) => item.id === chatId);
  if (!chat) {
    return;
  }

  const message = chat.messages.find((item) => item.id === messageId);
  if (!message) {
    return;
  }

  message.streaming = true;
  const tokens = markdown.split(/(\s+)/);
  let current = "";

  for (const token of tokens) {
    current += token;
    message.markdown = current;
    renderMessages();
    scrollToBottom();
    await wait(18);
  }

  message.markdown = markdown;
  message.streaming = false;
  saveChats();
  renderMessages();
  scrollToBottom();
}

function render() {
  renderSidebar();
  renderMessages();
}

function renderSidebar() {
  elements.chatHistoryList.innerHTML = "";

  state.chats
    .slice()
    .sort((left, right) => new Date(right.updatedAt) - new Date(left.updatedAt))
    .forEach((chat) => {
      const button = document.createElement("button");
      button.className = `history-item ${chat.id === state.activeChatId ? "active" : ""}`;
      button.innerHTML = `
        <div class="history-item-title">${escapeHtml(chat.title)}</div>
        <div class="history-item-time">${formatTimestamp(chat.updatedAt)}</div>
      `;
      button.addEventListener("click", () => {
        state.activeChatId = chat.id;
        saveChats();
        render();
        toggleSidebar(false);
      });
      elements.chatHistoryList.appendChild(button);
    });
}

function renderMessages() {
  const chat = getActiveChat();
  elements.messages.innerHTML = "";

  if (!chat) {
    elements.emptyState.classList.remove("hidden");
    elements.chatTitle.textContent = "New chat";
    return;
  }

  elements.chatTitle.textContent = chat.title;
  const hasMessages = chat.messages.length > 0;
  elements.emptyState.classList.toggle("hidden", hasMessages);

  chat.messages.forEach((message) => {
    const row = document.createElement("article");
    row.className = "message-row";

    const avatar = document.createElement("div");
    avatar.className = `avatar ${message.role}`;
    avatar.innerHTML =
      message.role === "assistant"
        ? '<i class="fa-solid fa-sparkles"></i>'
        : '<i class="fa-solid fa-user"></i>';

    const card = document.createElement("div");
    card.className = `message-card ${message.role}`;

    const bodyClass = message.streaming ? "message-body streaming-cursor" : "message-body";
    const showCopy = message.role === "assistant";
    card.innerHTML = `
      <div class="message-meta">
        <span>${message.role === "assistant" ? "Assistant" : "You"} - ${formatTimestamp(message.timestamp)}</span>
        <div class="message-actions">
          ${showCopy ? `<button class="icon-action" data-copy="${message.id}" title="Copy response"><i class="fa-regular fa-copy"></i></button>` : ""}
        </div>
      </div>
      <div class="${bodyClass}" data-message-body="${message.id}"></div>
    `;

    row.appendChild(avatar);
    row.appendChild(card);
    elements.messages.appendChild(row);

    const body = card.querySelector(`[data-message-body="${message.id}"]`);
    if (message.role === "assistant") {
      body.innerHTML = marked.parse(message.markdown || "");
      if (!message.streaming && Array.isArray(message.tableData) && message.tableData.length && !body.querySelector("table")) {
        body.insertAdjacentHTML("beforeend", buildStructuredTable(message.tableData));
      }
    } else {
      body.innerHTML = `<p>${escapeHtml(message.content)}</p>`;
    }

    const copyButton = card.querySelector(`[data-copy="${message.id}"]`);
    if (copyButton) {
      copyButton.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(message.markdown || message.summary || "");
          showToast("Response copied to clipboard.");
        } catch (error) {
          showToast("Unable to copy response.");
        }
      });
    }
  });

  scrollToBottom();
}

function buildStructuredTable(rows) {
  if (!rows.length) {
    return "";
  }

  const headers = Object.keys(rows[0]);
  const head = headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
  const body = rows
    .map((row) => {
      const cells = headers.map((header) => `<td>${escapeHtml(String(row[header] ?? ""))}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  return `
    <div class="structured-table">
      <div class="structured-table-caption">Structured result preview</div>
      <table>
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function clearActiveChat() {
  const chat = getActiveChat();
  if (!chat) {
    return;
  }

  const shouldClear = window.confirm("Clear the current conversation?");
  if (!shouldClear) {
    return;
  }

  chat.messages = [];
  chat.title = "New chat";
  chat.updatedAt = new Date().toISOString();
  saveChats();
  render();
}

function exportActiveChat() {
  const chat = getActiveChat();
  if (!chat) {
    return;
  }

  const transcript = [
    `# ${chat.title}`,
    "",
    ...chat.messages.flatMap((message) => [
      `## ${message.role === "assistant" ? "Assistant" : "You"} - ${formatTimestamp(message.timestamp)}`,
      "",
      message.role === "assistant" ? message.markdown || "" : message.content,
      "",
    ]),
  ].join("\n");

  const blob = new Blob([transcript], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${chat.title.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "chat"}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function autoResizeInput() {
  const input = elements.messageInput;
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 240)}px`;
}

function updateCharCount() {
  const count = elements.messageInput.value.length;
  elements.charCount.textContent = `${count} / 2000`;
}

function handleComposerKeys(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
}

function showTyping(visible) {
  elements.typingIndicator.classList.toggle("hidden", !visible);
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
  });
}

function toggleSidebar(visible) {
  state.sidebarOpen = visible;
  elements.sidebar.classList.toggle("open", visible);
  elements.sidebarBackdrop.classList.toggle("open", visible);
}

function trimTitle(text) {
  const collapsed = text.replace(/\s+/g, " ").trim();
  return collapsed.length > 42 ? `${collapsed.slice(0, 42)}...` : collapsed;
}

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Just now";
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    day: "numeric",
  }).format(date);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.textContent = message;
  toast.style.position = "fixed";
  toast.style.right = "20px";
  toast.style.bottom = "20px";
  toast.style.zIndex = "60";
  toast.style.padding = "0.85rem 1rem";
  toast.style.borderRadius = "0.95rem";
  toast.style.background = "rgba(24, 24, 24, 0.96)";
  toast.style.border = "1px solid rgba(255,255,255,0.08)";
  toast.style.color = "var(--text)";
  toast.style.boxShadow = "0 20px 40px rgba(0,0,0,0.22)";
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2600);
}
