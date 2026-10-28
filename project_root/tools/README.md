# Herramientas del repositorio

Estos módulos sirven al desarrollo, la revisión y la distribución. El código de
producción en `src/` no debe importarlos. Ejecuta los comandos siguientes desde
`project_root`; los scripts con rutas absolutas también indican esa capacidad en
su ayuda. No se añade un gestor de tareas ni una dependencia nueva.

## Arquitectura

- `check_architecture.py`: guard AST de los límites del README.
  Comando: `python tools/check_architecture.py`; no importa ni ejecuta la app.
- `windows_test_batches.py`: divide la suite en cuatro procesos seriales:
  `gui`, `gui-layout`, `theme-runtime` y `remaining`. La colección completa y
  `python tools/windows_test_batches.py --verify build/reports` comprueban que
  la unión de IDs sea exacta, sin duplicados ni omisiones. Consulte el
  [procedimiento completo](../../docs/development/WORKFLOW.md#suite-completa-en-cuatro-procesos).

## Medición y diagnóstico

- `benchmark_scheduler.py`: motor de horarios con semilla y comprobación de invariantes.
  Comando: `python tools/benchmark_scheduler.py --repeats 5 --json`.
- `benchmark_excel_import.py`: importación y respuesta de la interfaz.
- `benchmark_schedule_filter.py`: filtrado del horario.
- `benchmark_editor_operations.py`: operaciones del editor con datos sintéticos.
- `recover_session.py`: recuperación explícita a un destino nuevo; no usar datos
  reales en capturas o artefactos públicos.

## Datos y recursos de desarrollo

- `generate_demo_assets.py`: JSON sintético e iconos reproducibles. La procedencia
  está en [data/input/PROVENANCE.md](../data/input/PROVENANCE.md).
- `build_demo_workbook.mjs`: genera el Excel sintético a partir del JSON.
- `fonts/`: recurso tipográfico del generador de manual, con su licencia.

## Documentación y distribución

- `build_manual.py`: genera el manual desde [la fuente canónica](../../docs/user/MANUAL_USUARIO.md)
  hacia `build/docs/MANUAL_USUARIO.pdf`.
- `build_identity.py`, `package_windows.py`: identidad de compilación y ZIP de revisión.
- `build_installer.ps1`, `test_installer.ps1`, `installer_test_helpers.ps1`:
  creación y comprobación del instalador.
- `collect_windows_acceptance.ps1`: evidencia de aceptación Windows.
- `lock_windows.py`, `collect_license_notices.py`: locks e inventarios/avisos.
- `prune_unused_qt_pdf.py`: comprobación del conjunto nativo distribuido.
- `prepare_release_sources.py`: fuente de terceros y evidencia del proveedor, con
  descargas limitadas por URL/tamaño/SHA-256 y salida reproducible. Requiere el
  `7z`/`7zz` del sistema; no instala ni ejecuta código descargado.
  `python tools/prepare_release_sources.py --output build/release-sources/THIRD-PARTY-SOURCES.tar.gz`.
  Lee [alcance y límites](../../third_party/RELEASE_SOURCES.txt); preparar este
  archivo no verifica la identidad del binario final ni autoriza publicación.
- `mcp_payload.py`, `frozen_mcp_smoke.py`: complemento opcional y comprobación empaquetada.
- `security_review.py`: controles estáticos y de dependencias.

Los puntos de entrada públicos `build_exe.ps1`, `build_mcp.ps1`, `gui_app.py`,
`main.py` y `mcp_app.py` permanecen en `project_root`. Las herramientas se ejecutan
directamente desde `tools/`; no hay scripts de reenvío en la raíz.

Antes de mover una herramienta, revisa sus consumidores en `.github/workflows`,
PowerShell, archivos `.spec`, pruebas, documentación e importaciones Python.
Un cambio de carpeta debe conservar también la ejecución desde otra carpeta y
las rutas Windows, no solo los imports bajo pytest.
