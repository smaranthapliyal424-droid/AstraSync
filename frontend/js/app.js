if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("../public/sw.js");
  });
}

// Register PWA service worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/frontend/sw.js").catch(console.error);
}

function getProfile() {
  return JSON.parse(localStorage.getItem("astrasync_profile") || "{}");
}
function setProfile(p) {
  localStorage.setItem("astrasync_profile", JSON.stringify(p));
}
function getLogs() {
  return JSON.parse(localStorage.getItem("astrasync_logs") || "[]");
}
function setLogs(logs) {
  localStorage.setItem("astrasync_logs", JSON.stringify(logs));
}
function addLog(entry) {
  const logs = getLogs();
  logs.unshift(entry);
  setLogs(logs.slice(0, 60));
}

function todayISO() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

async function enableAlerts() {
  if (!("Notification" in window)) {
    alert("Notifications not supported in this browser.");
    return;
  }
  const perm = await Notification.requestPermission();
  if (perm === "granted") {
    new Notification("AstraSync Alerts Enabled", { body: "You will receive risk notifications." });
  } else {
    alert("Notification permission denied.");
  }
}

// Helper: set active nav
function setActiveNav(href) {
  document.querySelectorAll(".navIcon, .bottomNav a").forEach(a => {
    const isActive = a.getAttribute("href")?.includes(href);
    if (isActive) a.classList.add("active"); else a.classList.remove("active");
  });
}

