"""METAR Reader: fetch a METAR for an airport and show it in plain English.

Local-only, single-user tool. No authentication or secrets are required:
the app only calls the public, unauthenticated aviationweather.gov API and
handles no sensitive data.
"""
import logging
import re

import requests
from flask import Flask, render_template, request

from metar_decoder import decode_metar

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metar_reader")

METAR_API_URL = "https://aviationweather.gov/api/data/metar"
# ICAO airport codes are 4 alphanumeric characters (e.g. KJFK, EGLL).
AIRPORT_CODE_PATTERN = re.compile(r"^[A-Z0-9]{3,4}$")
REQUEST_TIMEOUT_SECONDS = 5


def fetch_metar(airport_code: str) -> str:
    """Fetch the raw METAR text for a validated airport code, or None."""
    response = requests.get(
        METAR_API_URL,
        params={"ids": airport_code, "format": "raw"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    raw_text = response.text.strip()
    return raw_text or None


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=None, error=None, airport_code="")


@app.route("/metar", methods=["GET"])
def metar():
    airport_code = request.args.get("airport_code", "").strip().upper()

    if not AIRPORT_CODE_PATTERN.match(airport_code):
        return render_template(
            "index.html",
            result=None,
            error="Enter a valid 3-4 character airport code (letters and numbers only).",
            airport_code=airport_code,
        )

    try:
        raw_metar = fetch_metar(airport_code)
    except requests.RequestException:
        logger.warning("Failed to fetch METAR for airport_code=%s", airport_code)
        return render_template(
            "index.html",
            result=None,
            error="Could not reach the weather service. Please try again shortly.",
            airport_code=airport_code,
        )

    if raw_metar is None:
        return render_template(
            "index.html",
            result=None,
            error="No weather data found for that airport code.",
            airport_code=airport_code,
        )

    decoded = decode_metar(raw_metar)
    return render_template(
        "index.html",
        result={"raw": raw_metar, "decoded": decoded},
        error=None,
        airport_code=airport_code,
    )


if __name__ == "__main__":
    # debug=False by default: never expose stack traces in this app.
    app.run(host="127.0.0.1", port=5000)
