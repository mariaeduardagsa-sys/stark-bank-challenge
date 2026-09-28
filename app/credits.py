import json
from dataclasses import dataclass

@dataclass(frozen=True)
class InvoiceCredit:
    invoice_id: str
    amount: int
    
def extract_invoice_credit(content: str) -> InvoiceCredit | None:
    event = json.loads(content)["event"]
    
    if event["subscription"] != "invoice":
        return None
    
    log = event["log"]
    if log["type"] != "credited":
        return None
    
    invoice = log["invoice"]
    amount = invoice["amount"]
    fee = invoice["fee"]
    
    if type(amount) is not int or type(fee) is not int:
        raise ValueError("Invoice amount and fee must be integers")
    
    if amount < 0 or fee < 0:
        raise ValueError("Invoice amount and fee must not be negative")

    net_amount = amount - fee
    
    if net_amount <= 0:
        raise ValueError("Invoice net amount must be positive")
    
    return InvoiceCredit(
        invoice_id=invoice["id"],
        amount= net_amount
    )    