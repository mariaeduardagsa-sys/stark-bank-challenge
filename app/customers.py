from faker import Faker

from app.invoices import Customer


def build_sandbox_customers(
    count: int = 100,
    seed: int | None = None,
) -> list[Customer]:
    if type(count) is not int or count <= 0:
        raise ValueError("Customer count must be a positive integer")

    fake = Faker("pt_BR")

    if seed is not None:
        fake.seed_instance(seed)

    return [
        Customer(
            name=fake.name(),
            tax_id=fake.unique.ssn(),
        )
        for _ in range(count)
    ]