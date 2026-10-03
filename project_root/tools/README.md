# Herramientas del repositorio

Estos módulos sirven al desarrollo, la revisión y la distribución. El código de
producción en `src/` no debe importarlos. Ejecuta los comandos siguientes desde
`project_root`; los scripts con rutas absolutas también indican esa capacidad en
su ayuda. No se añade un gestor de tareas ni una dependencia nueva.

## Arquitectura

- `check_architecture.py`: guard AST de los límites del README.
  Comando: `python tools/check_architecture.py`; no importa ni ejecuta la app.

## Medición y diagnóstico

- `benchmark_scheduler.py`: motor de horarios con semilla y comprobación de invariantes.
  Comando: `python tools/benchmark_scheduler.py --repeats 5 --json`.
- `benchmark_excel_import.py`: importación y respuesta de la interfaz.
- `benchmark_schedule_filter.py`: filtrado del horario.
- `benchmark_editor_operations.py`: operaciones del editor con datos sintéticos.
- `recover_session.py`: recuperación explícita a un destino nuevo; no usar datos
  reales en capturas o artefactos públicos.
- `verify_cross_version_recovery.py`: comprobación de compatibilidad de recuperación.

## Datos y recursos de desarrollo

- `generate_demo_assets.py`: JSON sintético e iconos reproducibles. La procedencia
  está en [data/input/PROVENANCE.md](../data/input/PROVENANCE.md).
- `build_demo_workbook.mjs`: genera el Excel sintético a partir del JSON.
- `convert_png_to_ico.py`: conversión auxiliar histórica del icono. La generación
  reproducible oficial usa `generate_demo_assets.py`.
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
- `mcp_payload.py`, `frozen_mcp_smoke.py`: complemento opcional y comprobación empaquetada.
- `security_review.py`: controles estáticos y de dependencias.

Los puntos de entrada públicos `build_exe.ps1`, `build_mcp.ps1`, `gui_app.py`,
`main.py` y `mcp_app.py` permanecen en `project_root`. Los scripts históricos
`benchmark.py`, `convert_png_to_ico.py` y `generate_courses_json.py` son adaptadores
pequeños de compatibilidad; su implementación está en `tools/`.

Antes de mover una herramienta, revisa sus consumidores en `.github/workflows`,
PowerShell, archivos `.spec`, pruebas, documentación e importaciones Python.
Un cambio de carpeta debe conservar también la ejecución desde otra carpeta y
las rutas Windows, no solo los imports bajo pytest.
