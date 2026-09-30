import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from app.batch_store import (
    claim_batch,
    complete_batch,
    list_due_batches,
    list_pending_batches,
    save_batch_schedule,
    save_batch_payload, 
    save_batch_result,
    mark_batch_for_review,
    check_batch_send_window,
    load_schedule_end
)

from app.invoices import Customer, InvoiceDraft


def read_batches(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        return connection.execute(
            """
            SELECT batch_number, scheduled_at, status
            FROM invoice_batches
            ORDER BY batch_number
            """
        ).fetchall()


def test_save_schedule_persists_eight_pending_batches(tmp_path):
    database_path = tmp_path / "data" / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    saved = save_batch_schedule(database_path, start_at)

    rows = read_batches(database_path)

    assert saved is True
    assert len(rows) == 8
    assert [row[0] for row in rows] == list(range(1, 9))
    assert all(row[2] == "pending" for row in rows)

    saved_times = [
        datetime.fromisoformat(row[1])
        for row in rows
    ]

    assert saved_times == [
        start_at + timedelta(hours=3 * index)
        for index in range(8)
    ]


def test_save_schedule_does_not_duplicate_existing_batches(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    save_batch_schedule(database_path, start_at)
    original_rows = read_batches(database_path)

    saved_again = save_batch_schedule(database_path, start_at)

    assert saved_again is False
    assert read_batches(database_path) == original_rows


def test_save_schedule_rejects_different_start_time(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    save_batch_schedule(database_path, start_at)
    original_rows = read_batches(database_path)

    with pytest.raises(
        ValueError,
        match="A different batch schedule already exists",
    ):
        save_batch_schedule(
            database_path,
            start_at + timedelta(hours=1),
        )

    assert read_batches(database_path) == original_rows

def test_list_pending_batches_does_not_create_missing_database(tmp_path):
    database_path = tmp_path / "events.db"

    assert list_pending_batches(database_path) == []
    assert not database_path.exists()


def test_list_pending_batches_handles_database_without_schedule(tmp_path):
    database_path = tmp_path / "events.db"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("CREATE TABLE example (id INTEGER)")

    assert list_pending_batches(database_path) == []


def test_list_pending_batches_restores_dates_and_excludes_finished(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                UPDATE invoice_batches
                SET status = 'completed'
                WHERE batch_number = 1
                """
            )

    batches = list_pending_batches(database_path)

    assert batches == [
        (number, start_at + timedelta(hours=3 * (number - 1)))
        for number in range(2, 9)
    ]
    
@pytest.mark.parametrize(
    ("elapsed", "expected_numbers"),
    [
        (timedelta(seconds=-1), []),
        (timedelta(0), [1]),
        (timedelta(hours=3, seconds=-1), [1]),
        (timedelta(hours=3), [1, 2]),
    ],
)
def test_list_due_batches_respects_scheduled_time(
    tmp_path,
    elapsed,
    expected_numbers,
):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    batches = list_due_batches(
        database_path,
        now=start_at + elapsed,
    )

    assert [number for number, _ in batches] == expected_numbers


def test_list_due_batches_rejects_datetime_without_timezone(tmp_path):
    database_path = tmp_path / "events.db"

    with pytest.raises(ValueError, match="now must include a timezone"):
        list_due_batches(
            database_path,
            now=datetime(2026, 10, 1, 12),
        )
    
def test_claim_batch_reserves_due_batch_only_once(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    first_claim = claim_batch(database_path, 1, now=start_at)
    second_claim = claim_batch(database_path, 1, now=start_at)

    assert first_claim is True
    assert second_claim is False

    rows = read_batches(database_path)

    assert rows[0][2] == "processing"
    assert all(row[2] == "pending" for row in rows[1:])
    assert list_due_batches(database_path, now=start_at) == []


def test_claim_batch_preserves_future_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    claimed = claim_batch(database_path, 2, now=start_at)

    assert claimed is False
    assert read_batches(database_path)[1][2] == "pending"


def test_claim_batch_returns_false_for_missing_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    original_rows = read_batches(database_path)

    claimed = claim_batch(database_path, 99, now=start_at)

    assert claimed is False
    assert read_batches(database_path) == original_rows


def test_claim_batch_rejects_datetime_without_timezone(tmp_path):
    database_path = tmp_path / "events.db"

    with pytest.raises(ValueError, match="now must include a timezone"):
        claim_batch(
            database_path,
            1,
            now=datetime(2026, 10, 1, 12),
        )

def test_complete_batch_finishes_processing_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    claim_batch(database_path, 1, now=start_at)

    invoices = [
        InvoiceDraft(
            customer=Customer(
                name="Pessoa de Teste",
                tax_id="00000000000",
            ),
            amount=1000,
        )
        for _ in range(8)
    ]

    save_batch_payload(database_path, 1, invoices)
    save_batch_result(
        database_path,
        1,
        [f"invoice-{index}" for index in range(8)],
    )

    complete_batch(database_path, 1)

    assert read_batches(database_path)[0][2] == "completed"
    assert claim_batch(database_path, 1, now=start_at) is False


def test_complete_batch_rejects_pending_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with pytest.raises(ValueError, match="Processing batch not found"):
        complete_batch(database_path, 1)

    assert read_batches(database_path)[0][2] == "pending"


def test_complete_batch_rejects_missing_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    original_rows = read_batches(database_path)

    with pytest.raises(ValueError, match="Processing batch not found"):
        complete_batch(database_path, 99)

    assert read_batches(database_path) == original_rows

@pytest.mark.parametrize("results_table_exists", [False, True])
def test_complete_batch_requires_saved_result(tmp_path, results_table_exists):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    claim_batch(database_path, 1, now=start_at)

    if results_table_exists:
        with closing(sqlite3.connect(database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE invoice_batch_results (
                        batch_number INTEGER PRIMARY KEY,
                        invoice_ids TEXT NOT NULL
                    )
                    """
                )

    with pytest.raises(ValueError, match="Batch result not found"):
        complete_batch(database_path, 1)

    assert read_batches(database_path)[0][2] == "processing"
    
@pytest.mark.parametrize(
    ("batch_number", "elapsed", "expected_claim", "expected_status"),
    [
        (
            1,
            timedelta(hours=3, seconds=-1),
            True,
            "processing",
        ),
        (
            1,
            timedelta(hours=3),
            False,
            "missed",
        ),
        (
            8,
            timedelta(hours=24, seconds=-1),
            True,
            "processing",
        ),
        (
            8,
            timedelta(hours=24),
            False,
            "missed",
        ),
    ],
)
def test_claim_batch_respects_execution_window(
    tmp_path,
    batch_number,
    elapsed,
    expected_claim,
    expected_status,
):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    claimed = claim_batch(
        database_path,
        batch_number,
        now=start_at + elapsed,
    )

    rows = read_batches(database_path)

    assert claimed is expected_claim
    assert rows[batch_number - 1][2] == expected_status
    assert batch_number not in [
        number
        for number, _ in list_pending_batches(database_path)
    ]

def test_mark_batch_for_review_prevents_new_claim(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    claim_batch(database_path, 1, now=start_at)

    mark_batch_for_review(database_path, 1)

    assert read_batches(database_path)[0][2] == "needs_review"
    assert claim_batch(database_path, 1, now=start_at) is False


@pytest.mark.parametrize("batch_number", [2, 99])
def test_mark_batch_for_review_requires_processing_batch(
    tmp_path,
    batch_number,
):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    original_rows = read_batches(database_path)

    with pytest.raises(ValueError, match="Processing batch not found"):
        mark_batch_for_review(database_path, batch_number)

    assert read_batches(database_path) == original_rows

@pytest.mark.parametrize(
    ("elapsed", "allowed", "expected_status"),
    [
        (timedelta(hours=2, minutes=59), True, "processing"),
        (timedelta(hours=3), False, "missed"),
    ],
)
def test_send_window_rechecks_time_after_claim(
    tmp_path,
    elapsed,
    allowed,
    expected_status,
):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    claim_batch(database_path, 1, now=start_at)

    result = check_batch_send_window(
        database_path,
        1,
        now=start_at + elapsed,
    )

    assert result is allowed
    assert read_batches(database_path)[0][2] == expected_status


def test_send_window_rejects_unclaimed_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with pytest.raises(ValueError, match="Processing batch not found"):
        check_batch_send_window(database_path, 1, now=start_at)

    assert read_batches(database_path)[0][2] == "pending"

def test_schedule_end_uses_original_start_even_after_status_changes(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    claim_batch(database_path, 1, now=start_at)
    mark_batch_for_review(database_path, 1)

    assert load_schedule_end(database_path) == (
        start_at + timedelta(hours=24)
    )


def test_schedule_end_returns_none_without_database(tmp_path):
    database_path = tmp_path / "events.db"

    assert load_schedule_end(database_path) is None
    assert not database_path.exists()