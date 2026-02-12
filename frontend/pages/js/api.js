const API_BASE = window.location.hostname === "localhost"
  ? "http://127.0.0.1:5001"
  : "https://your-production-backend.com";


async function apiPost(path, payload) {
  if (!API_BASE) return null;
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
if (!res.ok) {
  const text = await res.text();
  console.error("API Error:", text);
  return { error: text };
}
  return res.json();
}

async function apiGet(path) {
  if (!API_BASE) return null;
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Mock scoring for demo (replace with /score later)
function mockScore(entry) {
  const reasons = [];
  let score = 0;

  if (entry.bp_sys >= 160 || entry.bp_dia >= 100) { score += 3; reasons.push("BP very high"); }
  else if (entry.bp_sys >= 140 || entry.bp_dia >= 90) { score += 2; reasons.push("BP trending high"); }

  if (entry.spo2_avg && entry.spo2_avg < 90) { score += 3; reasons.push("Low SpO₂ dips"); }
  else if (entry.spo2_avg && entry.spo2_avg < 94) { score += 2; reasons.push("SpO₂ slightly low"); }

  if (entry.sleep_hours < 4) { score += 3; reasons.push("Very low sleep"); }
  else if (entry.sleep_hours < 5) { score += 2; reasons.push("Sleep deficit"); }

  if (entry.steps < 2000) { score += 1; reasons.push("Very low activity"); }
  if (entry.screen_time_min > 360) { score += 1; reasons.push("High screen time"); }
  if (entry.alcohol) { score += 1; reasons.push("Alcohol use logged"); }
  if (entry.smoking) { score += 2; reasons.push("Smoking increases risk"); }

  let risk_color = "Green";
  if (score >= 6) risk_color = "Red";
  else if (score >= 3) risk_color = "Yellow";

  const confidence = Math.min(95, 55 + score * 8);

  const next_steps = [];
  if (risk_color === "Green") {
    next_steps.push("Maintain routine and log daily");
    next_steps.push("Walk 20–30 min today");
    next_steps.push("Sleep target: 7+ hours");
  } else if (risk_color === "Yellow") {
    next_steps.push("Recheck BP twice daily for 3 days");
    next_steps.push("Hydrate and reduce screen time tonight");
    next_steps.push("If symptoms, consult a doctor");
  } else {
    next_steps.push("Consult doctor soon for confirmation");
    next_steps.push("Enter/Upload lab values (eGFR/ACR if available)");
    next_steps.push("Avoid heavy exertion; rest and monitor");
  }

  return {
    risk_color,
    confidence,
    reasons: reasons.slice(0, 3),
    next_steps: next_steps.slice(0, 3),
    organ: {
      heart: (entry.bp_sys >= 140 || entry.resting_hr >= 90) ? "Elevated" : "Normal",
      kidney: "Needs labs (optional)",
      sleep: (entry.sleep_hours < 6 || (entry.spo2_avg && entry.spo2_avg < 94)) ? "At risk" : "Normal"
    }
  };
}
async function scoreEntry(entry){
  // Backend scoring (your real model)
  return await apiPost("/score", entry);
}
async function syncGoogleFit() {
  return await apiGet("/sync/google-fit");
}
