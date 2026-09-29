// MemoryDesk AI - Chat Controller Module

function fillPrompt(text) {
  const input = document.getElementById("chat-input");
  if (input) {
    input.value = text;
    input.focus();
  }
}

function appendMessage(role, text, metadata = {}) {
  const container = document.getElementById("chat-stream");
  if (!container) return;

  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.innerText = role === "user" ? "You" : "AI";

  const wrapper = document.createElement("div");
  wrapper.className = "msg-content-wrapper";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerText = text;
  wrapper.appendChild(bubble);

  // If assistant response with retrieved memories from Hindsight
  if (role === "assistant" && metadata.memories_used > 0) {
    const memBar = document.createElement("div");
    memBar.className = "memory-citation-bar";
    memBar.innerHTML = `<span>🧠</span> <strong>${metadata.memories_used} Hindsight memories recalled</strong> &bull; Click to inspect`;
    
    // Toggle details on click
    memBar.onclick = () => {
      if (metadata.retrieved_memories && metadata.retrieved_memories.length > 0) {
        const memList = metadata.retrieved_memories.map(m => `&bull; ${m.text}`).join("<br>");
        const detailBox = document.createElement("div");
        detailBox.style.marginTop = "0.35rem";
        detailBox.style.padding = "0.5rem 0.75rem";
        detailBox.style.background = "#f0fdf4";
        detailBox.style.border = "1px solid #bbf7d0";
        detailBox.style.borderRadius = "6px";
        detailBox.style.fontSize = "0.78rem";
        detailBox.style.color = "#166534";
        detailBox.innerHTML = `<strong>Recalled Memory Units:</strong><br>${memList}`;
        wrapper.appendChild(detailBox);
        memBar.onclick = null; // show once
      }
    };
    wrapper.appendChild(memBar);
  }

  // If new memory was stored in Hindsight
  if (role === "assistant" && metadata.memory_updated) {
    const updateBar = document.createElement("div");
    updateBar.className = "memory-update-banner";
    const storedExcerpt = metadata.new_memory_stored ? `: "${metadata.new_memory_stored.substring(0, 50)}..."` : "";
    updateBar.innerHTML = `<span>✓</span> <strong>Memory Retained in Hindsight</strong>${storedExcerpt}`;
    wrapper.appendChild(updateBar);
  }

  // If OS-Specific AutoFix Script was generated
  if (role === "assistant" && metadata.auto_fix_script) {
    const fix = metadata.auto_fix_script;
    const fixCard = document.createElement("div");
    fixCard.className = "autofix-card";
    const encoded = encodeURIComponent(fix.code);
    fixCard.innerHTML = `
      <div class="autofix-header">
        <span>⚡ OS-Adaptive Fix (${fix.os})</span>
        <div style="display: flex; gap: 0.4rem; align-items: center;">
          <span class="autofix-shell-badge">${fix.shell}</span>
          <button class="copy-btn" onclick="navigator.clipboard.writeText(decodeURIComponent('${encoded}')); showToast('Copied command to clipboard!', 'success');">
            📋 Copy
          </button>
        </div>
      </div>
      <div class="autofix-code">${fix.code}</div>
      <div style="padding: 0.4rem 0.85rem; font-size: 0.72rem; color: #94a3b8; background: #131d31; border-top: 1px solid #1e293b;">
        ${fix.explanation}
      </div>
    `;
    wrapper.appendChild(fixCard);
  }

  row.appendChild(avatar);
  row.appendChild(wrapper);
  container.appendChild(row);

  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
  const container = document.getElementById("chat-stream");
  const existing = document.getElementById("typing-indicator-row");
  if (existing) return;

  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.id = "typing-indicator-row";

  row.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-content-wrapper">
      <div class="msg-bubble" style="color: #64748b; font-style: italic; display: flex; align-items: center; gap: 0.5rem;">
        <span class="pulse-dot"></span>
        Querying Hindsight & generating response...
      </div>
    </div>
  `;
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator-row");
  if (el) el.remove();
}

async function sendChatMessage(messageText) {
  if (!messageText || !messageText.trim()) return;
  if (window.AppState.isSending) return;

  const customerId = window.AppState.currentCustomer ? window.AppState.currentCustomer.id : "cust_rahul";

  // Append user bubble
  appendMessage("user", messageText);
  window.AppState.isSending = true;

  const sendBtn = document.getElementById("send-button");
  if (sendBtn) sendBtn.disabled = true;

  showTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: customerId,
        message: messageText
      })
    });

    removeTypingIndicator();

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: "Network error" }));
      showToast(errData.detail || "Unable to reach MemoryDesk API", "error");
      appendMessage("assistant", "Unable to connect to the memory service. Please check the backend configuration.");
      return;
    }

    const data = await res.json();
    
    // Append assistant bubble with Hindsight metadata & AutoFix script
    appendMessage("assistant", data.response, {
      memories_used: data.memories_used,
      retrieved_memories: data.retrieved_memories,
      memory_updated: data.memory_updated,
      new_memory_stored: data.new_memory_stored,
      auto_fix_script: data.auto_fix_script
    });


    // Update memory indicator notification on right panel
    const retrievalBox = document.getElementById("retrieval-status-box");
    const countText = document.getElementById("retrieval-count-text");
    const detailText = document.getElementById("retrieval-detail-text");
    if (retrievalBox && countText) {
      retrievalBox.style.display = "block";
      countText.innerText = `${data.memories_used} relevant memories retrieved`;
      if (data.memory_updated) {
        detailText.innerText = `✓ New memory retained into bank (${data.new_memory_stored ? data.new_memory_stored.substring(0, 45) + '...' : 'Updated'})`;
      } else {
        detailText.innerText = `Recalled from Hindsight bank in real-time`;
      }
    }

    // Refresh memory inspector panel & timeline
    if (typeof refreshCurrentMemory === "function") {
      refreshCurrentMemory();
    }

  } catch (err) {
    removeTypingIndicator();
    console.error("Chat error:", err);
    showToast("Error connecting to MemoryDesk service.", "error");
    appendMessage("assistant", "I encountered a communication error with the backend. Please ensure the server is running.");
  } finally {
    window.AppState.isSending = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  if (!input) return;
  const text = input.value.trim();
  if (text) {
    input.value = "";
    sendChatMessage(text);
  }
}
