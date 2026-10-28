# SORTH 3.0.0: notas preparadas para revisión

Estado: **BORRADOR; versión sin publicar**. La fecha, el commit y los hashes de
distribución se completarán con la candidata final aprobada de `main`. Este
documento no autoriza una etiqueta ni una release.

## Cambios

- Se distinguen y restauran por separado las sesiones sin generar y los
  resultados generados vacíos; se validan las asignaciones persistidas.
- Se consolida la interfaz PyQt6 y se retiran implementaciones, adaptadores,
  lectores y scripts antiguos. Se unifican preferencias y traducciones ES/EN.
- Se conservan proyectos, escenarios, calendario, recursos, edición reversible,
  temas, exportaciones Excel/CSV/PDF e integración MCP opcional aislada.
- Se actualizan dependencias vulnerables, locks, hashes y avisos originales.
- Los PDF identifican la versión real de la aplicación en todas sus páginas,
  tanto desde fuente como en el ejecutable; se elimina el rótulo fijo 2.0.0.
- La preparación de fuentes admite los listados nativos de 7-Zip en Windows,
  preservando campos vacíos y los controles de rutas e integridad.
- El pipeline genera una candidata identificada por commit, ejecución, intento
  y hashes. La publicación permanece retenida hasta su aprobación explícita.

## Incompatibilidades y datos

Los formatos vigentes son sesión SQLite 5, catálogo 2 y metadatos de escenario
2. No se migran formatos anteriores. Un archivo incompatible se rechaza sin
modificarlo; conserve su copia y el binario que lo admite. Para un proyecto
nuevo, use el Excel de origen y los procedimientos del
[manual de recuperación](../user/SESSION_RECOVERY.md).

La importación acepta las hojas y encabezados documentados. No interpreta alias
de formatos anteriores. Las preferencias de funciones usan el almacén JSON
actual; no se importan automáticamente desde QSettings.

## Validación y límites

La [evidencia técnica](../evidence/release-readiness-3.0/REPORT.md) identifica una
candidata concreta; sus resultados no se trasladan a otro commit. Antes de
publicar deben completarse los gates de
[la primera release](FIRST_RELEASE_PIPELINE.md), incluida la aceptación manual.

El planificador usa heurísticas y puede dejar grupos sin asignar. Los resultados
necesitan revisión humana. Consulte las [limitaciones actuales](../KNOWN_LIMITATIONS.md)
y el [procedimiento de instalación](WINDOWS_DISTRIBUTION.md). Las candidatas de
revisión no están firmadas y no constituyen una publicación estable.
