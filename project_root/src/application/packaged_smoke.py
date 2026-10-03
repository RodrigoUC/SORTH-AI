"""Opt-in executable validation against bundled sample data and an isolated session.

Never opens or modifies the normal user's session or preferences. Results go to
the explicitly requested output directory; the CI launcher enforces its own timeout as well.
"""
import json
import os
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QSettings, QTimer

from ..gui.i18n import language_manager
from ..gui.locales import LANGUAGES
from ..infrastructure.excel_reader import ExcelReader
from ..infrastructure.schedule_exporter import ScheduleExporter
from ..infrastructure.session_repository import SessionRepository
from ..scheduling.time_model import TimeModel


def smoke_settings(output_dir):
    """Explicit INI adapter: named QSettings constructors ignore defaultFormat."""
    path = Path(output_dir).resolve() / 'smoke-profile' / 'interface.ini'
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    settings.setFallbacksEnabled(False)
    return settings


def configure_smoke_profile(output_dir, *, create):
    """Isolate JSON stores and explicit INI settings before constructing any UI.

    Never depend on setDefaultFormat/setPath for QSettings('SORTH', 'SORTH'):
    Qt documents that overload as NativeFormat, including the Windows registry.
    All smoke UI consumers receive the explicit adapter with fallbacks disabled.
    """
    profile = Path(output_dir).resolve() / 'smoke-profile'
    if create:
        profile.mkdir()  # A previous profile must never be reused as fresh evidence.
    elif not profile.is_dir():
        raise ValueError('Theme restart requires an existing synthetic smoke profile.')
    for key, folder in (('HOME', 'home'), ('USERPROFILE', 'home'),
                        ('LOCALAPPDATA', 'config'), ('APPDATA', 'config'),
                        ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data')):
        os.environ[key] = str(profile / folder)
    settings = smoke_settings(output_dir)
    from ..gui.theme_preferences import default_theme_path
    from .mcp_preferences import default_path
    paths = (Path(settings.fileName()), default_path(), default_theme_path())
    if not all(path.resolve().is_relative_to(profile) for path in paths):
        raise RuntimeError('Smoke preferences escaped the isolated profile.')
    if settings.format() != QSettings.Format.IniFormat or settings.fallbacksEnabled():
        raise RuntimeError('Smoke settings must use explicit INI format without fallbacks.')
    if create:
        settings.setValue('interface/language', 'es')
        settings.setValue('interface/reduced_motion', True)
        settings.sync()
        if settings.status() != QSettings.Status.NoError:
            raise RuntimeError('Could not seed isolated smoke preferences.')
        paths[1].parent.mkdir(parents=True, exist_ok=True)
        paths[1].write_text(json.dumps({'version': 1, 'features': {
            'mcp_server': False, 'import_diff_preview': True},
            'mcp_generation': '0' * 32}), encoding='utf-8')
    return paths


def create_smoke_window(output_dir, *, restore_session=True):
    """Inject only diagnostic constructors through existing settings adapters.

    MainWindow's production defaults stay unchanged. Its two constructor-local
    factories are replaced only while this synchronous smoke window is built;
    every reopened window and fresh-process probe uses the same explicit stores.
    """
    from ..gui import i18n, main_window
    from ..gui.features import FeaturePreferences
    from ..gui.motion import MotionController
    from .mcp_preferences import default_path
    configure_smoke_profile(output_dir, create=False)
    settings = smoke_settings(output_dir)
    if i18n._manager is None:
        i18n._manager = i18n.LanguageManager(settings=settings)
    elif Path(i18n._manager.settings.fileName()).resolve() != Path(settings.fileName()).resolve():
        raise RuntimeError('Smoke language manager already uses another preference store.')

    def motion(parent):
        return MotionController(parent, settings=settings)

    def features(unused=None):
        if unused is not None:
            raise RuntimeError('Unexpected smoke feature settings override.')
        return FeaturePreferences(settings=settings, path=default_path())

    original_motion, original_features = main_window.MotionController, main_window.FeaturePreferences
    try:
        main_window.MotionController, main_window.FeaturePreferences = motion, features
        return main_window.MainWindow(
            repo=SessionRepository(str(Path(output_dir) / 'smoke-session.db')),
            restore_session=restore_session)
    finally:
        main_window.MotionController, main_window.FeaturePreferences = original_motion, original_features


def smoke_preference_paths(window, output_dir):
    """Check the actual live consumers, not only the profile setup helper."""
    from ..gui.theme import theme_manager
    profile = Path(output_dir).resolve() / 'smoke-profile'
    stores = {'language': language_manager().settings,
              'motion': window._motion.settings,
              'feature_legacy': window._features.settings}
    paths = {name: Path(store.fileName()).resolve() for name, store in stores.items()}
    paths.update(features=window._features.path.resolve(),
                 appearance=theme_manager().preferences.path.resolve())
    if not all(path.is_relative_to(profile) for path in paths.values()):
        raise RuntimeError('Live smoke preferences escaped the isolated profile.')
    if any(store.format() != QSettings.Format.IniFormat or store.fallbacksEnabled()
           for store in stores.values()):
        raise RuntimeError('Live smoke settings must use explicit INI format without fallbacks.')
    return {name: str(path.relative_to(Path(output_dir).resolve())) for name, path in paths.items()}


def run_theme_probe(app, output_dir, phase):
    """Fresh-process startup verification; reports cannot impersonate frozen runs."""
    from ..gui import theme
    from ..gui.theme_preferences import default_theme_path
    from .packaged_workflow import smoke_preserved_files
    from .edit_history import fingerprint
    from ..gui.smoke_rendering import require_readable_text
    from PyQt6.QtWidgets import QApplication, QDialog
    report = {'ok': False, 'phase': phase, 'pid': os.getpid(),
              'frozen': bool(getattr(sys, 'frozen', False))}
    window = None
    try:
        configure_smoke_profile(output_dir, create=False)
        expected = json.loads((output_dir / 'theme-expected.json').read_text(encoding='utf-8'))
        before = smoke_preserved_files(output_dir)
        appearance = default_theme_path().read_bytes()
        def accept_restore():
            dialog = QApplication.activeModalWidget()
            if isinstance(dialog, QDialog):
                dialog.accept()
        QTimer.singleShot(0, accept_restore)
        window = create_smoke_window(output_dir)
        report['preference_paths'] = smoke_preference_paths(window, output_dir)
        if fingerprint(window._capture_edit_state()) != expected['domain']:
            raise RuntimeError('Fresh-process restore changed the saved schedule or inputs.')
        window.show()
        app.processEvents()
        manager = theme.theme_manager()
        if phase == 'custom':
            if (manager.current_key != 'custom' or manager.current.to_dict() != expected['theme']
                    or manager.recovery_issue or manager.startup_issue):
                raise RuntimeError('Custom appearance was not restored in the fresh process.')
        elif (manager.current_key != 'original' or not manager.recovery_issue
              or window._theme_recovery_notice.isHidden()):
            raise RuntimeError('Corrupt appearance did not show a preserved-file fallback.')
        if (language_manager().language != 'es' or not window._motion.reduced
                or window._features.enabled('mcp_server')
                or not window._features.enabled('import_diff_preview')):
            raise RuntimeError('Restart changed isolated language, motion or optional permissions.')
        from PyQt6.QtGui import QPalette
        if app.palette().color(QPalette.ColorRole.Window).name() != manager.current.colors['canvas'].lower():
            raise RuntimeError('Restart did not apply the saved/fallback native palette.')
        report['text_rendering'] = require_readable_text(window, output_dir, f'theme-{phase}-restart')
        if not window.grab().save(str(output_dir / f'theme-{phase}-restart.png')):
            raise RuntimeError('Could not capture the restarted appearance.')
        window.close()
        if (default_theme_path().read_bytes() != appearance
                or smoke_preserved_files(output_dir) != before):
            raise RuntimeError('Startup changed preferences or synthetic schedule data.')
        report.update(ok=True, selected=manager.current_key,
                      appearance_preserved=True, session_and_preferences_preserved=True)
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if window is not None:
            window.close()
    (output_dir / f'theme-{phase}-restart.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1


def run_smoke_test(app, output_dir: Path, *, theme_probe=None) -> int:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if theme_probe is not None:
        return run_theme_probe(app, output_dir, theme_probe)
    result_path = output_dir / 'smoke-result.json'
    if result_path.exists() or (output_dir / 'smoke-session.db').exists():
        raise ValueError('Use a fresh smoke-output directory to avoid stale results.')
    configure_smoke_profile(output_dir, create=True)
    source_root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    result = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'stages': [],
              'text_rendering': {}}
    from ..gui.smoke_rendering import require_readable_text
    if result['frozen']:
        result['build_identity'] = json.loads((source_root / 'build-identity.json').read_text(encoding='utf-8'))
    window = create_smoke_window(output_dir, restore_session=False)
    repo = window._repo
    result['preference_paths'] = smoke_preference_paths(window, output_dir)
    window.show()
    completed = False

    def finish(error=None):
        nonlocal completed
        if completed:
            return
        completed = True
        poll.stop()
        deadline.stop()
        if error:
            result['error'] = str(error)
        result['ok'] = error is None
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        if window._worker is None or not window._worker.isRunning():
            window.close()
        app.exit(0 if result['ok'] else 1)

    def check_done():
        if window._busy:
            return
        poll.stop()
        try:
            if not window.current_schedule:
                raise RuntimeError('The bundled sample produced no schedule.')
            assignments = window.current_schedule
            groups = window.current_groups
            if len(assignments) != len(groups):
                raise RuntimeError(f'Only {len(assignments)}/{len(groups)} sample groups assigned.')
            result.update(assigned=len(assignments), groups=len(groups), classrooms=len(window._classrooms))
            result['stages'].append('background_schedule')
            exporter = ScheduleExporter(TimeModel.default())
            exporter.to_excel(assignments, str(output_dir / 'schedule.xlsx'), groups=groups)
            exporter.to_csv(assignments, str(output_dir / 'schedule.csv'), groups=groups)
            if not all((output_dir / name).stat().st_size > 0 for name in ('schedule.xlsx', 'schedule.csv')):
                raise RuntimeError('An export is empty.')
            result['stages'].append('excel_csv_export')
            pdf_path = output_dir / 'schedule.pdf'
            exporter.to_pdf(assignments, str(pdf_path), groups=groups,
                            total_assigned=len(assignments), pending_count=0)
            if not pdf_path.read_bytes().startswith(b'%PDF-'):
                raise RuntimeError('PDF export did not produce a PDF document.')
            result['stages'].append('pdf_export')
            saved = repo.load_session()
            if saved['assignments'] != assignments:
                raise RuntimeError('SQLite roundtrip changed assignments.')
            result['stages'].append('sqlite_roundtrip')
            manager = language_manager()
            previous_language = manager.language
            try:
                for language, label in [('es', 'Generar horario'), ('en', 'Generate schedule')]:
                    manager.set_language(language, persist=False)
                    localized_pdf = output_dir / f'schedule-{language}.pdf'
                    exporter.to_pdf(assignments, str(localized_pdf), groups=groups,
                                    total_assigned=len(assignments), pending_count=0, labels=LANGUAGES[language].messages)
                    if not localized_pdf.read_bytes().startswith(b'%PDF-'):
                        raise RuntimeError('Localized PDF export failed.')
                    if window.btn_generate.text() != label or window.current_schedule != assignments:
                        raise RuntimeError('Language switching changed data or failed to translate controls.')
                    result['text_rendering'][language] = require_readable_text(window, output_dir, language)
                    if not window.grab().save(str(output_dir / f'schedule-{language}.png')):
                        raise RuntimeError('Could not capture the localized Qt window.')
                result['stages'].append('language_switch_es_en')
            finally:
                manager.set_language(previous_language, persist=False)
            if not window.grab().save(str(output_dir / 'schedule.png')):
                raise RuntimeError('Could not capture the rendered Qt window.')
            result['stages'].append('qt_render')
            from .packaged_workflow import verify_workflow
            verify_workflow(window, output_dir, result)
            from .packaged_workflow import verify_theme_workflow
            verify_theme_workflow(window, output_dir, result)
            finish()
        except Exception:
            finish(traceback.format_exc())

    def start():
        try:
            result['text_rendering']['startup'] = require_readable_text(window, output_dir, 'startup')
            from PyQt6.QtGui import QImage, QIcon
            if QIcon(str(source_root / 'assets/sorth.ico')).pixmap(32, 32).isNull():
                raise RuntimeError('Bundled application icon could not be decoded.')
            svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>'
            decoded = QImage.fromData(svg, b'SVG')
            png_path = output_dir / 'plugin-check.png'
            if decoded.isNull() or not decoded.save(str(png_path)) or QImage(str(png_path)).isNull():
                raise RuntimeError('SVG/PNG image plugins failed.')
            result['stages'].append('icon_svg_png_decode')
            sample = source_root / 'data/input/Cursos_Ejemplo.xlsx'
            reader = ExcelReader(str(sample))
            window._classrooms = reader.load_classrooms()
            window._classroom_course_map = reader.load_course_classroom_map(
                known_classrooms=set(window._classrooms))
            window.course_manager.load_courses_from_excel(reader.load_courses(known_classrooms=set(window._classrooms)))
            window.excel_path = str(sample)
            window.excel_path_label.setText(sample.name)
            result['stages'].append('bundled_excel_import')
            window._generate_schedule()
            # Avoid interactive error dialogs in this explicitly automated mode.
            window._worker.error.disconnect()
            window._worker.error.connect(lambda message: finish(message))
            poll.start(25)
            deadline.start(60000)
        except Exception:
            finish(traceback.format_exc())

    poll = QTimer()
    poll.timeout.connect(check_done)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(lambda: finish('Timed out after 60 seconds.'))
    QTimer.singleShot(0, start)
    code = app.exec()
    # A timed-out worker must not be destroyed while still executing. The CI
    # process launcher has a hard timeout for a genuinely wedged worker.
    if window._worker is not None:
        window._worker.wait()
    return code
