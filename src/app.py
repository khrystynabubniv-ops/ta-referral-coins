import json
import logging

from flask import Flask, jsonify, request

from . import config, inbox, security, worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.post("/webhooks/ashby")
def ashby_webhook():
    raw_body = request.get_data()
    signature = request.headers.get(security.SIGNATURE_HEADER, "")

    if not security.verify_signature(raw_body, signature, config.ASHBY_WEBHOOK_SECRET):
        logger.warning("rejected Ashby webhook: invalid signature")
        return jsonify({"error": "invalid signature"}), 401

    try:
        payload = json.loads(raw_body)
    except ValueError:
        return jsonify({"error": "invalid JSON"}), 400

    row_id = inbox.enqueue(payload)
    logger.info("queued Ashby webhook event as coin_inbox row %s", row_id)
    return jsonify({"status": "queued", "id": row_id}), 202


def _start_worker_once() -> None:
    if not getattr(app, "_worker_started", False):
        worker.start()
        app._worker_started = True


_start_worker_once()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
