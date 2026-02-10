"""
Time utilities for the Task Tracker application.

This module provides a single source of truth for time operations,
ensuring consistency across all endpoints and preventing clock drift issues.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time.
    Single source of truth for "now" throughout the application.

    Returns:
        timezone-aware datetime in UTC
    """
    return datetime.now(timezone.utc)


def is_overdue(due_date: Optional[datetime], status: str) -> bool:
    """
    Check if a task is overdue.

    A task is overdue if it has a due date in the past and is not
    in 'done' or 'backlog' status.

    Args:
        due_date: The task's due date (timezone-aware)
        status: The task's status

    Returns:
        True if task is overdue (due in past, not done/backlog), False otherwise
    """
    if not due_date or status in ('done', 'backlog'):
        return False
    return due_date < utc_now()


def date_range_for_upcoming(days: int) -> tuple[datetime, datetime]:
    """
    Calculate date range for upcoming tasks.

    Args:
        days: Number of days ahead

    Returns:
        Tuple of (now, future_date) as timezone-aware datetimes
    """
    now = utc_now()
    future_date = now + timedelta(days=days)
    return now, future_date
