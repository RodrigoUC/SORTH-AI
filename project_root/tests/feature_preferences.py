"""Configure test feature flags through the production JSON contract."""
from pathlib import Path
from src.infrastructure.feature_preferences import FeaturePreferences


def enable_features(settings, *keys):
    """Enable named tools without relying on a retired QSettings feature store."""
    preferences = FeaturePreferences(path=Path(str((settings).fileName()) + '.features.json'))
    values = preferences.values()
    values.update({key: True for key in keys})
    preferences.save(values)
