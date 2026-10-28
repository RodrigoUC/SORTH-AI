"""Bounded application identity reads, independent of GUI and update transport."""
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from .json_records import decode_record


_VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')


class IdentityError(ValueError):
    """A missing or invalid identity must never become a guessed version."""


@dataclass(frozen=True)
class AppIdentity:
    """Source version, plus the exact build identifiers when running frozen."""

    version: str
    build_id: str | None = None
    source_commit: str | None = None


def read_identity(*, source_root: Path | None = None) -> AppIdentity:
    """Read VERSION in source or the frozen manifest, without network or fallback."""
    try:
        if getattr(sys, 'frozen', False):
            with (Path(sys._MEIPASS) / 'build-identity.json').open('rb') as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError('oversized identity')
            data = decode_record(raw)
            version = data['version']
            commit = data['source_commit']
            if (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)
                    or data['build_id'] != f'{version}-{commit[:12]}'):
                raise ValueError('mismatched identity')
            result = AppIdentity(version, data['build_id'], commit)
        else:
            root = source_root if source_root is not None else Path(__file__).resolve().parents[2]
            with (root / 'VERSION').open('rb') as stream:
                raw = stream.read(129)
            if len(raw) > 128:
                raise ValueError('oversized version')
            result = AppIdentity(raw.decode('ascii').strip())
        if (not isinstance(result.version, str) or len(result.version) > 128
                or not _VERSION.fullmatch(result.version)):
            raise ValueError('invalid version')
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        raise IdentityError('invalid_identity') from None
