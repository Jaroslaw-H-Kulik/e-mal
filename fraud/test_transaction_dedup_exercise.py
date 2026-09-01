from datetime import datetime
from decimal import Decimal

import pytest

from transaction_dedup_exercise import (
    Transaction,
    TransactionStatus,
    compute_settled_balance,
)


def test_no_transactions_returns_zero():
    assert compute_settled_balance([], "A1") == Decimal("0")


def test_single_settled_transaction_is_counted():
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("100.00")


def test_pending_and_failed_transactions_are_excluded():
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1)),
        Transaction("T2", "A1", "K2", Decimal("50.00"), TransactionStatus.PENDING, datetime(2024, 1, 2)),
        Transaction("T3", "A1", "K3", Decimal("25.00"), TransactionStatus.FAILED, datetime(2024, 1, 3)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("100.00")


def test_transactions_from_other_accounts_are_ignored():
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1)),
        Transaction("T2", "A2", "K2", Decimal("999.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("100.00")


def test_duplicate_submissions_are_counted_once_not_per_row():
    """
    Regression test for the Part 2 helper bug.

    A client retry resubmitted the same logical payment (same
    idempotency_key), producing two rows that both settled. A buggy
    implementation that fails to dedupe by idempotency_key would sum
    both rows and report the customer as charged twice.
    """
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 10, 0)),
        Transaction("T2", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 10, 5)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("100.00")


def test_duplicate_group_uses_latest_status_not_first():
    """
    The first submission was recorded as PENDING (before the retry
    actually completed); the retry is the row that settled. The current
    state of this logical transaction is SETTLED.
    """
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.PENDING, datetime(2024, 1, 1, 10, 0)),
        Transaction("T2", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 10, 5)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("100.00")


def test_duplicate_group_where_latest_is_not_settled_contributes_nothing():
    """
    The first submission settled, but a later duplicate row for the same
    idempotency_key ended up FAILED (e.g. a reconciliation correction).
    The current state is FAILED, so nothing should be counted — not even
    the earlier SETTLED amount.
    """
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 10, 0)),
        Transaction("T2", "A1", "K1", Decimal("100.00"), TransactionStatus.FAILED, datetime(2024, 1, 1, 10, 5)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("0")


def test_duplicate_group_uses_latest_amount_not_first():
    """
    The provisional amount recorded at submission time was corrected
    (e.g. FX conversion finalized) in a later duplicate row. The current
    amount is the one on the latest row.
    """
    txns = [
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 10, 0)),
        Transaction("T2", "A1", "K1", Decimal("98.50"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 10, 5)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("98.50")


def test_multiple_independent_duplicate_groups_sum_correctly():
    txns = [
        # K1: two duplicate rows, current state SETTLED $100
        Transaction("T1", "A1", "K1", Decimal("100.00"), TransactionStatus.PENDING, datetime(2024, 1, 1, 9, 0)),
        Transaction("T2", "A1", "K1", Decimal("100.00"), TransactionStatus.SETTLED, datetime(2024, 1, 1, 9, 5)),
        # K2: single row, SETTLED $50
        Transaction("T3", "A1", "K2", Decimal("50.00"), TransactionStatus.SETTLED, datetime(2024, 1, 2, 9, 0)),
        # K3: single row, still PENDING - excluded
        Transaction("T4", "A1", "K3", Decimal("30.00"), TransactionStatus.PENDING, datetime(2024, 1, 3, 9, 0)),
    ]
    assert compute_settled_balance(txns, "A1") == Decimal("150.00")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
