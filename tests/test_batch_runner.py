from datetime import datetime, timezone
from random import Random
from unittest.mock import patch

from app.batch_runner import run_due_batches


def test_runner_does_not_process_when_no_batches_are_due(tmp_path):
    now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    with (
        patch("app.batch_runner.list_due_batches") as mock_list,
        patch("app.batch_runner.process_batch") as mock_process,
    ):
        mock_list.return_value = []

        results = run_due_batches(
            database_path=tmp_path / "events.db",
            customers=[],
            rng=Random(42),
            project=object(),
            clock=lambda: now,
        )

        mock_process.assert_not_called()

    assert results == []


def test_runner_continues_to_next_batch_after_failure(tmp_path, caplog):
    now = datetime(2026, 10, 1, 15, tzinfo=timezone.utc)

    with (
        patch("app.batch_runner.list_due_batches") as mock_list,
        patch("app.batch_runner.process_batch") as mock_process,
    ):
        mock_list.return_value = [
            (1, now),
            (2, now),
        ]

        mock_process.side_effect = [
            RuntimeError("Response unavailable"),
            "completed",
        ]

        results = run_due_batches(
            database_path=tmp_path / "events.db",
            customers=[],
            rng=Random(42),
            project=object(),
            clock=lambda: now,
        )

        processed_numbers = [
            call.kwargs["batch_number"]
            for call in mock_process.call_args_list
        ]

    assert processed_numbers == [1, 2]
    assert results == [
        (1, "error"),
        (2, "completed"),
    ]
    assert "Failed to process batch 1" in caplog.text
    assert "Response unavailable" in caplog.text