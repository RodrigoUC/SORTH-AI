"""Opt-in management tools; atomic preferences never gate domain safety."""
from pathlib import Path
import os
import tempfile

from .mcp_preferences import default_path, read_record, preferences_lock, update_permission, write_record
from ..application.optional_features import FEATURES


class McpPreferenceConflict(OSError):
    """An external CLI changed the shared permission since this GUI read it."""


class FeaturePreferences:
    VERSION = 1

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_path()
        self.load_error = None
        self._record = {'version': self.VERSION, 'features': {}}
        try:
            self._record = self._read()
        except (OSError, ValueError, TypeError) as error:
            self.load_error = str(error)

    def _read(self):
        return read_record(self.path)

    def refresh(self):
        try:
            self._record = self._read()
            self.load_error = None
        except (OSError, ValueError, TypeError) as error:
            self._record = {'version': self.VERSION, 'features': {}}
            self.load_error = str(error)

    def enabled(self, key):
        return key in {feature.key for feature in FEATURES} and self._record['features'].get(key) is True

    def values(self):
        return {feature.key: self.enabled(feature.key) for feature in FEATURES}

    def _write_atomic(self, record):
        write_record(self.path, record)
        self._record = record
        self.load_error = None

    def save(self, values):
        known = {feature.key for feature in FEATURES}
        if set(values) != known or any(type(value) is not bool for value in values.values()):
            raise ValueError('Expected exactly the registered boolean feature preferences')
        with preferences_lock(self.path):
            try:
                record = self._read()
            except (OSError, ValueError, TypeError) as error:
                self.load_error = str(error)
                raise OSError('Preferences require explicit recovery') from error
            if (record['features'].get('mcp_server', False) !=
                    self._record['features'].get('mcp_server', False)
                    or record.get('mcp_generation') != self._record.get('mcp_generation')):
                self._record = record
                self.load_error = None
                raise McpPreferenceConflict('MCP permission changed externally; review before saving')
            update_permission(record, values['mcp_server'])
            record['features'].update(values)
            self._write_atomic(record)

    def recover_defaults(self, preserved_values=None):
        """Explicit user-confirmed recovery; retain exact original bytes first."""
        defaults = {feature.key: False for feature in FEATURES}
        if preserved_values is not None:
            if (not set(preserved_values).issubset(defaults)
                    or any(type(v) is not bool for v in preserved_values.values())):
                raise ValueError('Invalid preserved preferences')
            defaults.update(preserved_values)
        with preferences_lock(self.path):
            backup = None
            if self.path.exists():
                raw = self.path.read_bytes()
                with tempfile.NamedTemporaryFile(mode='wb', prefix=self.path.name + '.preserved-',
                                                 suffix='.bak', dir=self.path.parent, delete=False) as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                    backup = Path(stream.name)
            record = {'version': self.VERSION, 'features': defaults}
            update_permission(record, defaults['mcp_server'])
            self._write_atomic(record)
            return backup
