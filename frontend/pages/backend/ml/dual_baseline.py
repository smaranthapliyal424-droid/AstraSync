# backend/ml/dual_baseline.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import math, statistics as stats

IMPORTANT = ["bp_sys","bp_dia","spo2_avg","resting_hr","sleep_hours","steps"]

ALL_METRICS = IMPORTANT + ["water_ml","screen_time_min","toilet_freq","alcohol","smoking"]

# ---------------------------
# Helpers
# ---------------------------
def safe_float(x):
    try:
        if x is None: return None
        if isinstance(x, str) and x.strip() == "": return None
        v = float(x)
        if math.isnan(v): return None
        return v
    except:
        return None

def median(xs: List[float]) -> float:
    return stats.median(xs)

def mad(xs: List[float]) -> float:
    m = median(xs)
    return median([abs(x-m) for x in xs]) if xs else 0.0

def clamp(a, lo, hi):
    return max(lo, min(hi, a))

def bmi(height_cm: float, weight_kg: float) -> float | None:
    if not height_cm or not weight_kg: 
        return None
    h = height_cm / 100.0
    if h <= 0: 
        return None
    return weight_kg / (h*h)

def age_group(age: int) -> str:
    if age < 18: return "teen"
    if age < 30: return "18_29"
    if age < 45: return "30_44"
    if age < 60: return "45_59"
    return "60_plus"

def bmi_band(b: float | None) -> str:
    if b is None: return "unknown"
    if b < 18.5: return "under"
    if b < 25: return "normal"
    if b < 30: return "over"
    return "obese"

