"""Cooperative, process-lifetime ownership of the desktop working session.

Only the GUI entry point takes this lock. Repository callers and isolated test /
recovery candidates remain usable without importing or starting a GUI.
"""
from pathlib import Path

from PyQt6.QtCore import QLockFile


class SessionInUseError(OSError):
    """Ownership is unavailable or cannot be established safely."""


def acquire_gui_session_lock(session_path: Path) -> QLockFile:
    """Acquire before opening/migrating the repository; caller retains ownership.

    Resolve directory/file symlinks so aliases share a lock. Qt recovers locks
    belonging to dead local processes. Age alone never expires a live desktop
    session, malformed lock, or lock belonging to another host. No force-unlock
    path is offered. Local filesystems are required for the supported desktop
    workflow; this is not a distributed lock or protection from older binaries.
    """
    path = Path(session_path).resolve()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = QLockFile(str(path) + '.gui.lock')
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        raise SessionInUseError('Could not acquire desktop session ownership')
    return lock
