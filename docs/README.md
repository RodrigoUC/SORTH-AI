# Documentación de SORTH

Este índice reúne las guías que antes estaban dispersas en `project_root`.
Los comandos de aplicación, pruebas y compilación siguen ejecutándose desde
`project_root`, salvo que una guía indique otra ubicación.

## Usar la aplicación

- [Inicio rápido](QUICKSTART.md) y [manual completo](user/MANUAL_USUARIO.md)
- [Importar Excel](user/EXCEL_IMPORT_WORKFLOW.md)
- [Validación del horario](user/SCHEDULING_VALIDATION.md) y [recursos](user/RESOURCE_VALIDATION.md)
- [Exportar Excel/CSV](user/SCHEDULE_EXPORT_NOTES.md) y [PDF](user/PDF_EXPORT_NOTES.md)
- [Calidad del horario](user/QUALITY_METRICS.md)
- [Guardado y recuperación](user/SESSION_RECOVERY.md)
- [Funciones opcionales](user/OPTIONAL_FEATURES.md): [calendario](user/PROJECT_CALENDAR.md),
  [recursos docentes](user/OPTIONAL_RESOURCES.md), [escenarios](user/PROJECT_SCENARIOS.md),
  [edición reversible](user/REVERSIBLE_EDITS.md), [sesiones fijadas](user/PINNED_SESSIONS.md)
  y [opciones de ubicación](user/PLACEMENT_SUGGESTIONS.md)
- [Integración MCP opcional](../project_root/MCP_OPTIONAL.md)
- [Limitaciones conocidas](KNOWN_LIMITATIONS.md) y [privacidad](../PRIVACY.md)

## Desarrollar y verificar

- [Arquitectura del README](../project_root/README.md#arquitectura),
  [mapa y límites ejecutables](architecture/ARCHITECTURE.md),
  [decisión investigada](architecture/decisions/0001-modular-layers.md)
  y [flujo de desarrollo](development/WORKFLOW.md)
- [Contribuir](../CONTRIBUTING.md) y [diseño de la interfaz](../DESIGN.md)
- [Localización](development/LOCALIZATION.md), [accesibilidad](development/ACCESSIBILITY.md)
  y [notas de refinamiento](development/REFINEMENT_NOTES.md)
- [Operaciones del editor](performance/EDITOR_OPERATIONS.md) y [filtro del horario](performance/SCHEDULE_FILTER.md)
- [Decisiones y propuestas de diseño](design/)
- [Evidencia visual de importación](evidence/import/), [idiomas](evidence/localization/)
  y [validación](evidence/validation/)
- [Controles de seguridad](SECURITY_CHECKS.md)

Las capturas y mediciones son evidencia de una revisión concreta, no una promesa
de rendimiento ni una aprobación automática de la versión actual. Usa datos
sintéticos al añadir evidencia nueva.

## Compilar y distribuir

- [Distribución Windows](release/WINDOWS_DISTRIBUTION.md)
- [Checklist de release](RELEASING.md)
- [Aceptación nativa Windows](WINDOWS_RELEASE_ACCEPTANCE.md) y [registro](WINDOWS_ACCEPTANCE_RECORD.md)
- [Licencias](LICENSING_REVIEW.md) y [disponibilidad del código fuente](SOURCE_AVAILABILITY.md)

Las rutas históricas `project_root/MANUAL_USUARIO.md` y
`project_root/WINDOWS_DISTRIBUTION.md` conservan enlaces de compatibilidad.
Edita las guías canónicas en `docs/user` y `docs/release`; no dupliques su contenido.
`MCP_OPTIONAL.md` conserva su ubicación porque forma parte del contrato del
complemento y del empaquetado actual.