# ---------------------------
# Standard reference (Day-1 safety)
# Keep hackathon-safe: screening thresholds, not diagnosis.
# ---------------------------
def standard_thresholds(profile: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Returns thresholds by metric: {metric: {yellow_low/high, red_low/high}}.
    Some metrics are "lower is worse" (SpO2, sleep).
    """
    # Base thresholds (simple MVP)
    base = {
        "bp_sys": {"yellow_high": 140, "red_high": 160},
        "bp_dia": {"yellow_high": 90,  "red_high": 100},
        "spo2_avg": {"yellow_low": 94, "red_low": 90},
        "sleep_hours": {"yellow_low": 5.0, "red_low": 4.0},
        "resting_hr": {"yellow_high": 90, "red_high": 100},
        "steps": {"yellow_low": 3000, "red_low": 1500},
    }

    # Optional: adjust slightly by age / BMI (simple, defensible)
    age = int(profile.get("age") or 0)
    height = safe_float(profile.get("height"))
    weight = safe_float(profile.get("weight"))
    b = bmi(height or 0, weight or 0)

    ag = age_group(age) if age else "unknown"
    bb = bmi_band(b)

    # older age: allow slightly higher resting HR threshold
    if ag in ("45_59","60_plus"):
        base["resting_hr"]["yellow_high"] = 95
        base["resting_hr"]["red_high"] = 105

    # obese band: increase alert sensitivity for BP (slightly)
    if bb == "obese":
        base["bp_sys"]["yellow_high"] = 135
        base["bp_sys"]["red_high"] = 155
        base["bp_dia"]["yellow_high"] = 88
        base["bp_dia"]["red_high"] = 98

    return base

def standard_score(entry: Dict[str, Any], thresh: Dict[str, Dict[str, float]]) -> Tuple[float, List[str], str]:
    """
    Returns (score 0..1, reasons, label_hint)
    """
    score = 0.0
    reasons = []
    worst = "Green"

    def bump(level: str, reason: str, amt: float):
        nonlocal score, worst
        score += amt
        reasons.append(reason)
        if level == "Red":
            worst = "Red"
        elif level == "Yellow" and worst != "Red":
            worst = "Yellow"

    # BP
    bs = safe_float(entry.get("bp_sys"))
    bd = safe_float(entry.get("bp_dia"))
    if bs is not None:
        if bs >= thresh["bp_sys"]["red_high"]:
            bump("Red", "BP systolic very high vs standard", 0.40)
        elif bs >= thresh["bp_sys"]["yellow_high"]:
            bump("Yellow", "BP systolic high vs standard", 0.22)

    if bd is not None:
        if bd >= thresh["bp_dia"]["red_high"]:
            bump("Red", "BP diastolic very high vs standard", 0.35)
        elif bd >= thresh["bp_dia"]["yellow_high"]:
            bump("Yellow", "BP diastolic high vs standard", 0.20)

    # SpO2 (lower is worse)
    sp = safe_float(entry.get("spo2_avg"))
    if sp is not None:
        if sp < thresh["spo2_avg"]["red_low"]:
            bump("Red", "SpO₂ low vs standard", 0.45)
        elif sp < thresh["spo2_avg"]["yellow_low"]:
            bump("Yellow", "SpO₂ slightly low vs standard", 0.25)

    # Sleep (lower is worse)
    sh = safe_float(entry.get("sleep_hours"))
    if sh is not None:
        if sh < thresh["sleep_hours"]["red_low"]:
            bump("Red", "Severe sleep deficit vs standard", 0.30)
        elif sh < thresh["sleep_hours"]["yellow_low"]:
            bump("Yellow", "Sleep deficit vs standard", 0.18)

    # Resting HR
    rhr = safe_float(entry.get("resting_hr"))
    if rhr is not None:
        if rhr >= thresh["resting_hr"]["red_high"]:
            bump("Red", "Resting HR very high vs standard", 0.30)
        elif rhr >= thresh["resting_hr"]["yellow_high"]:
            bump("Yellow", "Resting HR high vs standard", 0.16)

    # Steps (lower is worse)
    st = safe_float(entry.get("steps"))
    if st is not None:
        if st < thresh["steps"]["red_low"]:
            bump("Yellow", "Very low activity today", 0.10)
        elif st < thresh["steps"]["yellow_low"]:
            bump("Yellow", "Low activity today", 0.07)

    # Lifestyle bumps
    if int(entry.get("smoking") or 0) == 1:
        bump("Yellow", "Smoking logged (risk factor)", 0.10)
    if int(entry.get("alcohol") or 0) == 1:
        bump("Yellow", "Alcohol logged (risk factor)", 0.06)

    return clamp(score, 0.0, 1.0), reasons[:3], worst

# ---------------------------
# Personal baseline (7–14 days)
# ---------------------------
def compute_personal_baseline(logs: List[Dict[str, Any]], window: int = 14) -> Dict[str, Dict[str, float]]:
    recent = logs[:window]
    base = {}
    for k in ALL_METRICS:
        xs = []
        for row in recent:
            v = safe_float(row.get(k))
            if v is not None:
                xs.append(v)
        if len(xs) < 4:
            continue
        med = median(xs)
        spread = mad(xs)
        if spread < 1e-6:
            spread = max(1.0, 0.05*abs(med) if med else 1.0)
        low = med - 2.2*spread
        high = med + 2.2*spread
        base[k] = {"median": med, "mad": spread, "low": low, "high": high}
    return base

def personal_score(entry: Dict[str, Any], base: Dict[str, Dict[str, float]]) -> Tuple[float, List[str]]:
    reasons = []
    total = 0.0
    for k, b in base.items():
        v = safe_float(entry.get(k))
        if v is None:
            continue
        z = abs(v - b["median"]) / (b["mad"] + 1e-6)
        is_out = (v < b["low"] or v > b["high"] or z > 1.5)
        if is_out:
            s = min(1.0, z/3.0)
            total += s
            delta = v - b["median"]
            sign = "+" if delta >= 0 else ""
            reasons.append((s, f"{k} {sign}{delta:.1f} vs your baseline"))
    reasons.sort(reverse=True, key=lambda x: x[0])
    score = clamp(total/3.0, 0.0, 1.0)
    return score, [r for _, r in reasons[:3]]

# ---------------------------
# Missing-data completeness + confidence
# ---------------------------
def completeness(entry: Dict[str, Any]) -> Tuple[float, List[str]]:
    missing = []
    available = 0
    for k in IMPORTANT:
        v = safe_float(entry.get(k))
        if v is None:
            missing.append(k)
        else:
            available += 1
    comp = available / len(IMPORTANT)
    return comp, missing

# ---------------------------
# Fusion: Standard + Personal
# ---------------------------
def fuse_risk(
    std_score: float, std_label_hint: str,
    per_score: float, comp: float, days_of_history: int
) -> Tuple[str, int]:
    """
    Returns (risk_color, confidence)
    """
    # Weighting based on history length (cold start vs personalized)
    if days_of_history < 7:
        w_std, w_per = 0.65, 0.35
    else:
        w_std, w_per = 0.40, 0.60

    final = w_std*std_score + w_per*per_score

    risk = "Green"
    if final >= 0.35: risk = "Yellow"
    if final >= 0.65 or std_label_hint == "Red": risk = "Red"

    # Confidence depends on completeness and history depth
    hist_factor = 0.55 if days_of_history < 7 else 0.75
    conf = int(100 * (0.25 + 0.45*comp + 0.30*hist_factor))
    conf = clamp(conf, 35, 92)
    return risk, int(conf)

def score_entry(
    profile: Dict[str, Any],
    entry: Dict[str, Any],
    logs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Main function to call from /score endpoint.
    logs should be latest-first list of dicts.
    """
    days = len(logs)

    comp, missing = completeness(entry)

    # Standard
    th = standard_thresholds(profile)
    std_s, std_reasons, std_hint = standard_score(entry, th)

    # Personal baseline
    per_base = compute_personal_baseline(logs, window=14) if days >= 4 else {}
    per_s, per_reasons = personal_score(entry, per_base) if per_base else (0.0, [])

    # Fuse
    risk, conf = fuse_risk(std_s, std_hint, per_s, comp, days)

    # Merge reasons: prioritize Red/Yellow standard reasons + personal drift
    reasons = (std_reasons + per_reasons)[:3]
    if not reasons:
        reasons = ["Not enough data: add BP/SpO₂/Sleep for higher accuracy"]

    # Next steps always include missing-input suggestion
    next_steps = []
    if missing:
        next_steps.append(f"Add {', '.join(missing[:2])} to improve accuracy")

    if risk == "Green":
        next_steps += ["Maintain routine and log daily", "Walk 20–30 min", "Sleep 7+ hours"]
    elif risk == "Yellow":
        next_steps += ["Recheck BP / SpO₂ and log again", "Hydrate + reduce screen time", "Upload lab report if available"]
    else:
        next_steps += ["Consult a doctor soon for confirmation", "Enter/Upload confirm tests (BP/Labs)", "Rest and monitor symptoms"]

    return {
        "risk_color": risk,
        "confidence": conf,
        "reasons": reasons,
        "missing_inputs": missing[:4],
        "completeness": round(comp, 2),
        "standard_score": round(std_s, 2),
        "personal_score": round(per_s, 2),
        "history_days_used": days
    }
