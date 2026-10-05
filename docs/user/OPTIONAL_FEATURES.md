# Optional features

Use **Configuración / Settings** in the masthead to enable advanced tools. New
installations start with every optional feature disabled. Save applies changes;
Cancel or Escape keeps the previous preferences. The separately confirmed MCP
add-on preparation takes effect immediately and is not undone by Settings Cancel. Preferences survive restarting
on the same computer in a versioned `SORTH/optional-features.json` file under the
user configuration directory, separately from project and session databases.
Writes use `QSaveFile` with direct-write fallback disabled: only a complete atomic
commit changes disk and committed in-memory flags. Language/motion QSettings are
not written or migrated. Existing opt-in feature keys are read once as a fallback
when the new file does not exist; their original store remains untouched.

Currently implemented switches:

- **Avisar de actualizaciones al iniciar / Notify about updates at startup**:
  OFF by default. After an explicit Settings Save, checks stable official GitHub
  releases once at startup and shows an unobtrusive notice for a newer version.
  GitHub receives normal connection/IP metadata, never academic/session data.
  No automatic download or installation. The always-available manual **Check for
  updates** button does not commit pending preferences. See [Updates](UPDATES.md).

- **Permitir servidor MCP local / Allow local MCP server**: an explicit startup
  and per-tool-call permission, shared with the headless adapter. A bounded local
  check is required before enabling in the GUI. The separate **Prepare MCP add-on**
  action confirms before copying and checking the bundled Windows companion,
  without network or system Python installation. Missing bundles are reported
  explicitly. Preparation does not enable the feature, start a service, connect
  a model or open a listener. OFF also suppresses pending results; the client
  owns process shutdown. See [MCP configuration](../../project_root/MCP_OPTIONAL.md).

- **Herramientas de sesiones fijadas / Pinned session tools**: exposes pin/unpin controls in schedule
  tables. Disabling never removes existing pins or changes their placements.
  Pinned constraints remain enforced by generation, edits, manual placement,
  recovery and export validation. A confirmation explains this before hiding
  controls while pins exist. A visible notice and the F6 status reader explain
  how to enable controls again. Pin indicators remain visible.
- **Herramientas de proyectos y escenarios / Project and scenario tools**: exposes the project catalog.
  Disabling retains the working session and all independent saved scenarios. A
  notice identifies an existing catalog without opening or migrating it.

Course editing, ordinary generation, classroom restrictions, manual assignment,
quality summaries, export, accessibility controls, recovery and data-validation
protections remain available. Performance and safety are not optional switches.
MCP remains a separately prepared, explicitly started process. The client starts
it only after local permission is saved. Settings never installs dependencies
from the network, starts services or grants external access. The client guide
only displays copyable configuration and links; it does not modify other apps.

## Extension contract

`src/application/optional_features.py` contains the Qt-free feature registry;
`src/gui/features.py` provides the desktop atomic preference store. Each `Feature`
has a stable key, localized Spanish-source title and localized description.
The JSON stores a schema version and a `features` object. Only boolean values
are valid for known keys; unknown keys stay preserved but inactive. Malformed or
future-format files block ordinary saves without overwriting bytes. Settings
shows an explicit recovery action: it keeps an exact `.preserved-*.bak` copy of
an existing JSON file before resetting optional tools to off. Legacy QSettings
errors also block migration; explicit recovery leaves that source untouched.
Saving changes only registered keys, preserving future keys. Add a registry entry only together with
working controls and behavior, never as a placeholder for an unfinished feature.

New advanced tools must start off, retain domain data when disabled, explain any
remaining effects in the main-window notice, and never bypass safety rules.
Bulk editing and undo are documented in [Reversible edits](REVERSIBLE_EDITS.md);
placement suggestions in [Placement suggestions](PLACEMENT_SUGGESTIONS.md).
Import preview, calendar and resource parameters are described below.

## Verification

Offscreen PyQt6 tests cover defaults, malformed/unknown values, saved preferences
on a new window, cancellation, language switching, hidden controls, preserved pin
state and enforcement after disabling and restart. Linux screenshots verify the
960×640 main window and native settings dialog. Native Windows appearance and
screen-reader behavior still require platform acceptance.

- `import_diff_preview`: revisión de cursos/aulas añadidos, modificados y
  eliminados, restricciones y asignaciones antes de reemplazar una sesión.
  Desactivada inicialmente; ocultar esta revisión no desactiva validación,
  protección de fijaciones, carga en segundo plano ni cancelación segura.

## Calendario del proyecto

**Parámetros avanzados del calendario** comienza desactivado. Permite editar días
lectivos, horas y descansos con revisión previa. Ocultar esta herramienta nunca
restablece las reglas guardadas. Consulta [Calendario del proyecto](PROJECT_CALENDAR.md)
para la migración, validaciones, sesiones fijadas y alcance MCP.

## Parámetros de recursos (#14)

El registro ahora incluye `teacher`, `student_group` y `student`. A diferencia de
ocultar herramientas, apagarlos desactiva sus restricciones efectivas tras
confirmación y retirada del resultado actual. Conserva recursos y relaciones.
Los parámetros efectivos viajan con las sesiones/escenarios; las preferencias de
interfaz no pueden omitir la validación de un snapshot. Véase OPTIONAL_RESOURCES.md.

Consulta [Privacidad y datos locales](../../PRIVACY.md) para ubicaciones, datos
conservados, exportaciones, respaldos y diferencia entre desactivar y borrar.
