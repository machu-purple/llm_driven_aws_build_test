const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const messagesEl = document.getElementById("messages");

function addMessage(role, content, isError = false) {
  const div = document.createElement("div");
  div.className = "message " + (isError ? "error" : role);
  const roleLabel = role === "user" ? "あなた" : "アシスタント";
  div.innerHTML = `<span class="role">${roleLabel}</span><div>${escapeHtml(content)}</div>`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function setLoading(loading) {
  sendBtn.disabled = loading;
  sendBtn.textContent = loading ? "送信中..." : "送信";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  addMessage("user", text);
  setLoading(true);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();

    if (!res.ok) {
      addMessage("assistant", data.detail || "エラーが発生しました", true);
      return;
    }
    addMessage("assistant", data.reply);
  } catch (err) {
    addMessage("assistant", "通信エラー: " + err.message, true);
  } finally {
    setLoading(false);
  }
});
