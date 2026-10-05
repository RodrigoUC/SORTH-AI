"""Stable data identity and consistent visible branding are separate contracts."""
import sys
from pathlib import Path
from types import SimpleNamespace
from PyQt6.QtGui import QImage, QIcon
from tools.generate_demo_assets import icon_ico, icon_png
from tools.generate_installer_branding import wizard_png

ROOT = Path(__file__).resolve().parents[2]


def test_existing_icon_and_high_dpi_wizard_are_reproducible(_qt_application_lifetime):
    assert (ROOT / 'assets/sorth.ico').read_bytes() == icon_ico()
    assert (ROOT / 'installer/branding/mark.png').read_bytes() == icon_png(256)
    assert (ROOT / 'installer/branding/wizard.png').read_bytes() == wizard_png()
    assert QImage(str(ROOT / 'installer/branding/wizard.png')).width() == 656
    icon = QIcon(str(ROOT / 'assets/sorth.ico'))
    for size in (16, 24, 32, 48, 64, 128, 256):
        assert not icon.pixmap(size, size).isNull()


def test_windows_identity_remains_stable(monkeypatch):
    import ctypes
    import gui_app
    calls = []
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setattr(ctypes, 'windll', SimpleNamespace(shell32=SimpleNamespace(
        SetCurrentProcessExplicitAppUserModelID=calls.append)), raising=False)
    gui_app._set_windows_app_id()
    assert calls == ['SORTH.App']
    source = (ROOT / 'gui_app.py').read_text()
    assert 'app.setApplicationName("SORTH")' in source
    assert 'app.setOrganizationName("SORTH")' in source
    assert 'app.setApplicationDisplayName("SORTH-AI")' in source
    assert source.index('_set_windows_app_id()\n') < source.index('app = QApplication')


def test_setup_identity_keeps_review_isolation_and_explicit_icons():
    source = (ROOT / 'installer/sorth.iss').read_text()
    for setting in ('AppName=SORTH-AI', 'AppId=SORTH-{#BuildId}',
                    'SetupIconFile=..\\assets\\sorth.ico',
                    'VersionInfoProductName=SORTH-AI', 'DisableWelcomePage=no',
                    'VersionInfoProductVersion={#AppVersion}',
                    'VersionInfoProductTextVersion={#BuildId}',
                    'Name: "spanish"', 'Name: "english"', 'Flags: unchecked'):
        assert setting in source
    assert source.count('AppUserModelID: "SORTH.App"') == 2
    assert source.count('IconFilename: "{app}\\SORTH.exe"') == 2
    assert 'unsigned review' in source
    assert 'sin firma digital' in source
    assert '[Run]' not in source


def test_display_title_translations_are_consistent():
    from src.gui.locales.en import MESSAGES as en
    from src.gui.locales.es import MESSAGES as es
    title = 'SORTH-AI - Sistema de Organización de Horarios'
    assert es[title] == title
    assert en[title] == 'SORTH-AI - Academic Schedule Organizer'
