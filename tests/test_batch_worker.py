from datetime import datetime, timedelta, timezone
from random import Random
from unittest.mock import Mock, patch

import pytest

from app.batch_worker import run_batch_loop


def test_worker_repeats_rounds_and_stops_at_deadline(tmp_path):
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    current = start_at
    waits = []

    def clock():
        return current

    def fake_sleep(seconds):
        nonlocal current
        waits.append(seconds)
        current += timedelta(seconds=seconds)

    with patch("app.batch_worker.run_due_batches") as mock_run:
        mock_run.return_value = []

        run_batch_loop(
            database_path=tmp_path / "events.db",
            customers=[],
            rng=Random(42),
            project=object(),
            end_at=start_at + timedelta(seconds=65),
            interval_seconds=30,
            clock=clock,
            sleep=fake_sleep,
        )

        assert mock_run.call_count == 3

    assert waits == [30, 30, 5]
    assert current == start_at + timedelta(seconds=65)


def test_worker_does_not_start_after_deadline(tmp_path):
    end_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    fake_sleep = Mock()

    with patch("app.batch_worker.run_due_batches") as mock_run:
        run_batch_loop(
            database_path=tmp_path / "events.db",
            customers=[],
            rng=Random(42),
            project=object(),
            end_at=end_at,
            clock=lambda: end_at,
            sleep=fake_sleep,
        )

        mock_run.assert_not_called()

    fake_sleep.assert_not_called()


def test_worker_rejects_zero_interval(tmp_path):
    with pytest.raises(ValueError, match="Interval must be a positive integer"):
        run_batch_loop(
            database_path=tmp_path / "events.db",
            customers=[],
            rng=Random(42),
            project=object(),
            end_at=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
            interval_seconds=0,
        )