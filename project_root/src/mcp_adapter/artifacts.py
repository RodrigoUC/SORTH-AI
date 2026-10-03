"""Process-local XLSX resources: opaque names, bounded retention, no file access."""
from dataclasses import dataclass
from hashlib import sha256
import secrets
import time

from ..application.preview_contract import ContractError, obj, integer, OUTPUT_SCHEMA, ERROR_SCHEMA
from ..application.preview_clarification import NEEDS_INPUT_SCHEMA

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
MAX_XLSX_BYTES = 524_288
MAX_EXPORT_OUTPUT_BYTES = 1_048_576
MAX_ARTIFACTS = 4
ARTIFACT_TTL_SECONDS = 300

ARTIFACT_SCHEMA = obj({
    'uri': {'type': 'string', 'maxLength': 160},
    'name': {'type': 'string', 'enum': ['sorth-preview.xlsx']},
    'mime_type': {'type': 'string', 'enum': [XLSX_MIME]},
    'size_bytes': integer(1, MAX_XLSX_BYTES),
    'sha256': {'type': 'string', 'minLength': 64, 'maxLength': 64},
    'expires_in_seconds': integer(1, ARTIFACT_TTL_SECONDS),
    'delivery': {'type': 'string', 'enum': ['mcp_resource']},
    'message': {'type': 'string', 'maxLength': 512},
})
EXPORT_OUTPUT_SCHEMA = {'type': 'object', 'oneOf': [
    obj({'preview': OUTPUT_SCHEMA, 'artifact': ARTIFACT_SCHEMA}), NEEDS_INPUT_SCHEMA, ERROR_SCHEMA,
]}


@dataclass(frozen=True)
class Artifact:
    uri: str
    data: bytes
    generation: object
    expires: float

    def metadata(self):
        return {'uri': self.uri, 'name': 'sorth-preview.xlsx', 'mime_type': XLSX_MIME,
                'size_bytes': len(self.data), 'sha256': sha256(self.data).hexdigest(),
                'expires_in_seconds': ARTIFACT_TTL_SECONDS, 'delivery': 'mcp_resource',
                'message': 'Read this MCP resource in this connection within five minutes. Download/attachment rendering depends on the host; do not claim delivery until the host has saved or attached the bytes. No local file or public URL was created.'}


class ArtifactStore:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._items = {}

    def _prune(self, generation):
        now = self._clock()
        self._items = {uri: item for uri, item in self._items.items()
                       if generation is not None and item.generation == generation and item.expires > now}

    def add(self, data, generation):
        self._prune(generation)
        if generation is None:
            raise ContractError('MCP_DISABLED', 'server', 'MCP is disabled; the file was discarded.')
        if not isinstance(data, bytes) or not 0 < len(data) <= MAX_XLSX_BYTES:
            raise ContractError('OUTPUT_LIMIT', 'result', 'Excel exceeds the 512 KiB limit. Reduce the request and retry.')
        while len(self._items) >= MAX_ARTIFACTS:
            del self._items[next(iter(self._items))]
        uri = f'sorth-xlsx://exports/{secrets.token_urlsafe(24)}/sorth-preview.xlsx'
        item = Artifact(uri, data, generation, self._clock() + ARTIFACT_TTL_SECONDS)
        self._items[uri] = item
        return item

    def list(self, generation):
        self._prune(generation)
        return tuple(self._items.values())

    def read(self, uri, generation):
        self._prune(generation)
        if generation is None:
            raise ContractError('MCP_DISABLED', 'resource', 'MCP is disabled; no resource is available.')
        if uri not in self._items:
            raise ContractError('RESOURCE_UNAVAILABLE', 'resource', 'Resource unknown, expired, evicted or revoked. Generate the Excel again if authorized.')
        return self._items[uri]
