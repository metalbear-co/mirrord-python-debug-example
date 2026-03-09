import os
from datetime import datetime

import redis
from flask import Flask, redirect, render_template, request, url_for


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_KEY = os.getenv("REDIS_KEY", "knote:entries")

app = Flask(__name__)
redis_client = None


def init_clients() -> None:
    """Fail fast if Redis is not reachable."""
    global redis_client
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=3,
    )
    redis_client.ping()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}, 200


@app.get("/readyz")
def readyz():
    try:
        redis_client.ping()
        return {"status": "ready"}, 200
    except Exception:
        return {"status": "not-ready"}, 503


@app.get("/")
def index():
    raw = redis_client.lrange(REDIS_KEY, 0, -1)
    entries = []
    for row in raw:
        parts = row.split("|", 2)
        if len(parts) == 3:
            ts, name, message = parts
        else:
            # Backward compatibility for any older value format.
            ts, message = row.split("|", 1)
            name = "Anonymous"
        entries.append({"created_at": ts, "name": name, "message": message})
    entries.reverse()
    return render_template("index.html", entries=entries)


@app.post("/note")
def create_note():
    name = request.form.get("name", "").strip() or "Anonymous"
    message = request.form.get("message", "").strip()
    if message:
        ts = datetime.utcnow().isoformat()
        redis_client.rpush(REDIS_KEY, f"{ts}|{name}|{message}")
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_clients()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)
