# METAR Reader

A small Flask web app that turns a cryptic [METAR](https://en.wikipedia.org/wiki/METAR)
aviation weather report into plain English. Enter an airport code (e.g.
`KJFK`, `EGLL`) and get back a readable summary of wind, visibility,
weather, clouds, temperature, and altimeter — plus the raw METAR for
reference.

Weather data comes from the public, unauthenticated
[aviationweather.gov API](https://aviationweather.gov/data/api/). No
API key, account, or configuration is required.

## How it works

- `app.py` — Flask routes: serves the input form and, given an airport
  code, fetches the raw METAR and renders the decoded result.
- `metar_decoder.py` — parses a raw METAR string token by token and
  converts each part (wind, visibility, sky cover, temperature,
  altimeter, etc.) into a plain-English phrase.
- `templates/`, `static/` — the HTML page and its assets.

## Requirements

- Python 3.9+

## Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/<your-username>/METAR-READER.git
cd METAR-READER
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running the app

```bash
.venv/bin/python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your
browser and enter an airport code.

## Running the tests

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest
```

## Notes

This app is intended for local, single-user use. It stores no data and
requires no authentication or secrets — it only calls the public
aviationweather.gov API.
