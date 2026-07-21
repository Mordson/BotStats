from core.repositories import _normalize_activity_name


def test_strips_trademark_symbols():
    assert _normalize_activity_name("Call of Duty®") == "Call of Duty"


def test_collapses_subtitle_separator():
    assert _normalize_activity_name("Call of Duty: Black Ops 7") == "Call of Duty Black Ops 7"


def test_same_game_normalizes_to_same_name():
    assert _normalize_activity_name("Call of Duty® Black Ops 7") == _normalize_activity_name(
        "Call of Duty: Black Ops 7"
    )


def test_collapses_extra_whitespace():
    assert _normalize_activity_name("Valorant   ") == "Valorant"
