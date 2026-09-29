// MemoryDesk AI - Dashboard Controller Module

// Load all customers on start
async function loadCustomers() {
  try {
    const res = await fetch(`${API_BASE}/api/customers`);
    if (!res.ok) return;
    const customers = await res.json();
    window.AppState.customers = customers;

    const select = document.getElementById("customer-select");
    if (!select) return;
    select.innerHTML = "";

    customers.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.innerText = `${c.name} (${c.company || 'Personal'})`;
      select.appendChild(opt);
    });

    if (customers.length > 0) {
      onCustomerChange(customers[0].id);
    }
  } catch (err) {
    console.error("Error loading customers:", err);
  }
}

// When active customer changes
async function onCustomerChange(customerId) {
  const customer = window.AppState.customers.find(c => c.id === customerId);
  if (!customer) return;

  window.AppState.currentCustomer = customer;
  updateCustomerUI(customer);
  
  // Clear chat stream and load history
  const chatStream = document.getElementById("chat-stream");
  if (chatStream) chatStream.innerHTML = "";

  // Load existing conversations
  await loadConversations(customerId);

  // Load Hindsight memory and timeline
  await refreshCurrentMemory();
}

function updateCustomerUI(customer) {
  const avatarLetter = document.getElementById("cust-avatar-letter");
  const nameDisplay = document.getElementById("cust-name-display");
  const companyDisplay = document.getElementById("cust-company-display");
  const idDisplay = document.getElementById("cust-id-display");
  const osBadge = document.getElementById("cust-os-badge");
  const envBadge = document.getElementById("cust-env-badge");
  const convBadge = document.getElementById("cust-conversations-badge");

  if (avatarLetter) avatarLetter.innerText = customer.name.charAt(0);
  if (nameDisplay) nameDisplay.innerText = customer.name;
  if (companyDisplay) companyDisplay.innerText = customer.company || "Independent";
  if (idDisplay) idDisplay.innerText = customer.id;
  if (osBadge) osBadge.innerText = customer.os || "Windows 11";
  if (envBadge) envBadge.innerText = customer.environment || "Python 3.12";
  if (convBadge) convBadge.innerText = `${customer.conversations_count || 0} Conversations`;
}

// Fetch and render conversation history
async function loadConversations(customerId) {
  try {
    const res = await fetch(`${API_BASE}/api/customers/${customerId}/conversations`);
    if (!res.ok) return;
    const data = await res.json();
    
    if (data.conversations && data.conversations.length > 0) {
      data.conversations.forEach(msg => {
        appendMessage(msg.role, msg.content, {
          memories_used: msg.memories_used || 0
        });
      });
    } else {
      // Friendly initial greeting
      const cust = window.AppState.currentCustomer;
      const firstName = cust ? cust.name.split(" ")[0] : "there";
      appendMessage("assistant", `Hello ${firstName}! I am MemoryDesk AI. I have synchronized your persistent profile from Hindsight. How can I help you troubleshoot today?`);
    }
  } catch (err) {
    console.error("Error loading conversations:", err);
  }
}

// Fetch and render Hindsight Memory & Timeline
async function refreshCurrentMemory() {
  if (!window.AppState.currentCustomer) return;
  const customerId = window.AppState.currentCustomer.id;

  try {
    const res = await fetch(`${API_BASE}/api/customers/${customerId}/memory`);
    if (!res.ok) return;
    const data = await res.json();
    window.AppState.currentMemoryData = data;

    // 1. Structured Entity Profile
    const prof = data.structured_profile;
    const profName = document.getElementById("profile-name");
    const profOs = document.getElementById("profile-os");
    const profEnv = document.getElementById("profile-env");
    const profIssue = document.getElementById("profile-issue");
    const profPref = document.getElementById("profile-preference");

    if (profName) profName.innerText = prof.name || window.AppState.currentCustomer.name;
    if (profOs) profOs.innerText = prof.os || window.AppState.currentCustomer.os;
    if (profEnv) profEnv.innerText = prof.environment || window.AppState.currentCustomer.environment;
    if (profIssue) profIssue.innerText = prof.previous_issue || window.AppState.currentCustomer.last_issue || "None recorded yet";
    if (profPref) profPref.innerText = prof.preference || window.AppState.currentCustomer.preference;

    // 2. Timeline with active filter
    renderFilteredTimeline(window.AppState.activeMemoryFilter || 'all');

  } catch (err) {
    console.error("Error refreshing memory:", err);
  }
}

