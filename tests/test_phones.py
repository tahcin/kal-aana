from kalaana import phones


def test_parse_maps_formats():
    assert phones.parse("098765 00000").kind == "mobile"
    assert phones.parse("080 4377 2979").kind == "landline"
    assert phones.parse("1800 258 5603").kind == "toll_free"
    assert phones.parse("1860 233 1234").kind == "shared_cost"
    assert phones.parse("1600 123 4567").kind == "bfsi_1600"


def test_same_number_same_key():
    assert phones.parse("080-68727374").key == phones.parse("+91 80 6872 7374").key


def test_find_all_in_snippet():
    text = "T: 080-68422422 Registered Office. Call 1800 258 5603 or WhatsApp 98765 43210."
    kinds = sorted(p.kind for p in phones.find_all(text))
    assert kinds == ["landline", "mobile", "toll_free"]


def test_ignores_ids_and_dates():
    text = "nct-12099485 created 2026-10-07 19:45:17 id 150723174009"
    assert phones.find_all(text) == []


def test_mask_mobile_only():
    assert phones.parse("098765 00000").masked == "98••• •••00"
    assert phones.parse("1800 258 5603").masked == phones.parse("1800 258 5603").display


def test_errors_never_contain_the_api_key():
    from kalaana.client import _redact
    key = "a" * 64
    msg = _redact(f"https://serpapi.com/search?q=x&api_key={key}&gl=in failed for {key}", key)
    assert key not in msg and "api_key=***" in msg


def test_display_by_kind():
    assert phones.parse("094498 63448").display == "94498 63448"
    assert phones.parse("080-26630989").display == "080 2663 0989"
    assert phones.parse("1600 123 4567").display == "16001234567"


def test_area_code_and_region():
    noida_or_ghaziabad = phones.parse("0120 492 5505")
    assert noida_or_ghaziabad.area_code == "120" and "Uttar Pradesh" in noida_or_ghaziabad.region
    bengaluru = phones.parse("080 2663 0989")
    assert bengaluru.area_code == "80" and bengaluru.region == "Bangalore, Karnataka"
    assert phones.parse("94498 63448").area_code == "" and phones.parse("1800 258 1800").region == ""
