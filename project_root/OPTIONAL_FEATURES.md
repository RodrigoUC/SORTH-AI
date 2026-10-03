# Optional features

Use **Configuración / Settings** in the masthead to enable advanced tools. New
installations start with every optional feature disabled. Save applies changes;
Cancel or Escape keeps the previous preferences. Preferences survive restarting
on the same computer through `QSettings('SORTH', 'SORTH')`, separately from project
and session databases.

Currently implemented switches:

- **Sesiones fijadas / Pinned sessions**: exposes pin/unpin controls in schedule
  tables. Disabling never removes existing pins or changes their placements.
  Pinned constraints remain enforced by generation, edits, manual placement,
  recovery and export validation. A confirmation explains this before hiding
  controls while pins exist. A visible notice and the F6 status reader explain
  how to enable controls again. Pin indicators remain visible.
- **Proyectos y escenarios / Projects and scenarios**: exposes the project catalog.
  Disabling retains the working session and all independent saved scenarios. A
  notice identifies an existing catalog without opening or migrating it.

Course editing, ordinary generation, classroom restrictions, manual assignment,
quality summaries, export, accessibility controls, recovery and data-validation
protections remain available. Performance and safety are not optional switches.
MCP remains a separately installed, explicitly started process; this dialog does
not install dependencies, start services or grant external access.

## Extension contract

`src/gui/features.py` contains the implemented feature registry. Each `Feature`
has a stable key, localized Spanish-source title and localized description.
Preferences use `features/<key>`. Only actual booleans or QSettings' serialized
`true` are enabled; malformed and unknown keys fail closed. Saving changes only
registered keys, preserving future keys. Add a registry entry only together with
working controls and behavior, never as a placeholder for an unfinished feature.

New advanced tools must start off, retain domain data when disabled, explain any
remaining effects in the main-window notice, and never bypass safety rules.
Resources, bulk editing, undo, import preview, placement suggestions and calendar
configuration are not listed until their implementations are integrated.

## Verification

Offscreen PyQt6 tests cover defaults, malformed/unknown values, saved preferences
on a new window, cancellation, language switching, hidden controls, preserved pin
state and enforcement after disabling and restart. Linux screenshots verify the
960×640 main window and native settings dialog. Native Windows appearance and
screen-reader behavior still require platform acceptance.
