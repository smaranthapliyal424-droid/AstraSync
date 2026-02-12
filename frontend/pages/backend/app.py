import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv



from backend.services.db_service import (
    get_conn,
    init_db,
    save_profile,
    get_profile,
    save_log,
    get_logs
)
from backend.ml.dual_baseline import score_entry


load_dotenv()

app = Flask(__name__)
CORS(app)

conn = get_conn()
init_db(conn)

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/profile")
def set_profile():
    data = request.get_json(force=True)
    user_id = data.get("user_id", "demo_user")
    save_profile(conn, user_id, data)
    return jsonify({"ok": True})

@app.post("/submit_data")
def submit_data():
    entry = request.get_json(force=True)
    user_id = entry.get("user_id", "demo_user")
    date = entry.get("date")
    if not date:
        return jsonify({"ok": False, "error": "date required"}), 400
    save_log(conn, user_id, date, entry)
    return jsonify({"ok": True})

@app.post("/score")
def score():
    entry = request.get_json(force=True)
    user_id = entry.get("user_id", "demo_user")

    profile = get_profile(conn, user_id)
    logs = get_logs(conn, user_id, limit=14)

    result = score_entry(profile, entry, logs)
    return jsonify(result)

@app.get("/history/<user_id>")
def history(user_id):
    logs = get_logs(conn, user_id, limit=60)
    return jsonify({"logs": logs})


# ✅ ADD ROUTE HERE (ABOVE main)
@app.get("/sync/google-fit")
def sync_google_fit():
    entry = {
        "date": "2026-02-12",
        "steps": 8000,
        "heart_rate_avg": 72,
        "toilet_freq": 2,
        "alcohol": 0,
        "smoking": 0
    }
    return jsonify(entry)

import requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Step 1: Redirect to Google login
from urllib.parse import urlencode

@app.get("/auth/google-fit")
def google_fit_auth():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/fitness.activity.read https://www.googleapis.com/auth/fitness.heart_rate.read",
        "access_type": "offline",
        "prompt": "consent"
    }

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return jsonify({"auth_url": auth_url})



# Step 2: Google redirects here with ?code=
@app.get("/auth/google-fit/callback")
def google_fit_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code received"}), 400

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=data)
    token_data = response.json()

    return jsonify(token_data)

# ✅ ONLY ONE main block at bottom
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
