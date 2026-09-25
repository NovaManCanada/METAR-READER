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

# Public, unauthenticated aviationweather.gov API (see https://aviationweather.gov/data/api/).
METAR_API_URL = "https://aviationweather.gov/api/data/metar"
AIRPORT_API_URL = "https://aviationweather.gov/api/data/airport"
# ICAO/IATA airport codes are 3-4 alphanumeric characters (e.g. KJFK, EGLL).
AIRPORT_CODE_PATTERN = re.compile(r"^[A-Z0-9]{3,4}$")
REQUEST_TIMEOUT_SECONDS = 5


def is_real_airport(airport_code: str) -> bool:
    """Check whether airport_code refers to a real, known airport.

    Args:
        airport_code: A 3-4 character ICAO/IATA airport code, already
            validated against ``AIRPORT_CODE_PATTERN``.

    Returns:
        True if the airport lookup API recognizes the code, False otherwise.

    Raises:
        requests.RequestException: If the request to the weather API
            fails (network error, timeout, or non-2xx response).
    """
    response = requests.get(
        AIRPORT_API_URL,
        params={"ids": airport_code, "format": "json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    # Unknown airport codes return a 200/204 with an empty body rather
    # than an empty JSON array, so guard against that before parsing.
    if not response.text.strip():
        return False
    return bool(response.json())


def fetch_metar(airport_code: str) -> str:
    """Fetch the raw METAR text for a validated airport code.

    Args:
        airport_code: A 3-4 character ICAO/IATA airport code, already
            validated against ``AIRPORT_CODE_PATTERN``.

    Returns:
        The raw METAR report text, or None if the API returned no data
        for the given airport code.

    Raises:
        requests.RequestException: If the request to the weather API
            fails (network error, timeout, or non-2xx response).
    """
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
    """Render the empty input form."""
    return render_template("index.html", error=None, airport_code="")


@app.route("/metar", methods=["GET"])
def metar():
    """Look up and decode the METAR for the requested airport code.

    Reads ``airport_code`` from the query string, validates it, and
    either re-renders the input form with an error message, or renders
    a separate result page with the decoded METAR and the raw text.
    """
    airport_code = request.args.get("airport_code", "").strip().upper()

    if not AIRPORT_CODE_PATTERN.match(airport_code):
        return render_template(
            "index.html",
            error="Enter a valid 3-4 character airport code (letters and numbers only).",
            airport_code=airport_code,
        )

    try:
        airport_exists = is_real_airport(airport_code)
    except requests.RequestException:
        logger.warning("Failed to verify airport_code=%s", airport_code)
        return render_template(
            "index.html",
            error="Could not reach the weather service. Please try again shortly.",
            airport_code=airport_code,
        )

    if not airport_exists:
        return render_template(
            "index.html",
            error=f"'{airport_code}' is not a recognized airport code.",
            airport_code=airport_code,
        )

    try:
        raw_metar = fetch_metar(airport_code)
    except requests.RequestException:
        logger.warning("Failed to fetch METAR for airport_code=%s", airport_code)
        return render_template(
            "index.html",
            error="Could not reach the weather service. Please try again shortly.",
            airport_code=airport_code,
        )

    if raw_metar is None:
        return render_template(
            "index.html",
            error="No weather data found for that airport code.",
            airport_code=airport_code,
        )

    decoded = decode_metar(raw_metar)
    return render_template("result.html", result={"raw": raw_metar, "decoded": decoded})


if __name__ == "__main__":
    # debug=False by default: never expose stack traces in this app.
    app.run(host="127.0.0.1", port=5000)
