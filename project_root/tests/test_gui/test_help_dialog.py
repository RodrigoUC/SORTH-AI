"""Test HelpDialog creation, sections, lifecycle, and safe interaction."""
from pathlib import Path
import pytest
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from src.gui.help_dialog import HelpDialog
from src.gui.main_window import MainWindow
from src.infrastructure.feature_preferences import FeaturePreferences
from src.infrastructure.session_repository import SessionRepository


@pytest.fixture
def window(tmp_path):
    owner = MainWindow(
        SessionRepository(str(tmp_path / 'session.db')),
        restore_session=False,
        feature_preferences=FeaturePreferences(path=tmp_path / 'features.json')
    )
    owner.show()
    QApplication.processEvents()
    yield owner
    owner.close()
    owner.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_help_dialog_sections_and_lifecycle(window):
    """HelpDialog initializes cleanly, toggles sections safely, and closes without crash."""
    dialog = HelpDialog(window)
    dialog.show()
    QApplication.processEvents()

    # All expected sections exist in the container
    expected_sections = {'workflow', 'excel', 'classrooms', 'generation', 'viewer', 'export', 'shortcuts'}
    assert set(dialog.sections.keys()) == expected_sections

    # Default section is 'workflow' and is visible
    assert dialog.sections['workflow'].isVisible()
    assert not dialog.sections['excel'].isVisible()

    # Switch to each section via combo box
    for i in range(dialog.section_selector.count()):
        dialog.section_selector.setCurrentIndex(i)
        QApplication.processEvents()
        active_key = dialog.section_selector.itemData(i)
        for key, widget in dialog.sections.items():
            assert widget.isVisible() == (key == active_key)

    # Close dialog via close button
    btn_box = dialog.findChild(QDialogButtonBox)
    assert btn_box is not None
    close_btn = btn_box.button(QDialogButtonBox.StandardButton.Close)
    assert close_btn is not None

    close_btn.click()
    QApplication.processEvents()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
