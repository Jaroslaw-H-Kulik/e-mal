from datetime import date

import pytest

from loan_dispute_exercise import (
    DisputeEvent,
    DisputeStatus,
    LoanStatus,
    determine_loan_status,
)


def test_no_disputes_returns_ok():
    assert determine_loan_status([]) == LoanStatus.OK


def test_single_dispute_closed_returns_ok():
    events = [
        DisputeEvent(1, "D1", DisputeStatus.OPEN, date(2024, 1, 1)),
        DisputeEvent(2, "D1", DisputeStatus.CLOSED, date(2024, 1, 5)),
    ]
    assert determine_loan_status(events) == LoanStatus.OK


def test_all_disputes_closed_returns_ok():
    events = [
        DisputeEvent(1, "D1", DisputeStatus.CLOSED, date(2024, 1, 1)),
        DisputeEvent(2, "D2", DisputeStatus.CLOSED, date(2024, 1, 2)),
    ]
    assert determine_loan_status(events) == LoanStatus.OK


def test_any_dispute_open_returns_under_investigation():
    events = [
        DisputeEvent(1, "D1", DisputeStatus.CLOSED, date(2024, 1, 1)),
        DisputeEvent(2, "D2", DisputeStatus.OPEN, date(2024, 1, 2)),
    ]
    assert determine_loan_status(events) == LoanStatus.UNDER_INVESTIGATION


def test_any_dispute_fraud_returns_fraudulent():
    events = [
        DisputeEvent(1, "D1", DisputeStatus.CLOSED, date(2024, 1, 1)),
        DisputeEvent(2, "D2", DisputeStatus.FRAUD, date(2024, 1, 2)),
    ]
    assert determine_loan_status(events) == LoanStatus.FRAUDULENT


def test_fraud_takes_priority_over_open():
    events = [
        DisputeEvent(1, "D1", DisputeStatus.OPEN, date(2024, 1, 1)),
        DisputeEvent(2, "D2", DisputeStatus.FRAUD, date(2024, 1, 2)),
    ]
    assert determine_loan_status(events) == LoanStatus.FRAUDULENT


def test_reopened_dispute_uses_latest_status_not_first():
    # Dispute D1 was opened, then closed. It should count as CLOSED, not OPEN.
    events = [
        DisputeEvent(1, "D1", DisputeStatus.OPEN, date(2024, 1, 1)),
        DisputeEvent(2, "D1", DisputeStatus.CLOSED, date(2024, 1, 10)),
    ]
    assert determine_loan_status(events) == LoanStatus.OK


def test_latest_status_determined_by_date_not_event_id():
    """
    Regression test for the helper bug described in Part 2.

    D1's events are created out of event_id order: the event with the
    HIGHER event_id (2) actually happened EARLIER (2024-01-01) than the
    event with the LOWER event_id (1), which happened later (2024-01-15).
    This can occur in real systems (e.g. backfilled or imported events).

    The true latest event by date_created is event_id=1 (CLOSED,
    2024-01-15), so the dispute's current status is CLOSED and the loan
    should be OK. A buggy implementation that picks "latest" by sorting
    on event_id instead of date_created would incorrectly pick event_id=2
    (OPEN) as the latest and return UNDER_INVESTIGATION instead.
    """
    events = [
        DisputeEvent(1, "D1", DisputeStatus.CLOSED, date(2024, 1, 15)),
        DisputeEvent(2, "D1", DisputeStatus.OPEN, date(2024, 1, 1)),
    ]
    assert determine_loan_status(events) == LoanStatus.OK


def test_latest_fraud_status_detected_despite_event_id_order():
    """
    Same bug, but where getting the ordering wrong would hide a FRAUD
    status instead of falsely reporting one.
    """
    events = [
        DisputeEvent(5, "D1", DisputeStatus.OPEN, date(2024, 2, 1)),
        DisputeEvent(3, "D1", DisputeStatus.FRAUD, date(2024, 2, 20)),
    ]
    assert determine_loan_status(events) == LoanStatus.FRAUDULENT


def test_multiple_independent_disputes_each_use_their_own_latest_status():
    events = [
        # D1: opened then closed -> CLOSED
        DisputeEvent(1, "D1", DisputeStatus.OPEN, date(2024, 1, 1)),
        DisputeEvent(2, "D1", DisputeStatus.CLOSED, date(2024, 1, 3)),
        # D2: opened, still open -> OPEN
        DisputeEvent(3, "D2", DisputeStatus.OPEN, date(2024, 1, 2)),
    ]
    assert determine_loan_status(events) == LoanStatus.UNDER_INVESTIGATION


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
