from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import run_batches


def test_watch_command_starts_loop_instead_of_single_round(monkeypatch):
    now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    end_at = now + timedelta(hours=24)
    project = object()

    monkeypatch.setattr(
        "sys.argv",
        ["run_batches.py", "--execute", "--watch"],
    )
    monkeypatch.setattr(run_batches, "utc_now", lambda: now)
    monkeypatch.setattr(
        run_batches,
        "list_pending_batches",
        lambda path: [(1, now + timedelta(minutes=5))],
    )
    monkeypatch.setattr(
        run_batches,
        "load_schedule_end",
        lambda path: end_at,
    )
    monkeypatch.setattr(run_batches, "get_project", lambda: project)
    monkeypatch.setattr(
        run_batches,
        "build_sandbox_customers",
        lambda: [],
    )

    with (
        patch("run_batches.run_batch_loop") as mock_loop,
        patch("run_batches.run_due_batches") as mock_round,
    ):
        run_batches.main()

        mock_loop.assert_called_once()
        mock_round.assert_not_called()
        assert mock_loop.call_args.kwargs["end_at"] == end_at
        assert mock_loop.call_args.kwargs["project"] is project