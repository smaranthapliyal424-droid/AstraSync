def build_features(profile, entry, history):
    return {
        "steps_z": entry["steps"] / (profile["avg_steps"] + 1),
        "sleep_delta": entry["sleep_hours"] - profile["avg_sleep"],
        "hr_deviation": entry["heart_rate_avg"] - profile["resting_hr"],
        "trend_steps_7d": sum(h["steps"] for h in history[-7:]) / 7
    }