function filterMemoryView(category) {
  window.AppState.activeMemoryFilter = category;
  
  // Update button active state
  document.querySelectorAll(".filter-tab").forEach(tab => tab.classList.remove("active"));
  const tabMap = {
    'all': 'tab-all',
    'world_fact': 'tab-world',
    'experience': 'tab-exp',
    'observation': 'tab-obs'
  };
  const activeTab = document.getElementById(tabMap[category]);
  if (activeTab) activeTab.classList.add("active");

  renderFilteredTimeline(category);
}

function renderFilteredTimeline(category) {
  const data = window.AppState.currentMemoryData;
  if (!data) return;

  const totalCountEl = document.getElementById("memory-total-count");
  const timelineContainer = document.getElementById("timeline-list");
  if (!timelineContainer) return;

  let itemsToRender = [];
  if (category === 'all') {
    itemsToRender = data.memories || [];
  } else if (data.categorized_memories && data.categorized_memories[category + 's']) {
    itemsToRender = data.categorized_memories[category + 's'];
  } else {
    itemsToRender = (data.memories || []).filter(m => m.type === category);
  }

  if (totalCountEl) totalCountEl.innerText = `${itemsToRender.length} of ${data.total_memories} units`;

  timelineContainer.innerHTML = "";
  if (itemsToRender.length > 0) {
    itemsToRender.forEach((m, idx) => {
      const stepEl = document.createElement("div");
      stepEl.className = "timeline-step";
      
      let badgeLabel = "Memory Unit";
      if (m.type === "world_fact") badgeLabel = "🌍 World Fact";
      else if (m.type === "experience") badgeLabel = "📜 Experience";
      else if (m.type === "observation") badgeLabel = "💡 Observation";

      stepEl.innerHTML = `
        <div class="timeline-badge">${badgeLabel} #${idx + 1}</div>
        <div class="timeline-text">${m.text}</div>
      `;
      timelineContainer.appendChild(stepEl);
    });
  } else {
    timelineContainer.innerHTML = `<div style="font-size: 0.8rem; color: #94a3b8; padding: 0.5rem 0;">No ${category.replace('_', ' ')} memories recorded in this bank.</div>`;
  }
}


