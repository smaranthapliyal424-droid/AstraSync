import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from services.db_service import get_conn, init_db, save_profile, get_profile, save_log, get_logs
from ml.dual_baseline import score_entry

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
