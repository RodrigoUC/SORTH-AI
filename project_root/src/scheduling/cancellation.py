"""Cooperative cancellation: callers discard the isolated in-progress state."""

class SchedulingCancelled(Exception):
    """Normal cancellation outcome, distinct from invalid data or engine errors."""


def checkpoint(cancelled=None):
    if cancelled is not None and cancelled():
        raise SchedulingCancelled()
