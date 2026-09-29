import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pytest

from app.batch_payload import deserialize_invoice_batch
from app.batch_store import (
    claim_batch,
    load_batch_payload,
    save_batch_payload,
    save_batch_result,
    save_batch_schedule,
    load_batch_result
)
from app.invoices import Customer, InvoiceDraft

import json


def make_invoices(amount=1000):
    return [
        InvoiceDraft(
            customer=Customer(
                name=f"Pessoa de Teste {index}",
                tax_id="00000000000",
            ),
            amount=amount + index,
        )
        for index in range(8)
    ]


def prepare_batch(database_path):
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)
    claim_batch(database_path, 1, now=start_at)


def read_payload(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """
            SELECT content
            FROM invoice_batch_payloads
            WHERE batch_number = ?
            """,
            (1,),
        ).fetchone()

    return deserialize_invoice_batch(row[0])


def test_save_payload_persists_invoice_data(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    invoices = make_invoices()

    saved = save_batch_payload(database_path, 1, invoices)

    assert saved is True
    assert read_payload(database_path) == invoices


def test_save_payload_accepts_repeated_identical_data(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    invoices = make_invoices()
    save_batch_payload(database_path, 1, invoices)

    saved_again = save_batch_payload(database_path, 1, invoices)

    assert saved_again is False
    assert read_payload(database_path) == invoices


def test_save_payload_rejects_changes_to_saved_invoices(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    original = make_invoices(amount=1000)
    save_batch_payload(database_path, 1, original)

    with pytest.raises(
        ValueError,
        match="A different payload already exists",
    ):
        save_batch_payload(
            database_path,
            1,
            make_invoices(amount=2000),
        )

    assert read_payload(database_path) == original


@pytest.mark.parametrize("batch_number", [2, 99])
def test_save_payload_requires_processing_batch(tmp_path, batch_number):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)

    with pytest.raises(ValueError, match="Processing batch not found"):
        save_batch_payload(
            database_path,
            batch_number,
            make_invoices(),
        )

def test_load_payload_restores_saved_invoices(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    invoices = make_invoices()
    save_batch_payload(database_path, 1, invoices)

    restored = load_batch_payload(database_path, 1)

    assert restored == invoices


def test_load_payload_returns_none_before_payload_table_exists(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)

    assert load_batch_payload(database_path, 1) is None


def test_load_payload_returns_none_for_batch_without_payload(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    save_batch_payload(database_path, 1, make_invoices())

    assert load_batch_payload(database_path, 2) is None

def read_result(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """
            SELECT invoice_ids
            FROM invoice_batch_results
            WHERE batch_number = ?
            """,
            (1,),
        ).fetchone()

    return json.loads(row[0])


def test_save_result_persists_ids_and_accepts_repeated_confirmation(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    save_batch_payload(database_path, 1, make_invoices())
    invoice_ids = [f"invoice-{index}" for index in range(8)]

    save_batch_result(database_path, 1, invoice_ids)
    save_batch_result(database_path, 1, list(reversed(invoice_ids)))

    assert read_result(database_path) == invoice_ids


def test_save_result_preserves_original_when_confirmation_conflicts(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    save_batch_payload(database_path, 1, make_invoices())
    original_ids = [f"invoice-{index}" for index in range(8)]
    save_batch_result(database_path, 1, original_ids)

    with pytest.raises(ValueError, match="A different batch result"):
        save_batch_result(
            database_path,
            1,
            [f"other-{index}" for index in range(8)],
        )

    assert read_result(database_path) == original_ids


@pytest.mark.parametrize(
    ("invoice_ids", "message"),
    [
        ([""] * 8, "Invoice IDs must be non-empty strings"),
        (["same-id"] * 8, "Invoice IDs must be unique"),
        (
            [f"invoice-{index}" for index in range(7)],
            "Invoice count differs from planned batch",
        ),
    ],
)
def test_save_result_rejects_invalid_confirmation(
    tmp_path,
    invoice_ids,
    message,
):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    save_batch_payload(database_path, 1, make_invoices())

    with pytest.raises(ValueError, match=message):
        save_batch_result(database_path, 1, invoice_ids)

def test_load_result_restores_saved_invoice_ids(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    save_batch_payload(database_path, 1, make_invoices())
    invoice_ids = [f"invoice-{index}" for index in range(8)]
    save_batch_result(database_path, 1, invoice_ids)

    restored = load_batch_result(database_path, 1)

    assert restored == invoice_ids


def test_load_result_returns_none_before_results_table_exists(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)

    assert load_batch_result(database_path, 1) is None


def test_load_result_returns_none_for_batch_without_confirmation(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_batch(database_path)
    save_batch_payload(database_path, 1, make_invoices())
    save_batch_result(
        database_path,
        1,
        [f"invoice-{index}" for index in range(8)],
    )

    assert load_batch_result(database_path, 2) is None