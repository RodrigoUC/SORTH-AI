"""Explicit, runtime-localizable presentation messages for the Qt interface.

Spanish source strings are stable catalog keys. Message arguments are rendered
without translating user data. Preferences are independent from session SQLite
and from the operating system locale. Missing translations fall back to Spanish.
"""
from string import Formatter
from collections.abc import Mapping
import weakref

from PyQt6.QtCore import QObject, QSettings, QSignalBlocker, QTranslator, QCoreApplication, QLocale, Qt, pyqtSignal
from PyQt6 import sip

from .locales import DEFAULT_LANGUAGE, LANGUAGES


def _render(value):
    return value.render() if isinstance(value, (Message, LocalizedNumber)) else value


class Message(str):
    """A string accepted by Qt, retaining its source and interpolation values."""

    def __new__(cls, source, parameters=None, parts=None, count=None):
        obj = super().__new__(cls, cls._format(source, parameters or {}, parts, count))
        obj.source = source
        obj.parameters = parameters or {}
        obj.parts = parts
        obj.count = count
        return obj

    @staticmethod
    def _format(source, parameters, parts, count):
        if parts is not None:
            return ''.join(str(_render(part)) for part in parts)
        manager = language_manager()
        language = LANGUAGES[manager.language]
        fallback = LANGUAGES[DEFAULT_LANGUAGE]

        def choose(catalog, rule):
            value = catalog.get(source)
            if isinstance(value, Mapping):
                return value.get(rule(count), value.get('other')) if count is not None else value.get('other')
            return value

        original = choose(fallback.messages, fallback.plural_rule) or source
        template = choose(language.messages, language.plural_rule) or original
        # Missing fields and malformed catalog formatting fall back safely.
        def fields(text):
            return {field for _, field, _, _ in Formatter().parse(text) if field}
        try:
            if fields(template) != fields(original):
                template = original
        except ValueError:
            template = original
        values = {key: _render(value) for key, value in parameters.items()}
        try:
            return template.format(**values)
        except (ValueError, KeyError, IndexError):
            return original.format(**values)

    def render(self):
        return self._format(self.source, self.parameters, self.parts, self.count)

    def __add__(self, other):
        return Message('', parts=(self, other))

    def __radd__(self, other):
        return Message('', parts=(other, self))


def join_messages(separator, messages):
    """Join marked fragments without freezing their current translated values."""
    result = Message('')
    for index, message in enumerate(messages):
        if index:
            result += separator
        result += message
    return result


def msg(source, **parameters):
    """Mark an application message. Do not pass course/classroom/file names."""
    return Message(source, parameters)


def plural(key, count, **parameters):
    """Select a catalog's plural category at render time, including after switching."""
    parameters.setdefault('n', LocalizedNumber(count))
    return Message(key, parameters, count=count)


class LocalizedNumber:
    def __init__(self, value, decimals=None):
        self.value = value
        self.decimals = decimals

    def render(self):
        locale = language_manager().locale
        if isinstance(self.value, int):
            return locale.toString(self.value)
        return locale.toString(self.value, 'f', 2 if self.decimals is None else self.decimals)




class _StandardTranslator(QTranslator):
    """Qt-owned standard labels; no extra .qm resources needed by PyInstaller."""

    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        return LANGUAGES[self.manager.language].qt_messages.get(sourceText, '')

    def isEmpty(self):
        return False


class LanguageManager(QObject):
    changed = pyqtSignal(str)

    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings('SORTH', 'SORTH')
        saved = self.settings.value('interface/language', DEFAULT_LANGUAGE)
        self.language = saved if saved in LANGUAGES else DEFAULT_LANGUAGE
        self._objects = {}
        self._translator = _StandardTranslator(self)
        self._translator_installed = False
        self._install_translator()

    @property
    def locale(self):
        return QLocale(LANGUAGES[self.language].qt_locale)

    def format_date(self, date, format=QLocale.FormatType.ShortFormat):
        return self.locale.toString(date, format)

    def format_time(self, time, format=QLocale.FormatType.ShortFormat):
        return self.locale.toString(time, format)

    def _install_translator(self):
        app = QCoreApplication.instance()
        if app is not None and not self._translator_installed:
            app.installTranslator(self._translator)
            self._translator_installed = True

    def _set_widget_locale(self, obj):
        if hasattr(obj, 'setLocale'):
            obj.setLocale(self.locale)
        if hasattr(obj, 'setLayoutDirection'):
            obj.setLayoutDirection(Qt.LayoutDirection.RightToLeft
                                   if LANGUAGES[self.language].direction == 'rtl'
                                   else Qt.LayoutDirection.LeftToRight)

    def register(self, obj):
        self._install_translator()
        self._set_widget_locale(obj)
        identity = id(obj)
        self._objects[identity] = weakref.ref(obj, lambda _: self._objects.pop(identity, None))

    def set_language(self, language, persist=True):
        language = language if language in LANGUAGES else DEFAULT_LANGUAGE
        if persist:
            self.settings.setValue('interface/language', language)
            self.settings.sync()
        if language == self.language:
            return
        self.language = language
        app = QCoreApplication.instance()
        if app is not None:
            # Qt sends LanguageChange to its own standard dialogs/controls.
            app.removeTranslator(self._translator)
            app.installTranslator(self._translator)
            self._translator_installed = True
        # Block Qt text-change signals so combo selection/filtering and user
        # input do not mutate as a side effect of replacing display labels.
        for reference in list(self._objects.values()):
            obj = reference()
            if obj is None or sip.isdeleted(obj):
                continue
            blocker = QSignalBlocker(obj) if isinstance(obj, QObject) else None
            try:
                self._set_widget_locale(obj)
                obj.retranslate()
            finally:
                del blocker
        self.changed.emit(language)


_manager = None


def language_manager():
    global _manager
    if _manager is None or sip.isdeleted(_manager):
        _manager = LanguageManager()
    return _manager
