"""Route-level tests for app.py.

These use Flask's test client against the real routes and templates,
but mock fetch_metar so no real network call is made. Mock METAR
strings stand in for aviationweather.gov responses, letting us verify
that a given raw reading is decoded and rendered correctly end to end.
"""
from unittest.mock import patch

import requests
import pytest

from app import app


def _report(label, response):
    """Print the request label and the dynamic parts of the rendered page.

    Only lines relevant to the decoded result (error/summary/raw METAR)
    are shown; the static HTML boilerplate is skipped for readability.
    """
    body = response.get_data(as_text=True)
    relevant = [
        line.strip()
        for line in body.splitlines()
        if any(marker in line for marker in ('class="error"', 'class="summary"', 'class="raw"', "<strong>"))
    ]
    print(f"\n  request:  {label}")
    print(f"  status:   {response.status_code}")
    print(f"  rendered: {' | '.join(relevant) if relevant else '(no error/summary content)'}")


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_index_shows_empty_form(client):
    response = client.get("/")
    _report("GET /", response)
    assert response.status_code == 200
    assert b"Airport Code" in response.data


def test_valid_airport_renders_decoded_summary(client):
    mock_raw = "KJFK 231951Z 18005KT 10SM FEW250 24/18 A3002"
    with patch("app.fetch_metar", return_value=mock_raw) as mock_fetch:
        response = client.get("/metar", query_string={"airport_code": "kjfk"})
    _report(f"GET /metar?airport_code=kjfk (mock raw: {mock_raw})", response)

    mock_fetch.assert_called_once_with("KJFK")
    assert response.status_code == 200
    assert b"KJFK" in response.data
    assert b"visibility 10 miles" in response.data
    assert mock_raw.encode() in response.data


def test_gusty_weather_reading_renders_decoded_details(client):
    mock_raw = "EGLL 231920Z 27015G25KT 6000 -RA BKN008 12/10 Q1005"
    with patch("app.fetch_metar", return_value=mock_raw):
        response = client.get("/metar", query_string={"airport_code": "EGLL"})
    _report(f"GET /metar?airport_code=EGLL (mock raw: {mock_raw})", response)

    assert response.status_code == 200
    assert "gusting to".encode() in response.data
    assert "light rain".encode() in response.data
    assert "broken clouds".encode() in response.data


def test_lowercase_and_whitespace_are_normalized(client):
    mock_raw = "KJFK 231951Z 18005KT 10SM FEW250 24/18 A3002"
    with patch("app.fetch_metar", return_value=mock_raw) as mock_fetch:
        response = client.get("/metar", query_string={"airport_code": "  kjfk  "})
    _report("GET /metar?airport_code=  kjfk  ", response)

    mock_fetch.assert_called_once_with("KJFK")


@pytest.mark.parametrize("bad_code", ["", "K", "TOOLONG", "K J", "12345"])
def test_invalid_airport_code_shows_error_without_calling_api(client, bad_code):
    with patch("app.fetch_metar") as mock_fetch:
        response = client.get("/metar", query_string={"airport_code": bad_code})
    _report(f"GET /metar?airport_code={bad_code!r}", response)

    mock_fetch.assert_not_called()
    assert response.status_code == 200
    assert b"Enter a valid 3-4 character airport code" in response.data


def test_no_data_for_airport_shows_error(client):
    with patch("app.fetch_metar", return_value=None):
        response = client.get("/metar", query_string={"airport_code": "ZZZZ"})
    _report("GET /metar?airport_code=ZZZZ (mock raw: None)", response)

    assert response.status_code == 200
    assert b"No weather data found for that airport code." in response.data


def test_api_failure_shows_service_error(client):
    with patch("app.fetch_metar", side_effect=requests.RequestException("boom")):
        response = client.get("/metar", query_string={"airport_code": "KJFK"})
    _report("GET /metar?airport_code=KJFK (mock raises RequestException)", response)

    assert response.status_code == 200
    assert b"Could not reach the weather service" in response.data
