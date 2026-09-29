// MemoryDesk AI - Core App & Utility Module

const API_BASE = "";

// Global App State
window.AppState = {
  currentCustomer: null,
  customers: [],
  hindsightConnected: false,
  hindsightStatusText: "Hindsight: Active",
  isSending: false
};

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal Handlers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = "flex";
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = "none";
}

// Close modals when clicking outside
window.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.style.display = "none";
  }
});

// Periodic Health Check & Hindsight Status Polling
async function pollHealthStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) return;
    const data = await res.json();
    
    window.AppState.hindsightConnected = data.hindsight_connected;
    
    const badgeText = document.getElementById("hindsight-badge-text");
    const serverDetail = document.getElementById("hindsight-server-detail");
    const livePillText = document.getElementById("hindsight-pill-text");
    
    if (data.hindsight_connected) {
      if (badgeText) badgeText.innerText = "Hindsight: Live Server";
      if (serverDetail) serverDetail.innerText = `Connected (${data.hindsight_url})`;
      if (livePillText) livePillText.innerText = "● HINDSIGHT LIVE: ACTIVE";
    } else {
      if (badgeText) badgeText.innerText = "Hindsight: Local Engine";
      if (serverDetail) serverDetail.innerText = "Persistent Bank Synced";
      if (livePillText) livePillText.innerText = "● HINDSIGHT MEMORY: ACTIVE";
    }
  } catch (err) {
    console.debug("Health check error:", err);
  }
}

// Switch Sidebar Active Link
function switchNav(route) {
  document.querySelectorAll(".sidebar-item").forEach(el => el.classList.remove("active"));
  const activeEl = document.getElementById(`nav-${route}`);
  if (activeEl) activeEl.classList.add("active");
}

function focusMemoryPanel() {
  const inspector = document.querySelector(".dashboard-inspector");
  if (inspector) {
    inspector.style.boxShadow = "inset 0 0 0 2px var(--primary)";
    setTimeout(() => { inspector.style.boxShadow = "none"; }, 1000);
  }
}

function openBeforeAfterModal() {
  openModal("modal-before-after");
}

function openDemoStoryModal() {
  openModal("modal-demo-story");
}

function openCustomerModal() {
  openModal("modal-new-customer");
}

function openNewCustomerModal() {
  openModal("modal-new-customer");
}

// Initial health check on page load
document.addEventListener("DOMContentLoaded", () => {
  pollHealthStatus();
  setInterval(pollHealthStatus, 15000);
});
