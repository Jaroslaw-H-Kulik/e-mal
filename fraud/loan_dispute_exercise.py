"""
Practice exercise — modeled after a "Writing Code Interview" (~60 minutes).

--------------------------------------------------------------------------
PART 1 (implement)

A loan can have one or more "disputes" opened against it (e.g. a borrower
contests a charge). Each dispute's status changes over time, and every
status change is recorded as a `DisputeEvent`. A single dispute can
therefore have *multiple* events (e.g. it was opened, then later closed,
or opened then later flagged as fraud).

Implement `determine_loan_status`, which takes ALL dispute events recorded
against a loan (for potentially several distinct disputes, each identified
by `dispute_id`) and returns the loan's final `LoanStatus`, using these
business rules:

  * If the *latest* status of at least one dispute is FRAUD,
    the loan is FRAUDULENT.
  * Otherwise, if the *latest* status of at least one dispute is OPEN,
    the loan is UNDER_INVESTIGATION.
  * Otherwise (every dispute's latest status is CLOSED, or there are no
    disputes at all), the loan is OK.

You are given helper functions below — use them; do not reimplement
grouping/sorting logic inline.

--------------------------------------------------------------------------
PART 2 (debug)

Once part 1 is implemented, some tests will still fail. One of the
"already implemented" helper functions has a bug: it determines a
dispute's most recent event by sorting on the wrong field. Find it and
fix it.
--------------------------------------------------------------------------
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List


class DisputeStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FRAUD = "FRAUD"


class LoanStatus(Enum):
    OK = "OK"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    FRAUDULENT = "FRAUDULENT"


@dataclass(frozen=True)
class DisputeEvent:
    event_id: int
    dispute_id: str
    status: DisputeStatus
    date_created: date


# --------------------------------------------------------------------------
# Helper functions (already implemented) — use these, do not modify their
# signatures. One of them contains the bug described in Part 2.
# --------------------------------------------------------------------------

def group_events_by_dispute(
    events: List[DisputeEvent],
) -> Dict[str, List[DisputeEvent]]:
    """Groups events by their dispute_id."""
    grouped: Dict[str, List[DisputeEvent]] = {}
    for event in events:
        grouped.setdefault(event.dispute_id, []).append(event)
    return grouped


def get_latest_event(events: List[DisputeEvent]) -> DisputeEvent:
    """Returns the most recently created event out of the given list."""
    return sorted(events, key=lambda e: e.date_created)[-1]


def get_latest_status_per_dispute(
    events: List[DisputeEvent],
) -> List[DisputeStatus]:
    """Returns the current (latest) status of each distinct dispute."""
    grouped = group_events_by_dispute(events)

    result = [get_latest_event(dispute_events).status for dispute_events in grouped.values()]

    return result

# --------------------------------------------------------------------------
# TODO: implement this function (Part 1)
# --------------------------------------------------------------------------

def determine_loan_status(events: List[DisputeEvent]) -> LoanStatus:
    """
    Determines the final status of a loan from all of its dispute events.

    See the business rules described in the module docstring above.
    """
    
    # if empty return OK?

    dispute_statuses = get_latest_status_per_dispute(events)

    result = LoanStatus.OK
    for status in dispute_statuses:
        if status == DisputeStatus.FRAUD:
            result = LoanStatus.FRAUDULENT
        if status == DisputeStatus.OPEN and result != LoanStatus.FRAUDULENT:
            result = LoanStatus.UNDER_INVESTIGATION

    return result