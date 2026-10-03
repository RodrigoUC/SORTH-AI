# SORTH UI theme contract v1

## Scope and compatibility

This versioned contract is owned by the Qt-free
`project_root/src/gui/theme_contract.py`. It validates data and does not activate a
theme, save settings, load assets or call a network service. The bundled wrapper
imports this exact module. The [JSON Schema](sorth-theme-v1.schema.json) is generated
from `theme_json_schema()` and checked for drift by the repository tests.

The contract alone does not add theme importing to older SORTH versions. Check the
target application's theme importer before describing a file as runtime-tested.
If there is no importer, deliver a contract-valid file and state that limitation.

## File format

- One UTF-8 JSON object without a BOM, at most 16,384 bytes. Suggested extension:
  `.sorth-theme.json`.
- Required: `schema_version` (the integer `1`, not `true` or `1.0`), `name`
  (1–64 characters), `mode` (`light` or `dark`), and `colors` (all 30 roles below).
- Optional: `description` (1–240 characters). No other top-level fields.
- Metadata must be trimmed plain text, without markup, control/format characters,
  surrogate characters or bidi overrides. Consumers must render it as PlainText.
- Every color is exactly `#RRGGBB`; hexadecimal letters may be upper or lower case.
  No alpha, shorthand, color functions, named colors, gradients or references.
- Missing/unknown roles, duplicate JSON keys, non-finite numbers and future schema
  versions are rejected. A partial theme is never merged with a built-in theme.
- Files contain no identity/resource fields, QSS/CSS, HTML, scripts, assets, fonts,
  URL references or provider credentials. A theme cannot change layout or permissions.

## Roles and intended rendering

| Group | Roles | Intended use |
| --- | --- | --- |
| Reading surfaces | `canvas`, `surface`, `surface_alt` | Window/dialog backdrop, controls/tables, alternating rows |
| Header | `header`, `header_hover`, `on_header`, `on_header_muted` | Masthead, table headers, tooltip/status bar, header-action states |
| Text | `text`, `muted`, `heading` | Body/control text, secondary/placeholder text, section headings |
| Structure | `border`, `divider` | Meaningful control/scrollbar boundary; decorative separator |
| Main action | `primary`, `primary_hover`, `primary_pressed`, `on_primary` | Filled action states with independent readable text |
| Soft action | `primary_soft`, `on_primary_soft` | Overview/time gutter, hover-tab foreground |
| Selection | `accent`, `on_accent`, `accent_soft` | Selected-tab/menu emphasis, input selection text, table/pressed-state fill |
| Focus | `focus` | Keyboard and course-selection outline |
| Inactive | `disabled`, `disabled_text` | Disabled control fill and text |
| Status | `success`, `success_soft`, `warning`, `warning_soft`, `danger`, `danger_soft` | Semantic state text/edge and its associated soft fill |

`header` replaces the old internal `navy` token. `heading` and `on_primary_soft`
separate the old navy's unrelated foreground uses, so dark backgrounds do not
force dark heading text. `on_accent` is independent of `surface`: selected input
text must remain readable when the reading surface is dark. `primary_hover` is a
filled-action state; use `on_primary_soft` for hover-tab text.

The legacy sort-arrow file paths are not color roles. The renderer owns trusted
icons and must color them consistently with header foregrounds without accepting
file paths from a theme. Updating a palette must not remove trusted resources.

## Contrast requirements

The canonical validator tests concrete text/boundary adjacencies. Its report
names the foreground, background, actual ratio, minimum and purpose. Use that
report instead of duplicating the pair list in an AI prompt or another validator.

- Normal text uses at least 4.5:1. SORTH keeps this threshold for disabled text as
  a readability baseline, even though inactive components are exempt under WCAG.
- Meaningful component boundaries and focus use at least 3:1 against their real
  neighboring surfaces. `divider` is decorative and is not required to reach 3:1.
- Course-card gutters and selection separators use the actual theme `surface`.
  Theme `focus` must contrast with its neighboring themed surfaces at 3:1.
- Ratios are compared before rounding. Revalidate changed dependent roles.

This borrows the numeric thresholds from
[WCAG text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
Color-token checks do not establish
[visible keyboard focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html),
focus geometry, non-color cues, screen-reader support or complete WCAG conformance.

## Academic identity and exports

`src/scheduling/course_style.py` owns stable course identities and the white-paper
palette, selected deterministically from a literal course code. Screen tones adapt
to the actual reading surface while keeping hue families, markers and labels.
Excel and PDF retain the stable printable palette. Do not hash or reassign a
course based on its position, room, filter, language or theme.

V1 does not export an interface's dark reading surface into print. Printable
course identity remains stable. An explicitly requested export-style change
needs its own shared rendering contract; it is not a reason to change course data
or silently recolor one output. Conflict/error labeling stays explicit and cannot
rely only on red or another hue.

## Runtime verification

If applying/previewing is requested and the target version has an importer:

1. Validate the saved file with the canonical wrapper. Record the app revision and
   exact file used. Import/preview through the supported UI; preserve the saved
   theme until the user applies the change, and verify Cancel/restore behavior.
2. Inspect representative controls, Settings, dialogs, tables, filters, empty
   states, hover/pressed/disabled states, text selection, semantic notices and
   keyboard focus. Check light/dark native palettes and custom-painted course
   cards, not just the root stylesheet. Check themed course separators and
   candidate-preview isolation.
3. Check large fonts and narrow windows, locale switching, restart persistence,
   reduced motion and readable errors for invalid imports. Ensure the course
   identity is unchanged in screen, reopened Excel and reopened PDF.
4. Report the checks actually run. Native OS file pickers and window chrome follow
   the OS; Linux/offscreen previews do not establish native Windows acceptance.

This verification checklist does not authorize unrequested application edits,
activation, preference writes or changes to built-in themes.
