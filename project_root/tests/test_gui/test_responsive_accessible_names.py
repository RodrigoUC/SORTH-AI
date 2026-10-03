"""Automatic full captions follow text; explicit accessible names stay owned."""
import pytest
from PyQt6.QtWidgets import QWidget

from src.gui.i18n import Message, language_manager, msg
from src.gui.i18n_widgets import QCheckBox, QPushButton


@pytest.fixture
def spanish():
    manager = language_manager()
    previous = manager.language
    manager.set_language('es', persist=False)
    yield manager
    manager.set_language(previous, persist=False)


@pytest.mark.parametrize('kind', [QPushButton, QCheckBox])
def test_automatic_name_follows_message_literal_and_message_again(kind, spanish):
    button = kind(msg('Restaurar original'))
    try:
        button.wrapPresentationText(100)
        assert button.accessibleName() == 'Restaurar original'
        # A literal equal to a catalog key remains literal in both properties.
        button.setText('Restaurar original')
        assert 'setAccessibleName' not in button._messages
        spanish.set_language('en', persist=False)
        button.wrapPresentationText(100)
        assert button.text() == 'Restaurar original'
        assert button.accessibleName() == 'Restaurar original'
        button.setText('New literal caption')
        assert button.accessibleName() == 'New literal caption'
        button.setText(msg('Restaurar original'))
        assert button.accessibleName() == 'Restore original'
        button.wrapPresentationText(100)
        spanish.set_language('es', persist=False)
        button.wrapPresentationText(100)
        assert button.accessibleName() == 'Restaurar original'
        button.wrapPresentationText(1000)
        assert button.text() == button.accessibleName() == 'Restaurar original'
    finally:
        button.close()
        button.deleteLater()


@pytest.mark.parametrize('kind', [QPushButton, QCheckBox])
@pytest.mark.parametrize('when', ['before', 'after'])
@pytest.mark.parametrize('name', ['Explicit action name', msg('Código')])
def test_explicit_name_survives_wrapping_caption_and_locale_changes(kind, when, name, spanish):
    button = kind(msg('Restaurar original'))
    try:
        if when == 'after':
            button.wrapPresentationText(100)
        button.setAccessibleName(name)
        for source in (msg('Aplicar'), 'New literal caption', msg('Restaurar original')):
            button.setText(source)
            for locale in ('en', 'es'):
                spanish.set_language(locale, persist=False)
                button.wrapPresentationText(100)
                assert button.accessibleName() == (name.render() if isinstance(name, Message) else name)
    finally:
        button.close()
        button.deleteLater()


@pytest.mark.parametrize('kind', [QPushButton, QCheckBox])
def test_native_explicit_name_is_preserved_before_retranslation(kind, spanish):
    button = kind(msg('Restaurar original'))
    try:
        button.wrapPresentationText(100)
        QWidget.setAccessibleName(button, 'Native explicit name')
        spanish.set_language('en', persist=False)
        button.wrapPresentationText(100)
        assert button.accessibleName() == 'Native explicit name'
        assert 'setAccessibleName' not in button._messages
        button.setText('New literal caption')
        button.wrapPresentationText(100)
        assert button.accessibleName() == 'Native explicit name'
    finally:
        button.close()
        button.deleteLater()


@pytest.mark.parametrize('kind', [QPushButton, QCheckBox])
def test_explicit_same_text_name_is_not_mistaken_for_automatic_name(kind, spanish):
    button = kind(msg('Restaurar original'))
    try:
        button.wrapPresentationText(100)
        button.setAccessibleName('Restaurar original')
        spanish.set_language('en', persist=False)
        button.wrapPresentationText(100)
        assert button.accessibleName() == 'Restaurar original'
        assert button._presentation_text == 'Restore original'
    finally:
        button.close()
        button.deleteLater()


@pytest.mark.parametrize('kind', [QPushButton, QCheckBox])
def test_automatic_name_reuses_one_canonical_render(kind, spanish, monkeypatch):
    from src.gui import i18n_widgets
    button = kind(msg('Restaurar original'))
    try:
        button.wrapPresentationText(100)
        original = i18n_widgets._render
        calls = []
        def rendered(source):
            calls.append(source)
            return original(source)
        monkeypatch.setattr(i18n_widgets, '_render', rendered)
        button.retranslate()
        assert len(calls) == 1
        assert button.accessibleName() == 'Restaurar original'
        button.wrapPresentationText(100)
        assert len(calls) == 1
    finally:
        button.close()
        button.deleteLater()
