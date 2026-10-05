# Flujo de desarrollo para un proyecto que crece

La arquitectura conserva las capas del README; consulta
[responsabilidades y dependencias](../architecture/ARCHITECTURE.md). Este flujo
busca cambios pequeños, trazables y verificables sin introducir un framework de
procesos ni nuevas dependencias.

## Del problema al cambio

1. Describe el resultado esperado, el caso que falla y los límites. Para cambios
   amplios, abre o enlaza un issue antes de mezclar implementación y rediseño.
2. Identifica la capa propietaria y todos los consumidores. Incluye GUI, CLI, MCP,
   pruebas, PowerShell, workflows y empaquetado cuando corresponda.
3. Crea una rama enfocada. Si hay trabajo paralelo, usa un worktree separado y
   acuerda archivos/contratos compartidos antes de moverlos.
4. Añade el caso de regresión o un contrato reproducible con datos sintéticos.
5. Implementa el mínimo cambio cohesivo. Mantén commits lógicos y mensajes como
   `refactor: ...`, `fix: ...`, `test: ...` o `docs: ...`; evita reformatear módulos
   ajenos al problema.
6. Verifica, documenta incompatibilidades y abre un PR en borrador hasta cerrar los
   controles aplicables. El mantenedor decide la integración y la publicación.

## Revisión de PRs dependientes

