from cogs.community import parse_duration
from cogs.utility import parse_duration_spec


def test_parse_duration_spec_supports_seconds_minutes_hours_days():
    assert parse_duration_spec("15s") == 15
    assert parse_duration_spec("2m") == 120
    assert parse_duration_spec("3h") == 10800
    assert parse_duration_spec("4d") == 345600


def test_parse_duration_spec_rejects_invalid_values():
    assert parse_duration_spec("10") is None
    assert parse_duration_spec("abc") is None
    assert parse_duration_spec("5w") is None


def test_parse_duration_supports_minutes_hours_days():
    assert parse_duration("15m") == 900
    assert parse_duration("2h") == 7200
    assert parse_duration("3d") == 259200


def test_parse_duration_rejects_invalid_values():
    assert parse_duration("") is None
    assert parse_duration("30") is None
    assert parse_duration("abc") is None
    assert parse_duration("7s") is None
