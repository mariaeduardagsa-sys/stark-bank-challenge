from datetime import datetime, timedelta, timezone

import pytest

from app.schedule import build_batch_schedule

def test_schedule_has_eight_batches_every_three_hours():
    start_at = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)

    schedule = build_batch_schedule(start_at)

    assert len(schedule) == 8
    assert schedule[0] == start_at
    assert schedule[-1] == start_at + timedelta(hours=21)

    for previous, current in zip(schedule, schedule[1:]):
        assert (current - previous) == timedelta(hours=3)

def test_schedule_rejects_datetime_without_timezone():
    start_at = datetime(2026, 9, 23,12)
    with pytest.raises(ValueError, match="start_at must include a timezone"):
        build_batch_schedule(start_at)