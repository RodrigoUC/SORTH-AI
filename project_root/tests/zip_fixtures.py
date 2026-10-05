"""Real ZIP fixtures whose deliberately unsafe names survive on every host."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
import zipfile


def raw_zip_info(name, mode=0):
    # ZipInfo's constructor rewrites backslashes on Windows and truncates NULs.
    # Restore both fields so the local and central headers contain the raw name.
    member = zipfile.ZipInfo()
    member.filename = member.orig_filename = name
    member.external_attr = mode << 16
    return member


@contextmanager
def zip_separators(separator):
    """Exercise real ZipInfo normalization without changing the host filesystem."""
    # Patch only zipfile's os reference, never the process-wide os module.
    attributes = {**vars(zipfile.os), 'sep': separator,
                  'altsep': '/' if separator == '\\' else None}
    with patch.object(zipfile, 'os', SimpleNamespace(**attributes)):
        yield
