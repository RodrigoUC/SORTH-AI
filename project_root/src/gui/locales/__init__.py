"""Language registry: adding a catalog never requires editing a view.

Catalog keys are immutable gettext-style Spanish message IDs plus named plural
IDs. Values, including Spanish copy, may be revised without renaming a key.
"""
from dataclasses import dataclass
from typing import Callable, Mapping

from . import es, en


@dataclass(frozen=True)
class Language:
    code: str
    native_name: str
    qt_locale: str
    messages: Mapping[str, str | Mapping[str, str]]
    qt_messages: Mapping[str, str]
    plural_rule: Callable[[int | float], str]
    direction: str = 'ltr'


def one_other(number):
    return 'one' if number == 1 else 'other'


DEFAULT_LANGUAGE = 'es'
LANGUAGES = {
    'es': Language('es', 'Español', 'es_CR', es.MESSAGES, es.QT_MESSAGES, one_other),
    'en': Language('en', 'English', 'en_US', en.MESSAGES, en.QT_MESSAGES, one_other),
}


def register_language(language):
    """Register a catalog before constructing the UI (e.g. an app extension).

    CLDR categories zero/one/two/few/many/other are supported by plural messages;
    the catalog must always provide other. The shipped UI has only been visually
    verified for left-to-right languages; RTL requires layout QA before shipping.
    """
    if not language.code or not language.native_name or language.direction not in ('ltr', 'rtl'):
        raise ValueError('Invalid language metadata')
    LANGUAGES[language.code] = language
