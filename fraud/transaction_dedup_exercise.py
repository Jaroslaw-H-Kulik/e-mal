"""
Practice exercise #2 — modeled after a "Writing Code Interview" (~60 minutes).

--------------------------------------------------------------------------
BACKGROUND

Due to client retries and message-queue redelivery, the same logical
payment can be submitted more than once to this system. Every submission
is recorded as its own `Transaction` row, but duplicate submissions of the
same logical payment share the same `idempotency_key`. Because status is
only known at submission time, different rows for the same
`idempotency_key` can disagree (e.g. an early retry was recorded as
PENDING before the payment actually settled on a later attempt, or the
settled amount was corrected after an FX conversion).

--------------------------------------------------------------------------
PART 1 (implement)

Implement `compute_settled_balance`, which returns the total settled
balance for a given account, using these business rules:

  * Only transactions belonging to the given `account_id` count.
  * Transactions sharing the same `idempotency_key` are duplicate
    submissions of the *same* logical transaction and must be counted
    AT MOST ONCE.
  * Within a group of duplicates, the "current" state of that logical
    transaction is whichever row was created most recently — use its
    status AND its amount (earlier rows in the group may have had a
    provisional status or amount).
  * A logical transaction contributes to the balance only if its current
    status is SETTLED.

You are given helper functions below — use them; do not reimplement
grouping/dedup logic inline.

--------------------------------------------------------------------------
PART 2 (debug)

Once part 1 is implemented, some tests will still fail. One of the
"already implemented" helper functions groups records using the wrong
field, which defeats deduplication. Find it and fix it.
--------------------------------------------------------------------------
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List


class TransactionStatus(Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    idempotency_key: str
    amount: Decimal
    status: TransactionStatus
    created_at: datetime


# --------------------------------------------------------------------------
# Helper functions (already implemented) — use these, do not modify their
# signatures. One of them contains the bug described in Part 2.
# --------------------------------------------------------------------------

def filter_by_account(
    transactions: List[Transaction], account_id: str
) -> List[Transaction]:
    """Returns only the transactions belonging to the given account."""
    return [t for t in transactions if t.account_id == account_id]


def group_by_idempotency_key(
    transactions: List[Transaction],
) -> Dict[str, List[Transaction]]:
    """Groups transaction rows that represent the same logical
    transaction, i.e. duplicate submissions sharing an idempotency key."""
    grouped: Dict[str, List[Transaction]] = {}
    for t in transactions:
        grouped.setdefault(t.idempotency_key, []).append(t)
    return grouped


def get_latest_snapshot(transactions: List[Transaction]) -> Transaction:
    """Returns the most recently created row within a duplicate group."""
    return sorted(transactions, key=lambda t: t.created_at)[-1]


def dedupe_transactions(transactions: List[Transaction]) -> List[Transaction]:
    """Collapses duplicate submissions down to a single representative
    (the current/latest snapshot) per logical transaction."""
    grouped = group_by_idempotency_key(transactions)
    print("---Grouped---")
    print(grouped)
    result = [get_latest_snapshot(group) for group in grouped.values()]
    print(result)
    return result


# --------------------------------------------------------------------------
# TODO: implement this function (Part 1)
# --------------------------------------------------------------------------

def compute_settled_balance(transactions: List[Transaction], account_id: str) -> Decimal:
    """
    Returns the total settled balance for the given account.

    See the business rules described in the module docstring above.
    """

    transactions_by_account = filter_by_account(transactions, account_id)
    print("---By-Account---")
    print(transactions_by_account)
    deduped_transactions = dedupe_transactions(transactions_by_account)
    print("---Dedup---")
    print(deduped_transactions)

    result = 0
    for transaction in deduped_transactions:
        subresult = 0
        status = transaction.status
        if status == TransactionStatus.FAILED:
            subresult = 0
        if status == TransactionStatus.SETTLED:
            subresult = transaction.amount
        
        result = result + subresult

    return result
