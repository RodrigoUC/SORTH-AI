"""Opt-in management tools; atomic preferences never gate domain safety."""
from pathlib import Path
import json
import os
import tempfile

from PyQt6.QtCore import QIODevice, QSaveFile, QSettings
from ..application.mcp_preferences import default_path, read_record, preferences_lock, update_permission
from ..application.optional_features import Feature, FEATURES


class McpPreferenceConflict(OSError):
    """An external CLI changed the shared permission since this GUI read it."""


class FeaturePreferences:
    VERSION = 1
    MAX_BYTES = 65536

    def __init__(self, settings=None, path=None):
        # Existing language/motion QSettings are read-only here. An explicit INI
        # adapter gives tests and embedders an isolated sibling JSON destination.
        self.settings = settings if settings is not None else QSettings('SORTH', 'SORTH')
        self.path = Path(path) if path is not None else (
            Path(str(settings.fileName()) + '.features.json') if settings is not None else
            default_path())
        self.load_error = None
        self._record = {'version': self.VERSION, 'features': {}}
        try:
            self._record = self._read()
        except (OSError, ValueError, TypeError) as error:
            self.load_error = str(error)

    def _read(self):
        if self.path.exists():
            return read_record(self.path)
        # Force a real parse before trusting status; never setValue/sync this store.
        keys = self.settings.allKeys()
        if self.settings.status() != QSettings.Status.NoError:
            raise OSError('Existing preferences cannot be read safely')
        legacy = {}
        for key in keys:
            if key.startswith('features/') and key != 'features/mcp_server':
                value = self.settings.value(key)
                legacy[key[9:]] = value is True or (isinstance(value, str) and value.lower() == 'true')
        return {'version': self.VERSION, 'features': legacy}

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
        data = (json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
        if len(data) > self.MAX_BYTES:
            raise ValueError('Preferences exceed the supported size')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        output = QSaveFile(str(self.path))
        output.setDirectWriteFallback(False)
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError('Could not open atomic preference transaction')
        try:
            if output.write(data) != len(data):
                raise OSError('Could not write complete preferences')
            if not output.commit():
                raise OSError('Could not commit preferences')
        finally:
            # Cancels only an uncommitted temporary file, never the destination.
            output.cancelWriting()
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
