"""Parse a natural-language finance message into structured fields using Gemini."""

import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"

SYSTEM_PROMPT = """You are a finance transaction parser. Convert the user's message into a JSON object with exactly these fields:

{
  "main_category": "Income" or "Outcome",
  "value": the amount as a string of digits only, no currency symbols or commas, e.g. "1000",
  "payment_type": see rules below,
  "observation": a short 2-3 word description, e.g. "Internet Bill"
}

Rules:
- main_category is "Income" if the person RECEIVED money (salary, pay, refund, deposit, cash in, got paid).
- main_category is "Outcome" if the person PAID or SPENT money (bought, paid a bill, sent money, charged).
- payment_type for Income: one of "Salary", "Others", "Debts".
- payment_type for Outcome: one of "Monthly Bills", "Purchases", "Debts".
- Choose the payment_type that best fits the description. If unsure, use "Others" (Income) or "Purchases" (Outcome).
- If the amount is missing or unclear, use "0" and mention it in observation.
- Output ONLY valid JSON. No markdown fences, no extra text.
"""

_VALID = {
    "Income": {"Salary", "Others", "Debts"},
    "Outcome": {"Monthly Bills", "Purchases", "Debts"},
}


def _extract_json(text):
    """Pull a JSON object out of the model output, tolerating markdown fences."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _fallback_parse(text):
    """Regex-based parser used when the Gemini call fails."""
    lower = text.lower()

    income_kw = ["received", "got paid", "salary", "paycheck", "deposit",
                 "refund", "income", "earned", "cash in", "got money"]
    outcome_kw = ["paid", "spent", "bought", "purchase", "bill", "sent",
                  "transferred", "withdrawn", "charged", "paid the"]

    is_income = any(k in lower for k in income_kw)
    is_outcome = any(k in lower for k in outcome_kw)

    if is_income and not is_outcome:
        main_category = "Income"
    elif is_outcome:
        main_category = "Outcome"
    else:
        main_category = "Outcome"

    m = re.search(r"(\d+(?:[.,]\d+)?)", text)
    value = m.group(1).replace(",", "") if m else "0"

    obs = re.sub(r"[^A-Za-z0-9 ]", " ", text)
    obs = " ".join(obs.split())[:30] or "Transaction"

    if main_category == "Income":
        payment_type = "Salary" if "salary" in lower else "Others"
    else:
        bill_words = ["bill", "internet", "electric", "power", "water",
                      "rent", "phone", "mobile", "gas", "wifi", "net"]
        payment_type = "Monthly Bills" if any(w in lower for w in bill_words) else "Purchases"

    return {
        "main_category": main_category,
        "value": value,
        "payment_type": payment_type,
        "observation": obs,
    }


def parse_message(text, api_key=None):
    """Return dict with main_category, value, payment_type, observation."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generation_config": {
            "response_mime_type": "application/json",
            "temperature": 0,
        },
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _extract_json(out)
        if parsed and all(k in parsed for k in ("main_category", "value", "payment_type", "observation")):
            parsed["main_category"] = parsed.get("main_category") or "Outcome"
            if parsed["main_category"] not in _VALID:
                parsed["main_category"] = "Outcome"
            allowed = _VALID[parsed["main_category"]]
            if parsed["payment_type"] not in allowed:
                parsed["payment_type"] = "Others" if parsed["main_category"] == "Income" else "Purchases"
            parsed["value"] = str(parsed.get("value") or "0")
            return parsed
    except Exception as e:
        logger.warning("Gemini request failed (%s), using fallback parser", e)

    fb = _fallback_parse(text)
    fb["observation"] = "(fallback) " + fb["observation"]
    return fb