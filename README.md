# METAR Reader

A small Flask app that turns a cryptic METAR weather report into plain English.
Type in an airport code (e.g. `KJFK`, `EGLL`) and get back a readable summary
of wind, visibility, weather, clouds, temperature, and altimeter — plus the
raw METAR for reference.

Weather data comes from the public, unauthenticated
[aviationweather.gov API](https://aviationweather.gov/data/api/).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python app.py
```

Then open http://127.0.0.1:5000 and enter an airport code.

## Test

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest
```
