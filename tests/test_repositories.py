from datetime import datetime, timedelta, timezone

from core.repositories import (
    _aggregate_by_normalized_name,
    _as_aware_utc,
    _duration_seconds,
    _normalize_activity_name,
)


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


def test_aggregate_empty_rows_returns_empty_list():
    assert _aggregate_by_normalized_name([]) == []


def test_aggregate_merges_differently_normalized_names():
    rows = [("Call of Duty® Black Ops 7", 10), ("Call of Duty: Black Ops 7", 5)]
    assert _aggregate_by_normalized_name(rows) == [("Call of Duty Black Ops 7", 15)]


def test_aggregate_merges_case_insensitively():
    rows = [("Valorant", 10), ("valorant", 5)]
    assert _aggregate_by_normalized_name(rows) == [("Valorant", 15)]


def test_aggregate_canonical_name_is_first_occurrence():
    rows = [("valorant", 10), ("Valorant", 5)]
    assert _aggregate_by_normalized_name(rows) == [("valorant", 15)]


def test_aggregate_treats_none_seconds_as_zero():
    rows = [("Valorant", None), ("Valorant", 10)]
    assert _aggregate_by_normalized_name(rows) == [("Valorant", 10)]


def test_aggregate_all_none_seconds_totals_zero():
    rows = [("Valorant", None), ("Valorant", None)]
    assert _aggregate_by_normalized_name(rows) == [("Valorant", 0)]


def test_aggregate_limit_none_returns_all():
    rows = [("A", 3), ("B", 2), ("C", 1)]
    assert _aggregate_by_normalized_name(rows, limit=None) == [("A", 3), ("B", 2), ("C", 1)]


def test_aggregate_limit_zero_returns_empty():
    rows = [("A", 3), ("B", 2)]
    assert _aggregate_by_normalized_name(rows, limit=0) == []


def test_aggregate_limit_larger_than_groups_returns_all():
    rows = [("A", 3), ("B", 2)]
    assert _aggregate_by_normalized_name(rows, limit=10) == [("A", 3), ("B", 2)]


def test_aggregate_limit_truncates_to_top_n():
    rows = [("A", 3), ("B", 2), ("C", 1)]
    assert _aggregate_by_normalized_name(rows, limit=2) == [("A", 3), ("B", 2)]


def test_aggregate_ties_preserve_first_seen_order():
    rows = [("B", 5), ("A", 5)]
    assert _aggregate_by_normalized_name(rows) == [("B", 5), ("A", 5)]


def test_aggregate_single_row():
    assert _aggregate_by_normalized_name([("Valorant", 42)]) == [("Valorant", 42)]


def test_aggregate_passes_through_negative_seconds():
    assert _aggregate_by_normalized_name([("Valorant", -5)]) == [("Valorant", -5)]


def test_duration_seconds_zero_when_start_equals_end():
    now = datetime.now(timezone.utc)
    assert _duration_seconds(now, now) == 0


def test_duration_seconds_truncates_fractional_seconds():
    start = datetime.now(timezone.utc)
    assert _duration_seconds(start, start + timedelta(milliseconds=500)) == 0
    assert _duration_seconds(start, start + timedelta(milliseconds=1900)) == 1


def test_duration_seconds_naive_end_treated_as_utc():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_naive = datetime(2024, 1, 1, 0, 0, 30)
    assert _duration_seconds(start, end_naive) == 30


def test_duration_seconds_naive_start_treated_as_utc():
    start_naive = datetime(2024, 1, 1, 0, 0, 0)
    end = datetime(2024, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
    assert _duration_seconds(start_naive, end) == 30


def test_duration_seconds_both_naive():
    start = datetime(2024, 1, 1, 0, 0, 0)
    end = datetime(2024, 1, 1, 0, 1, 0)
    assert _duration_seconds(start, end) == 60


def test_duration_seconds_non_utc_aware_not_converted():
    tz = timezone(timedelta(hours=2))
    start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=tz)
    end = datetime(2024, 1, 1, 10, 1, 0, tzinfo=tz)
    assert _duration_seconds(start, end) == 60


def test_duration_seconds_negative_when_end_before_start():
    start = datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert _duration_seconds(start, end) == -60


def test_as_aware_utc_attaches_utc_to_naive_datetime():
    naive = datetime(2024, 1, 1, 12, 0, 0)
    result = _as_aware_utc(naive)
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive


def test_as_aware_utc_leaves_aware_datetime_unchanged():
    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert _as_aware_utc(aware) == aware
