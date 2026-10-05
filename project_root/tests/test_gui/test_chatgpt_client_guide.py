"""Read-only field guidance separates local desktop execution from hosted MCP."""
import sys

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from src.gui.i18n import language_manager
from src.gui.mcp_client_help import McpClientHelp, client_configuration

COMMAND = [r'C:\Users\Renée 🧭 Name\SORTH\components\mcp\verified-build\SORTH-MCP.exe', '--serve']


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('frozen', [False, True], ids=['source', 'frozen'])
@pytest.mark.parametrize('verified', [False, True], ids=['unavailable', 'verified'])
def test_desktop_fields_require_verified_command_and_web_never_copies(locale, frozen, verified, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', frozen, raising=False)
    manager = language_manager()
    original = manager.language
    manager.set_language(locale, persist=False)
    dialog = McpClientHelp(COMMAND if verified else None, permission_enabled=False, pending_permission=True)
    try:
        dialog.resize(460, 420)
        dialog.show()
        dialog.client.setCurrentIndex(dialog.client.findData('chatgpt_desktop'))
        QApplication.processEvents()
        assert dialog.copy_button.isEnabled() == verified
        assert dialog.configuration.isVisible() == verified
        assert 'learn.chatgpt.com/docs/extend/mcp' in dialog.source.text()
        assert ('sin guardar' if locale == 'es' else 'unsaved') in dialog.permission_status.text()
        if verified:
            block = dialog.configuration.toPlainText()
            assert block == client_configuration('chatgpt_desktop', COMMAND)
            assert COMMAND[0] in block
            assert 'STDIO' in block and '--serve' in block
            assert ('ninguna requerida' if locale == 'es' else 'none required') in block
            assert ('no se ha probado' if locale == 'es' else 'not been tested') in dialog.instructions.text()
            assert ('mismo equipo' if locale == 'es' else 'same computer') in dialog.instructions.text()
            dialog.configuration.setFocus()
            QTest.keyClick(dialog.configuration, Qt.Key.Key_Tab)
            assert QApplication.focusWidget() == dialog.copy_button
            QTest.keyClick(dialog.copy_button, Qt.Key.Key_Space)
            assert QApplication.clipboard().text() == block
        else:
            assert not dialog.configuration.toPlainText()
            assert 'Python' in dialog.instructions.text()
        dialog.client.setCurrentIndex(dialog.client.findData('chatgpt'))
        assert dialog.configuration.isHidden()
        assert dialog.copy_button.isHidden() and not dialog.copy_button.isEnabled()
        assert not dialog.configuration.toPlainText()
        assert 'HTTPS' in dialog.instructions.text() and 'Secure MCP Tunnel' in dialog.instructions.text()
        assert 'STDIO' in dialog.instructions.text()
        close = dialog.buttons.button(QDialogButtonBox.StandardButton.Close)
        QApplication.processEvents()
        assert dialog.rect().contains(close.mapTo(dialog, close.rect().center()))
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)


def test_desktop_fields_live_translate_without_changing_path_or_permission():
    manager = language_manager()
    original = manager.language
    manager.set_language('es', persist=False)
    dialog = McpClientHelp(COMMAND, permission_enabled=True)
    dialog.client.setCurrentIndex(dialog.client.findData('chatgpt_desktop'))
    try:
        assert 'Comando para iniciar:' in dialog.configuration.toPlainText()
        cursor = dialog.configuration.document().find(COMMAND[0])
        assert not cursor.isNull()
        dialog.configuration.setTextCursor(cursor)
        manager.set_language('en', persist=False)
        assert dialog.configuration.textCursor().selectedText() == COMMAND[0]
        assert 'Command to start:' in dialog.configuration.toPlainText()
        assert COMMAND[0] in dialog.configuration.toPlainText()
        assert 'Saved local permission: on' in dialog.permission_status.text()
        assert dialog.client.currentText() == 'ChatGPT desktop (STDIO)'
        assert dialog.client.currentData() == 'chatgpt_desktop'
        manager.set_language('es', persist=False)
        assert 'Comando para iniciar:' in dialog.configuration.toPlainText()
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)


@pytest.mark.parametrize('command', [None, [], ['SORTH-MCP.exe', '--serve'], [COMMAND[0], '--probe'], [COMMAND[0]], [COMMAND[0], '--serve', 'extra']])
def test_desktop_serializer_rejects_non_companion_commands(command):
    with pytest.raises(ValueError):
        client_configuration('chatgpt_desktop', command)


@pytest.mark.parametrize('client', ['opencode', 'claude'])
def test_language_change_preserves_existing_json_selection(client):
    manager = language_manager()
    original = manager.language
    manager.set_language('es', persist=False)
    dialog = McpClientHelp(COMMAND, permission_enabled=True)
    dialog.client.setCurrentIndex(dialog.client.findData(client))
    dialog.setStyleSheet('QWidget { font-size: 20pt; }')
    dialog.resize(460, 420)
    dialog.show()
    QApplication.processEvents()
    try:
        cursor = dialog.configuration.textCursor()
        cursor.setPosition(5)
        cursor.setPosition(30, QTextCursor.MoveMode.KeepAnchor)
        dialog.configuration.setTextCursor(cursor)
        selected = cursor.selectedText()
        dialog._copy()
        dialog.configuration.verticalScrollBar().setValue(dialog.configuration.verticalScrollBar().maximum())
        dialog.configuration.horizontalScrollBar().setValue(dialog.configuration.horizontalScrollBar().maximum())
        scroll = (dialog.configuration.verticalScrollBar().value(), dialog.configuration.horizontalScrollBar().value())
        assert any(scroll)
        manager.set_language('en', persist=False)
        assert dialog.configuration.textCursor().selectedText() == selected
        assert dialog.configuration.textCursor().anchor() == 5
        assert dialog.configuration.textCursor().position() == 30
        for value, bar in zip(scroll, (dialog.configuration.verticalScrollBar(), dialog.configuration.horizontalScrollBar())):
            assert bar.value() == min(value, bar.maximum())
        assert dialog.copy_status.text()
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)
