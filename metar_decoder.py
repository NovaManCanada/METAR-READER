"""Decode raw METAR text into a plain-English weather summary."""
import re

COMPASS_POINTS = [
    (0, "N"), (23, "NNE"), (68, "ENE"), (113, "ESE"), (158, "SE"),
    (203, "SSE"), (248, "S"), (293, "SSW"), (338, "SW"), (360, "N"),
]

WEATHER_CODES = {
    "DZ": "drizzle", "RA": "rain", "SN": "snow", "SG": "snow grains",
    "IC": "ice crystals", "PL": "ice pellets", "GR": "hail",
    "GS": "small hail", "UP": "unknown precipitation",
    "BR": "mist", "FG": "fog", "FU": "smoke", "VA": "volcanic ash",
    "DU": "dust", "SA": "sand", "HZ": "haze", "PY": "spray",
    "PO": "dust whirls", "SQ": "squalls", "FC": "funnel cloud",
    "SS": "sandstorm", "DS": "duststorm",
}

WEATHER_INTENSITY = {"-": "light", "+": "heavy", "VC": "nearby"}

SKY_COVER = {
    "SKC": "sky clear", "CLR": "clear skies", "NSC": "no significant cloud",
    "FEW": "a few clouds", "SCT": "scattered clouds",
    "BKN": "broken clouds", "OVC": "overcast",
}


def _compass(degrees: int) -> str:
    for upper, name in COMPASS_POINTS:
        if degrees <= upper:
            return name
    return "N"


def _decode_wind(token: str) -> str:
    match = re.match(r"^(\d{3}|VRB)(\d{2,3})(G(\d{2,3}))?(KT|MPS)$", token)
    if not match:
        return None
    direction, speed, _, gust, unit = match.groups()
    speed = int(speed)
    unit_label = "mph" if unit == "KT" else "m/s"
    speed_display = round(speed * 1.15078) if unit == "KT" else speed
    unit_display = "mph"

    if direction == "VRB":
        text = f"variable-direction wind at {speed_display} {unit_display}"
    else:
        text = f"wind {speed_display} {unit_display} from the {_compass(int(direction))}"

    if gust:
        gust_display = round(int(gust) * 1.15078) if unit == "KT" else int(gust)
        text += f", gusting to {gust_display} {unit_display}"
    return text


def _decode_visibility(token: str) -> str:
    if token == "CAVOK":
        return "ceiling and visibility OK"
    match = re.match(r"^(\d+)SM$", token)
    if match:
        return f"visibility {int(match.group(1))} miles"
    match = re.match(r"^(\d{4})$", token)
    if match:
        meters = int(match.group(1))
        if meters == 9999:
            return "visibility 10+ km"
        return f"visibility {meters} meters"
    return None


def _decode_weather(token: str) -> str:
    remaining = token
    intensity = ""
    if remaining.startswith(("-", "+")):
        intensity = WEATHER_INTENSITY[remaining[0]]
        remaining = remaining[1:]
    elif remaining.startswith("VC"):
        intensity = WEATHER_INTENSITY["VC"]
        remaining = remaining[2:]

    phenomena = []
    while remaining:
        code = remaining[:2]
        if code in WEATHER_CODES:
            phenomena.append(WEATHER_CODES[code])
            remaining = remaining[2:]
        else:
            return None

    if not phenomena:
        return None
    description = " ".join(phenomena)
    return f"{intensity} {description}".strip()


def _decode_sky(token: str) -> str:
    match = re.match(r"^(SKC|CLR|NSC|FEW|SCT|BKN|OVC)(\d{3})?(CB|TCU)?$", token)
    if not match:
        return None
    cover, height, cloud_type = match.groups()
    text = SKY_COVER[cover]
    if height:
        feet = int(height) * 100
        text += f" at {feet:,} ft"
    if cloud_type == "CB":
        text += " (cumulonimbus)"
    elif cloud_type == "TCU":
        text += " (towering cumulus)"
    return text


def _decode_temp_dewpoint(token: str) -> str:
    match = re.match(r"^(M?\d{2})/(M?\d{2})$", token)
    if not match:
        return None
    temp_raw, dew_raw = match.groups()
    temp_c = -int(temp_raw[1:]) if temp_raw.startswith("M") else int(temp_raw)
    dew_c = -int(dew_raw[1:]) if dew_raw.startswith("M") else int(dew_raw)
    temp_f = round(temp_c * 9 / 5 + 32)
    dew_f = round(dew_c * 9 / 5 + 32)
    return f"temperature {temp_f}°F, dew point {dew_f}°F"


def _decode_altimeter(token: str) -> str:
    match = re.match(r"^A(\d{4})$", token)
    if match:
        inches = int(match.group(1)) / 100
        return f"altimeter {inches:.2f} inHg"
    match = re.match(r"^Q(\d{4})$", token)
    if match:
        return f"altimeter {int(match.group(1))} hPa"
    return None


def _capitalize_first_letter(value: str) -> str:
    """Capitalize value's first character if it's a letter, e.g. for table display."""
    if value and value[0].isalpha():
        return value[0].upper() + value[1:]
    return value


def _strip_redundant_label(label: str, value: str) -> str:
    """Trim a decoded phrase's leading category words for table display.

    Decoded phrases like "wind 6 mph from the SSE" repeat the category
    name that a table's label column already shows, so drop it there.
    """
    if label == "Temperature / Dew Point":
        return value.replace("temperature ", "").replace(", dew point ", " / ")
    prefix = label.lower() + " "
    return value[len(prefix):] if value.lower().startswith(prefix) else value


FIELD_DECODERS = (
    ("Wind", _decode_wind),
    ("Visibility", _decode_visibility),
    ("Weather", _decode_weather),
    ("Sky Condition", _decode_sky),
    ("Temperature / Dew Point", _decode_temp_dewpoint),
    ("Altimeter", _decode_altimeter),
)


def decode_metar(raw_text: str) -> dict:
    """Decode a raw METAR string into structured plain-English parts.

    Returns a dict with 'station', 'observed_at', 'summary_sentence',
    'details' (list of decoded phrases), and 'fields' (list of
    {'label', 'value'} dicts, one per weather category, for tabular
    display). Unknown/unparsed tokens are ignored.
    """
    tokens = raw_text.strip().split()
    if tokens and tokens[0] in ("METAR", "SPECI"):
        tokens = tokens[1:]
    if not tokens:
        return {
            "station": None,
            "observed_at": None,
            "details": [],
            "fields": [],
            "summary_sentence": "No data available.",
        }

    station = tokens[0] if re.match(r"^[A-Z0-9]{3,4}$", tokens[0]) else None
    observed_at = None
    details = []
    field_values = {}

    for token in tokens[1:]:
        if re.match(r"^\d{6}Z$", token):
            day, hour, minute = token[0:2], token[2:4], token[4:6]
            observed_at = f"day {int(day)} at {hour}:{minute} UTC"
            continue
        if token in ("AUTO", "RMK"):
            if token == "RMK":
                break
            continue

        for label, decoder in FIELD_DECODERS:
            result = decoder(token)
            if result:
                details.append(result)
                field_values.setdefault(label, []).append(result)
                break

    fields = [
        {"label": label, "value": _capitalize_first_letter(_strip_redundant_label(label, "; ".join(values)))}
        for label, values in field_values.items()
    ]
    summary_sentence = format_summary(details)
    return {
        "station": station,
        "observed_at": observed_at,
        "details": details,
        "fields": fields,
        "summary_sentence": summary_sentence,
    }


def format_summary(details: list) -> str:
    if not details:
        return "No decodable weather details found."
    return ", ".join(details) + "."