// Search Memory Bank
async function executeMemorySearch() {
  if (!window.AppState.currentCustomer) return;
  const queryInput = document.getElementById("memory-search-input");
  const resultsContainer = document.getElementById("memory-search-results");
  if (!queryInput || !resultsContainer) return;

  const query = queryInput.value.trim();
  if (!query) {
    resultsContainer.innerHTML = "";
    return;
  }

  resultsContainer.innerHTML = `<span style="font-size: 0.75rem; color: #64748b;">Searching bank...</span>`;

  try {
    const res = await fetch(`${API_BASE}/api/memory/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: window.AppState.currentCustomer.id,
        query: query,
        limit: 4
      })
    });

    if (!res.ok) {
      resultsContainer.innerHTML = `<span style="font-size: 0.75rem; color: #ef4444;">Search failed</span>`;
      return;
    }

    const data = await res.json();
    resultsContainer.innerHTML = "";

    if (data.results && data.results.length > 0) {
      data.results.forEach(item => {
        const itemEl = document.createElement("div");
        itemEl.style.fontSize = "0.78rem";
        itemEl.style.padding = "0.4rem 0.6rem";
        itemEl.style.background = "#ffffff";
        itemEl.style.border = "1px solid #c7d2fe";
        itemEl.style.borderRadius = "4px";
        itemEl.innerHTML = `<strong style="color: #4f46e5;">[Score: ${item.relevance_score || 0.85}]</strong> ${item.text}`;
        resultsContainer.appendChild(itemEl);
      });
    } else {
      resultsContainer.innerHTML = `<span style="font-size: 0.75rem; color: #94a3b8;">No matching memories found for "${query}"</span>`;
    }
  } catch (err) {
    console.error("Search error:", err);
    resultsContainer.innerHTML = `<span style="font-size: 0.75rem; color: #ef4444;">Search request error</span>`;
  }
}

// Create New Customer Bank
async function handleCreateCustomer(e) {
  e.preventDefault();
  const name = document.getElementById("new-cust-name").value.trim();
  const company = document.getElementById("new-cust-company").value.trim();
  const os = document.getElementById("new-cust-os").value.trim();
  const env = document.getElementById("new-cust-env").value.trim();
  const pref = document.getElementById("new-cust-pref").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/customers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        email: `${name.toLowerCase().replace(/\s+/g, '')}@example.com`,
        company: company,
        title: "Developer",
        os: os,
        environment: env,
        preference: pref
      })
    });

    if (!res.ok) {
      showToast("Error creating customer", "error");
      return;
    }

    const newCust = await res.json();
    closeModal("modal-new-customer");
    showToast(`Registered customer bank for ${newCust.name}!`, "success");
    await loadCustomers();
    
    // Select newly created customer
    const select = document.getElementById("customer-select");
    if (select) {
      select.value = newCust.id;
      onCustomerChange(newCust.id);
    }
  } catch (err) {
    console.error("Error creating customer:", err);
    showToast("Error creating customer", "error");
  }
}

// -------------------------------------------------------------
// Interactive 60-Second Demo Story Stepper
// -------------------------------------------------------------
const DEMO_STEPS = {
  1: "My name is Rahul. I use Windows 11 and Python 3.12. I am developing a Django application.",
  2: "My Django application is giving me a database connection error on port 5432.",
  3: "The same database problem happened again."
};

function runDemoStep(stepNum) {
  const prompt = DEMO_STEPS[stepNum];
  if (!prompt) return;

  // Make sure Rahul is active
  const select = document.getElementById("customer-select");
  if (select && select.value !== "cust_rahul") {
    select.value = "cust_rahul";
    onCustomerChange("cust_rahul");
  }

  closeModal("modal-demo-story");
  fillPrompt(prompt);
  setTimeout(() => {
    sendChatMessage(prompt);
    showToast(`Triggered Demo Step ${stepNum}`, "info");
  }, 300);
}

async function runFullDemoStory() {
  closeModal("modal-demo-story");
  showToast("Starting automated 60-second Hackathon Demo...", "info");

  // Switch to Rahul
  const select = document.getElementById("customer-select");
  if (select && select.value !== "cust_rahul") {
    select.value = "cust_rahul";
    await onCustomerChange("cust_rahul");
  }

  // Step 1
  fillPrompt(DEMO_STEPS[1]);
  await new Promise(r => setTimeout(r, 600));
  sendChatMessage(DEMO_STEPS[1]);

  // Step 2
  await new Promise(r => setTimeout(r, 4500));
  fillPrompt(DEMO_STEPS[2]);
  await new Promise(r => setTimeout(r, 600));
  sendChatMessage(DEMO_STEPS[2]);

  // Step 3 (The Proof)
  await new Promise(r => setTimeout(r, 5000));
  fillPrompt(DEMO_STEPS[3]);
  await new Promise(r => setTimeout(r, 600));
  sendChatMessage(DEMO_STEPS[3]);
  showToast("Demonstration complete: Notice persistent recall in response!", "success");
}

// -------------------------------------------------------------
// Advanced Features: Hindsight Reflection & Tenant Isolation
// -------------------------------------------------------------
async function openReflectionModal() {
  if (!window.AppState.currentCustomer) return;
  const customerId = window.AppState.currentCustomer.id;

  openModal("modal-reflection");
  const loading = document.getElementById("reflection-loading");
  const content = document.getElementById("reflection-content");
  if (loading) loading.style.display = "block";
  if (content) content.style.display = "none";

  try {
    const res = await fetch(`${API_BASE}/api/customers/${customerId}/reflect`, { method: "POST" });
    if (!res.ok) throw new Error("Reflection failed");
    const data = await res.json();

    const modelEl = document.getElementById("reflection-mental-model");
    const patternEl = document.getElementById("reflection-recurring-pattern");
    const adviceEl = document.getElementById("reflection-proactive-advice");
    const scoreBadge = document.getElementById("disposition-score-badge");
    const barEl = document.getElementById("disposition-bar");
    const countEl = document.getElementById("facts-analyzed-count");

    if (modelEl) modelEl.innerText = data.mental_model;
    if (patternEl) patternEl.innerText = data.recurring_pattern;
    if (adviceEl) adviceEl.innerText = data.proactive_recommendation;

    const scorePct = Math.round((data.disposition_score || 0.85) * 100);
    if (scoreBadge) scoreBadge.innerText = `${scorePct}% Disposition Stability`;
    if (barEl) barEl.style.width = `${scorePct}%`;
    if (countEl) countEl.innerText = `Synthesized across ${data.facts_analyzed || 8} persistent memory units`;

  } catch (err) {
    console.error("Reflection error:", err);
    showToast("Error executing Hindsight reflection", "error");
  } finally {
    if (loading) loading.style.display = "none";
    if (content) content.style.display = "flex";
  }
}

function openIsolationModal() {
  openModal("modal-isolation");
  runIsolationTest();
}

async function runIsolationTest() {
  const queryInput = document.getElementById("isolation-query-input");
  const grid = document.getElementById("isolation-results-grid");
  const verdictBox = document.getElementById("isolation-verdict-box");
  const verdictText = document.getElementById("isolation-verdict-text");
  if (!grid) return;

  const query = queryInput ? queryInput.value.trim() : "database connection issue";
  grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: #64748b; padding: 1rem;">Executing cross-bank isolation query...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/memory/isolation-test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, customer_ids: ["cust_rahul", "cust_priya", "cust_arjun"] })
    });
    if (!res.ok) throw new Error("Isolation test failed");
    const data = await res.json();

    grid.innerHTML = "";
    const customerNames = {
      "cust_rahul": "Rahul Sharma (Win 11)",
      "cust_priya": "Priya Reddy (macOS M3)",
      "cust_arjun": "Arjun Kumar (Ubuntu)"
    };

    for (const [cid, info] of Object.entries(data.results_by_customer)) {
      const col = document.createElement("div");
      col.style.background = "#ffffff";
      col.style.border = "1px solid var(--border)";
      col.style.borderRadius = "8px";
      col.style.padding = "0.85rem";
      col.style.fontSize = "0.8rem";

      const recalledItems = info.recalled_texts.length > 0
        ? info.recalled_texts.map(t => `<div style="margin-top: 0.35rem; padding: 0.35rem 0.5rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 0.75rem;">${t}</div>`).join("")
        : `<div style="margin-top: 0.35rem; color: #94a3b8; font-style: italic;">No matching memories (Bank Isolated)</div>`;

      col.innerHTML = `
        <div style="font-weight: 700; color: var(--text-main);">${customerNames[cid] || cid}</div>
        <div style="font-size: 0.72rem; color: #047857; font-weight: 600; margin-top: 0.15rem;">${info.memories_count} facts retrieved</div>
        ${recalledItems}
      `;
      grid.appendChild(col);
    }

    if (verdictBox && verdictText) {
      verdictBox.style.display = "block";
      verdictText.innerText = data.security_verdict;
    }

  } catch (err) {
    console.error("Isolation test error:", err);
    grid.innerHTML = `<div style="grid-column: 1 / -1; color: #ef4444;">Error executing isolation test.</div>`;
  }
}

// Startup
document.addEventListener("DOMContentLoaded", () => {
  loadCustomers();
});

