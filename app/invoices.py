from dataclasses import dataclass
from random import Random 

@dataclass(frozen=True)
class Customer:
    name: str
    tax_id: str

@dataclass(frozen=True)
class InvoiceDraft:
    customer: Customer
    amount: int 

def build_invoice_batch(customers: list[Customer], rng: Random,) -> list[InvoiceDraft]:
    if not customers:
        raise ValueError("customers must not be empty")
    
    batch_size = rng.randint(8,12)

    return [
        InvoiceDraft(
            customer=rng.choice(customers),
            amount=rng.randint(1000, 10000)
        )
        for _ in range(batch_size)
    ]