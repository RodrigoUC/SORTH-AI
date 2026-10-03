"""Optional presentation capabilities. Domain safety is never feature-gated."""
from dataclasses import dataclass
from PyQt6.QtCore import QSettings


@dataclass(frozen=True)
class Feature:
    key: str
    title: str
    description: str


# Register only implemented features. New entries are disabled until opted in.
FEATURES = (
    Feature('pinned_sessions', 'Sesiones fijadas',
            'Fijar o desfijar sesiones para conservar su ubicación al regenerar.'),
    Feature('project_scenarios', 'Proyectos y escenarios',
            'Guardar copias independientes, abrir escenarios y compararlos.'),
)


class FeaturePreferences:
    def __init__(self, settings=None):
        self.settings = settings if settings is not None else QSettings('SORTH', 'SORTH')

    def enabled(self, key):
        if key not in {feature.key for feature in FEATURES}:
            return False
        value = self.settings.value('features/' + key, False)
        # QSettings INI may return strings after restarting. Malformed values fail closed.
        return value is True or (isinstance(value, str) and value.lower() == 'true')

    def values(self):
        return {feature.key: self.enabled(feature.key) for feature in FEATURES}

    def save(self, values):
        known = {feature.key for feature in FEATURES}
        if set(values) != known or any(type(value) is not bool for value in values.values()):
            raise ValueError('Expected exactly the registered boolean feature preferences')
        before = self.values()
        for key, value in values.items():
            self.settings.setValue('features/' + key, value)
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            for key, value in before.items():
                self.settings.setValue('features/' + key, value)
            raise OSError('Could not persist feature preferences')
        # Unknown future keys are deliberately never removed or activated.
