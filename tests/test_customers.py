import pytest

from app.customers import build_sandbox_customers


def test_sandbox_customers_have_names_and_distinct_tax_ids():
    customers = build_sandbox_customers(count=100, seed=42)

    assert len(customers) == 100
    assert all(customer.name.strip() for customer in customers)
    assert all(
        len(customer.tax_id) == 11 and customer.tax_id.isdigit()
        for customer in customers
    )
    assert len({customer.tax_id for customer in customers}) == 100


def test_sandbox_customers_are_reproducible_with_same_seed():
    first = build_sandbox_customers(count=10, seed=42)
    second = build_sandbox_customers(count=10, seed=42)

    assert first == second


@pytest.mark.parametrize("count", [0, -1, True, "10"])
def test_sandbox_customers_reject_invalid_count(count):
    with pytest.raises(
        ValueError,
        match="Customer count must be a positive integer",
    ):
        build_sandbox_customers(count=count)