La mejora de finalización de exportación depende de [#44](https://github.com/RodrigoUC/SORTH-AI/pull/44).
Su PR usa `fix/course-editing-and-compact-calendar` como base para mostrar solo
su delta. Windows, seguridad y MCP permiten esa base exacta en `pull_request`
y mantienen el checkout del SHA de la cabeza; no se amplían los permisos ni se
cambian los controles. Primero se integra #44; después se revisa la base del PR
dependiente para dirigirlo a `main` y se vuelve a validar su commit exacto.
No se integra el PR dependiente en la rama de #44.

## Nombres y ubicación

- Python: módulos/funciones `snake_case`, clases `PascalCase`; conserva el idioma y
  estilo del módulo, con identificadores del dominio coherentes.
- Pruebas: `test_<comportamiento>.py`, bajo la capa o contrato correspondiente.
  Los tests de arquitectura y documentación tienen sus propias carpetas.
- Guías: contenido de usuario en `docs/user`; decisiones en `docs/architecture`;
  instrucciones de contribución y verificación en `docs/development`.
- Evidencia: rutas bajo `docs/evidence` o `docs/performance`, con escenario, versión,
  plataforma, comando y límites. Nunca incluyas datos de usuarios, bases o secretos.
- Recursos de terceros: conservar procedencia y avisos en `third_party`; no
  reescribir textos originales para que coincidan con el estilo del proyecto.

## Controles antes de pedir revisión

Prepara el entorno con [CONTRIBUTING.md](../../CONTRIBUTING.md). Desde `project_root`:

```sh
python -m pip check
python tools/check_architecture.py
python -m pytest -c pytest.ini --rootdir=. -q tests/test_architecture tests/test_documentation
```

Para la suite completa, sigue [los cuatro lotes](#suite-completa-en-cuatro-procesos)
de abajo. Además, ejecuta `git diff --check`.

- Dominio: resultado reproducible con semilla fija, restricciones e invariantes.
- Importación/exportación: mínimos, vacíos, inválidos, límites y reapertura del
  archivo exportado; una operación fallida conserva el estado previo.
- Persistencia: esquema anterior, fallo/rollback, recuperación y conservación de
  entradas. No basta comprobar el caso feliz.
- GUI: teclado, escala/tamaño mínimo, idiomas, repetición, cancelación, cierre y
  restauración. Las capturas offscreen no sustituyen la aceptación Windows.
- MCP: pruebas aisladas con su entorno/lock y sin contaminar las dependencias base;
  seguir [el contrato opcional](../../project_root/MCP_OPTIONAL.md).
- Build/rutas: construir el manual, comprobar archivos incluidos, shims y comandos
  anteriores; el build Windows real sigue siendo un control independiente.
- Seguridad/dependencias: aplicar [SECURITY_CHECKS.md](../SECURITY_CHECKS.md). Un
  movimiento debe actualizar las rutas de excepciones revisadas sin añadir nuevas
  supresiones ni alterar sus huellas de código.

En el PR distingue pruebas aprobadas, fallidas y no ejecutadas. No llames completa
la aceptación de una plataforma o release porque pasaron los tests de Python.

## Suite completa en cuatro procesos

Desde la raíz del repositorio, entra en `project_root` (`cd project_root`) y usa
el Python del entorno de desarrollo activado. Todos los comandos siguientes se
ejecutan allí: `-c pytest.ini --rootdir=.` fija la configuración y la raíz; `tests`
selecciona la colección completa. Para reproducir Windows, usa el entorno con
lock de [la guía de distribución](../release/WINDOWS_DISTRIBUTION.md) y sustituye
`python` por `.\.venv-build\Scripts\python.exe` en cada comando.

Antes de iniciar pytest sin pantalla, configura Qt según tu shell:

```sh
# Linux/macOS: Bash o shell POSIX
export QT_QPA_PLATFORM=offscreen
```

```powershell
# Windows: PowerShell
$env:QT_QPA_PLATFORM="offscreen"
$env:QT_QPA_FONTDIR=[Environment]::GetFolderPath([Environment+SpecialFolder]::Fonts)
```

Windows offscreen necesita las fuentes instaladas en esa carpeta; no las copies
ni redistribuyas. Esto no sustituye la revisión visual en un escritorio real.

Ejecuta primero la colección, después cada lote **en serie, en un proceso nuevo**
y finalmente el verificador. El plugin existente crea el directorio de informes si hace falta.
Las cadenas detienen la secuencia si falla un comando. No ejecutes sólo la última
línea para decidir si la suite pasó.

```sh
# Bash/POSIX: ejecutar como una sola cadena
python -m pytest -c pytest.ini --rootdir=. tests --collect-only -q -p tools.windows_test_batches --test-inventory=build/reports/tests-all-inventory.json &&
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=gui --test-inventory=build/reports/tests-gui-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-gui.xml &&
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=gui-layout --test-inventory=build/reports/tests-gui-layout-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-gui-layout.xml &&
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=theme-runtime --test-inventory=build/reports/tests-theme-runtime-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-theme-runtime.xml &&
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=remaining --test-inventory=build/reports/tests-remaining-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-remaining.xml &&
python tools/windows_test_batches.py --verify build/reports
```

```powershell
# PowerShell: ejecutar el bloque completo; comprobar cada proceso nativo
& {
python -m pytest -c pytest.ini --rootdir=. tests --collect-only -q -p tools.windows_test_batches --test-inventory=build/reports/tests-all-inventory.json
if ($LASTEXITCODE -ne 0) { throw "Falló la validación de tests (salida $LASTEXITCODE)." }
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=gui --test-inventory=build/reports/tests-gui-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-gui.xml
if ($LASTEXITCODE -ne 0) { throw "Falló la validación de tests (salida $LASTEXITCODE)." }
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=gui-layout --test-inventory=build/reports/tests-gui-layout-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-gui-layout.xml
if ($LASTEXITCODE -ne 0) { throw "Falló la validación de tests (salida $LASTEXITCODE)." }
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=theme-runtime --test-inventory=build/reports/tests-theme-runtime-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-theme-runtime.xml
if ($LASTEXITCODE -ne 0) { throw "Falló la validación de tests (salida $LASTEXITCODE)." }
python -m pytest -c pytest.ini --rootdir=. tests -vv -p tools.windows_test_batches --regression-batch=remaining --test-inventory=build/reports/tests-remaining-inventory.json -o faulthandler_timeout=120 --junitxml=build/reports/tests-remaining.xml
if ($LASTEXITCODE -ne 0) { throw "Falló la validación de tests (salida $LASTEXITCODE)." }
python tools/windows_test_batches.py --verify build/reports
if ($LASTEXITCODE -ne 0) { throw "Falló la validación de tests (salida $LASTEXITCODE)." }
}
```

La colección, los cuatro lotes y la verificación deben terminar con código 0.
Si falla un paso, conserva el error y corrígelo antes de repetir la secuencia
completa. Usa informes generados en esta misma ejecución, con el mismo commit,
entorno y configuración, sin filtros `-k`, `-m` ni selecciones de archivos
adicionales. No reutilices informes de una ejecución anterior como evidencia.

Cada lote recoge toda la suite y selecciona su partición; los tests deseleccionados
se ejecutan en otro lote. El verificador exige inventarios disjuntos cuya unión
coincida exactamente con la colección completa y rechaza duplicados, omisiones,
pruebas inesperadas o mal asignadas. Su éxito sólo comprueba cobertura de la
selección, no que las pruebas hayan pasado: los inventarios se escriben al
terminar la colección, antes de ejecutar los tests. Conserva también los resultados
y skips de cada lote; un skip no cuenta como aprobado.

Este es el procedimiento de aislamiento validado y coincide con los lotes del
[workflow Windows](../../.github/workflows/windows-review.yml), aunque el plugin
puede ejecutarse también en Linux/macOS. La ejecución monolítica de toda la suite
Qt en un único `pytest` puede sufrir cierres nativos intermitentes observados en
Linux/offscreen. El aislamiento no demuestra una corrección de ese problema de
ciclo de vida ni identifica su causa; tampoco certifica otras plataformas.

Para iterar sobre una prueba o módulo, sigue usando pytest directamente, por ejemplo:

```sh
python -m pytest -c pytest.ini --rootdir=. tests/test_scheduling/ -v --tb=short
```

Un resultado focalizado no equivale a una ejecución completa de los cuatro lotes.

## Revisión de PRs dependientes

La protección de resultados de fórmulas Excel depende de [#44](https://github.com/RodrigoUC/SORTH-AI/pull/44).
Su PR usa `fix/course-editing-and-compact-calendar` como base para mostrar solo
su delta. Windows, seguridad y MCP permiten esa base exacta en `pull_request`
y mantienen el checkout del SHA de la cabeza; no se amplían los permisos ni se
cambian los controles. Primero se integra #44; después se revisa la base del PR
dependiente para dirigirlo a `main` y se vuelve a validar su commit exacto.
No se integra el PR dependiente en la rama de #44.
