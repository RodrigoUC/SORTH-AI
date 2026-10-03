"""Bounded immutable workbook snapshots. No GUI or persistence dependencies."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os

from .excel_reader import ExcelReader, ExcelImport, ExcelImportError, ImportCancelled


@dataclass(frozen=True)
class ImportCandidate:
    path: str
    digest: bytes
    imported: ExcelImport


def read_candidate(path, cancelled, previous=None):
    """Re-read before acceptance; changed bytes are fully validated anew.

    Validation operates on captured bytes, never a file that can mutate under
    pandas. A subsequent filesystem edit cannot change the accepted snapshot.
    """
    def checkpoint():
        if cancelled():
            raise ImportCancelled()

    checkpoint()
    if Path(path).suffix.lower() != '.xlsx':
        raise ExcelImportError('Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).')
    try:
        return _read_candidate(path, cancelled, previous, checkpoint)
    except FileNotFoundError as error:
        raise ExcelImportError('No se encontró el archivo. Selecciónelo nuevamente.') from error
    except PermissionError as error:
        raise ExcelImportError('No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.') from error


def _read_candidate(path, cancelled, previous, checkpoint):
    chunks = []
    size = 0
    with open(path, 'rb') as source:
        before = os.fstat(source.fileno())
        while True:
            checkpoint()
            chunk = source.read(256 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > ExcelReader.MAX_FILE_BYTES:
                raise ExcelImportError('El libro supera el límite de importación. Divídalo en archivos más pequeños.')
            chunks.append(chunk)
        after = os.fstat(source.fileno())
        # Compare handle metadata with handle metadata. On Windows CPython
        # 3.12, path stat reports creation time as ctime while fstat reports
        # change time, so mixing those APIs rejects unchanged workbooks.
        # Reopening the name also detects replacement of the path while the
        # original handle remains open; keep every identity/change field.
        with open(path, 'rb') as current_source:
            current = os.fstat(current_source.fileno())
        identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise ExcelImportError('El archivo cambió mientras se leía. Selecciónelo nuevamente.')
    data = b''.join(chunks)
    digest = sha256(data).digest()
    checkpoint()
    if previous is not None and previous.digest == digest:
        return previous
    imported = ExcelReader(path, source_bytes=data, cancelled=cancelled).load_validated()
    checkpoint()
    return ImportCandidate(path, digest, imported)
