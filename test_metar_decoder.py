from metar_decoder import decode_metar


def test_decode_basic_metar():
    raw = "KJFK 231951Z 18005KT 10SM FEW250 24/18 A3002"
    result = decode_metar(raw)
    assert result["station"] == "KJFK"
    assert "wind" in result["summary_sentence"]
    assert "visibility 10 miles" in result["summary_sentence"]
    assert "temperature 75°F" in result["summary_sentence"]
    assert "altimeter 30.02 inHg" in result["summary_sentence"]


def test_decode_with_gusts_and_weather():
    raw = "EGLL 231920Z 27015G25KT 6000 -RA BKN008 12/10 Q1005"
    result = decode_metar(raw)
    assert result["station"] == "EGLL"
    assert "gusting to" in result["summary_sentence"]
    assert "light rain" in result["summary_sentence"]
    assert "broken clouds" in result["summary_sentence"]
    assert "altimeter 1005 hPa" in result["summary_sentence"]


def test_decode_cavok():
    raw = "LFPG 231800Z VRB02KT CAVOK 20/12 A3000"
    result = decode_metar(raw)
    assert "ceiling and visibility OK" in result["summary_sentence"]
    assert "variable-direction wind" in result["summary_sentence"]


def test_decode_empty_string():
    result = decode_metar("")
    assert result["station"] is None
    assert result["summary_sentence"] == "No data available."


def test_decode_strips_report_type_prefix():
    raw = "METAR KJFK 232151Z 05015G26KT 10SM FEW055 19/06 A3043 RMK AO2"
    result = decode_metar(raw)
    assert result["station"] == "KJFK"


def test_decode_ignores_remarks():
    raw = "KDEN 231953Z 09010KT 10SM CLR 15/M03 A3015 RMK AO2 SLP200"
    result = decode_metar(raw)
    assert "SLP200" not in result["summary_sentence"]
    assert "temperature 59°F, dew point 27°F" in result["summary_sentence"]
