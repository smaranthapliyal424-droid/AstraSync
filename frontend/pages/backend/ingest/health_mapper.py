def map_health_connect_payload(payload):
    return {
        "date": payload["date"],
        "steps": payload.get("steps", 0),
        "sleep_hours": payload.get("sleep_hours"),
        "heart_rate_avg": payload.get("heart_rate_avg"),
        "calories": payload.get("calories"),
        "source": payload.get("source", "health_connect")
    }
