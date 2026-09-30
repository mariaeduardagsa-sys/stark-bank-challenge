from datetime import datetime, timezone
from random import Random

from app.batch_preparation import prepare_invoice_batch
from app.batch_store import (
    claim_batch,
    load_batch_payload,
    save_batch_schedule,
)
from app.invoices import Customer


def reserve_first_batch(database_path):
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    save_batch_schedule(database_path, start_at)

    assert claim_batch(database_path, 1, now=start_at) is True


def test_prepare_invoice_batch_generates_and_persists_invoices(tmp_path):
    database_path = tmp_path / "events.db"
    reserve_first_batch(database_path)

    customers = [
        Customer(name="Pessoa de Teste", tax_id="00000000000"),
    ]

    invoices = prepare_invoice_batch(
        database_path,
        batch_number=1,
        customers=customers,
        rng=Random(42),
    )

    assert 8 <= len(invoices) <= 12
    assert all(invoice.customer in customers for invoice in invoices)
    assert all(1000 <= invoice.amount <= 10000 for invoice in invoices)
    assert load_batch_payload(database_path, 1) == invoices


def test_prepare_invoice_batch_reuses_saved_data_without_new_draw(tmp_path):
    database_path = tmp_path / "events.db"
    reserve_first_batch(database_path)

    original = prepare_invoice_batch(
        database_path,
        batch_number=1,
        customers=[
            Customer(name="Pessoa Original", tax_id="00000000000"),
        ],
        rng=Random(42),
    )

    second_rng = Random(99)
    state_before = second_rng.getstate()

    restored = prepare_invoice_batch(
        database_path,
        batch_number=1,
        customers=[
            Customer(name="Outra Pessoa", tax_id="11111111111"),
        ],
        rng=second_rng,
    )

    assert restored == original
    assert second_rng.getstate() == state_before