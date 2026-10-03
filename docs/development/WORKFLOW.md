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
python -m pytest -q tests/test_architecture tests/test_documentation
python -m pytest -q
```

Sin pantalla, define `QT_QPA_PLATFORM=offscreen` antes de pytest. En PowerShell:
`$env:QT_QPA_PLATFORM="offscreen"`; en Linux/macOS:
`export QT_QPA_PLATFORM=offscreen`. Además, ejecuta `git diff --check`.

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
