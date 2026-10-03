"""Opt-in management tools; atomic preferences never gate domain safety."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile

from PyQt6.QtCore import QIODevice, QSaveFile, QSettings, QStandardPaths


@dataclass(frozen=True)
class Feature:
    key: str
    title: str
    description: str


FEATURES = (
    Feature('import_diff_preview', 'Vista previa de cambios del Excel',
            'Revisar cursos, aulas, restricciones y asignaciones antes de reemplazar la sesión.'),
    Feature('pinned_sessions', 'Herramientas de sesiones fijadas',
            'Mostrar controles para fijar o desfijar. Las fijaciones guardadas siempre se respetan.'),
    Feature('project_scenarios', 'Herramientas de proyectos y escenarios',
            'Mostrar controles para guardar, abrir y comparar copias independientes.'),
)


class FeaturePreferences:
    VERSION = 1
    MAX_BYTES = 65536

    def __init__(self, settings=None, path=None):
        # Existing language/motion QSettings are read-only here. An explicit INI
        # adapter gives tests and embedders an isolated sibling JSON destination.
        self.settings = settings if settings is not None else QSettings('SORTH', 'SORTH')
        self.path = Path(path) if path is not None else (
            Path(str(settings.fileName()) + '.features.json') if settings is not None else
            Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericConfigLocation))
            / 'SORTH' / 'optional-features.json')
        self.load_error = None
        self._record = {'version': self.VERSION, 'features': {}}
        try:
            self._record = self._read()
        except (OSError, ValueError, TypeError) as error:
            self.load_error = str(error)

    @staticmethod
    def _unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate preference key')
            result[key] = value
        return result

    def _read(self):
        if self.path.exists():
            with self.path.open('rb') as stream:
                raw = stream.read(self.MAX_BYTES + 1)
            if len(raw) > self.MAX_BYTES:
                raise ValueError('Preferences exceed the supported size')
            record = json.loads(raw, object_pairs_hook=self._unique_object)
            if (not isinstance(record, dict) or type(record.get('version')) is not int
                    or record['version'] != self.VERSION or not isinstance(record.get('features'), dict)):
                raise ValueError('Unsupported or damaged preferences')
            if any(type(record['features'].get(feature.key, False)) is not bool for feature in FEATURES):
                raise ValueError('Invalid feature preference')
            return record
        # Force a real parse before trusting status; never setValue/sync this store.
        keys = self.settings.allKeys()
        if self.settings.status() != QSettings.Status.NoError:
            raise OSError('Existing preferences cannot be read safely')
        legacy = {}
        for key in keys:
            if key.startswith('features/'):
                value = self.settings.value(key)
                legacy[key[9:]] = value is True or (isinstance(value, str) and value.lower() == 'true')
        return {'version': self.VERSION, 'features': legacy}

    def enabled(self, key):
        return key in {feature.key for feature in FEATURES} and self._record['features'].get(key) is True

    def values(self):
        return {feature.key: self.enabled(feature.key) for feature in FEATURES}

    def _write_atomic(self, record):
        data = (json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
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
        try:
            record = self._read()
        except (OSError, ValueError, TypeError) as error:
            self.load_error = str(error)
            raise OSError('Preferences require explicit recovery') from error
        record['features'].update(values)
        self._write_atomic(record)

    def recover_defaults(self):
        """Explicit user-confirmed recovery; retain exact original bytes first."""
        backup = None
        if self.path.exists():
            raw = self.path.read_bytes()
            with tempfile.NamedTemporaryFile(mode='wb', prefix=self.path.name + '.preserved-',
                                             suffix='.bak', dir=self.path.parent, delete=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                backup = Path(stream.name)
        self._write_atomic({'version': self.VERSION, 'features': {feature.key: False for feature in FEATURES}})
        return backup
