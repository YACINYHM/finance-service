"""Flask server: Telegram webhook -> Gemini parse -> append to Google Sheets Log."""

import datetime
import logging
import os

import requests
from flask import Flask, request, jsonify

from parser import parse_message
from sheets import append_log_row

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _today_str():
    """Return today's date as DD/MM/YYYY (UTC)."""
    return datetime.datetime.utcnow().strftime("%d/%m/%Y")


def _send_message(chat_id, text):
    """Reply to the user via Telegram."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception:
        logger.exception("Failed to send Telegram reply")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    message = data.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = message.get("chat_id")
    msg_date = message.get("date")

    if not text or chat_id is None:
        return jsonify({"ok": True, "reason": "no text"}), 200

    # Date: prefer the Telegram message timestamp, fall back to today.
    if msg_date:
        try:
            date_str = datetime.datetime.utcfromtimestamp(int(msg_date)).strftime("%d/%m/%Y")
        except Exception:
            date_str = _today_str()
    else:
        date_str = _today_str()

    parsed = parse_message(text)
    row = [
        date_str,
        parsed["main_category"],
        parsed["value"],
        parsed["payment_type"],
        parsed["observation"],
    ]

    try:
        append_log_row(row)
        reply = (
            f"Logged: {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}"
        )
    except Exception:
        logger.exception("Failed to append to Log sheet")
        reply = "Sorry, I couldn't save that to the sheet. Please try again."

    if chat_id:
        _send_message(chat_id, reply)

    return jsonify({"ok": True, "row": row}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))