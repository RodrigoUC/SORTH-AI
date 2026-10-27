# SORTH-AI - Sistema de Organización de Horarios

## Descargar e instalar en Windows

El instalador se genera en **GitHub Actions**, no se guarda como `.exe` en la
raíz del código. Actualmente son compilaciones de revisión **sin firma digital**;
no hay una release pública estable anunciada aquí.

1. Abre [Windows review build](https://github.com/RodrigoUC/SORTH-AI/actions/workflows/windows-review.yml)
   y elige una ejecución **correcta de `main`**, comprobando su commit.
2. En **Artifacts**, descarga `SORTH-windows-review-…` (GitHub puede pedir iniciar
   sesión). Los artefactos caducan a los siete días; una ejecución antigua puede
   no ofrecer descarga.
3. Extrae el ZIP del artefacto. El instalador es
   `SORTH-<versión>-<commit>-windows-x64-unsigned-setup.exe`; `SHA256SUMS.txt` permite
   comprobar que la descarga coincide con esa compilación. El hash no identifica
   por sí solo al editor ni garantiza seguridad.
4. El asistente instala sólo para tu usuario, añade **SORTH-AI** al menú Inicio y
   permite elegir un acceso directo al escritorio. Cada compilación conserva su
   identificador para distinguirla de otras versiones de revisión.

Si Windows bloquea el archivo, conserva el mensaje y consulta la
[guía de distribución y firma](docs/release/WINDOWS_DISTRIBUTION.md).
Cambiar los iconos o el nombre no elimina SmartScreen. Si sólo quieres el código,
consulta [instalación para desarrollo](project_root/README.md).

## Comunidad y estado del proyecto

El código propio de SORTH está bajo [GPL-3.0-only](LICENSING.md). Los recursos de terceros conservan sus licencias; la revisión de módulos nativos y del paquete final sigue pendiente antes de una release pública.

- [Contribuir](CONTRIBUTING.md) · [Soporte por Issues](SUPPORT.md) · [Seguridad](SECURITY.md)
- [Guía de convivencia](CODE_OF_CONDUCT.md) · [Créditos](CREDITS.md) · [Revisión de licencias](docs/LICENSING_REVIEW.md)
- [Documentación](docs/README.md) · [Inicio rápido](docs/QUICKSTART.md) · [Privacidad](PRIVACY.md)
- [Apariencia y temas propios](docs/user/APPEARANCE.md)
- [Limitaciones conocidas](docs/KNOWN_LIMITATIONS.md) · [Checklist de releases](docs/RELEASING.md)
- [Instalar y ejecutar desde código](project_root/README.md) · [Distribución Windows](docs/release/WINDOWS_DISTRIBUTION.md)

Los reportes pueden escribirse en español o inglés. Utiliza datos sintéticos: los issues son públicos.

## Funcionalidades actuales

SORTH es una aplicación de escritorio para organizar horarios académicos. Importa
Excel, genera propuestas, permite revisarlas y editarlas y exporta Excel, CSV o PDF.
La planificación contempla aulas, capacidad, laboratorios, restricciones y recursos
explícitamente asociados. Su heurística puede dejar sesiones pendientes; los
resultados requieren revisión humana y no garantizan optimalidad.

Las herramientas opcionales incluyen sesiones fijadas, calendario, docentes y
grupos, sugerencias de ubicación, escenarios, edición en lote y deshacer/rehacer.
MCP permite propuestas locales mediante un cliente configurado por separado; las
actualizaciones se consultan con permiso y no se instalan silenciosamente.

La versión de desarrollo es **3.0.0**. Conserva únicamente los formatos actuales y
rechaza bases antiguas sin convertirlas ni sobrescribirlas. Consulte
[los cambios y sus incompatibilidades](docs/evidence/consolidation-3.0/REPORT.md).

## Instalación y uso

La [guía técnica de la aplicación](project_root/README.md) es la fuente de instalación,
formato Excel y funcionamiento del motor. El [inicio rápido](docs/QUICKSTART.md)
y el [manual](docs/user/MANUAL_USUARIO.md) explican el recorrido de uso.

El ejemplo incluido tiene 8 aulas, 12 cursos, 36 grupos y 42 sesiones sintéticas.
Su origen y regeneración están en [procedencia de los datos](project_root/data/input/PROVENANCE.md).

## Arquitectura del Sistema

El dominio y los casos de uso permanecen independientes de Qt, archivos y red.
Los adaptadores de infraestructura y presentación se conectan desde composición.
Consulte [responsabilidades y dependencias](docs/architecture/ARCHITECTURE.md)
y [contribución y pruebas](CONTRIBUTING.md).

## Guías por función

- [Importar Excel](docs/user/EXCEL_IMPORT_WORKFLOW.md).
- [Validación y limitaciones](docs/KNOWN_LIMITATIONS.md).
- [Recuperar sesiones](docs/user/SESSION_RECOVERY.md) y [proyectos y escenarios](docs/user/PROJECT_SCENARIOS.md).
- [Calidad del horario](docs/user/QUALITY_METRICS.md), [Excel/CSV](docs/user/SCHEDULE_EXPORT_NOTES.md) y [PDF](docs/user/PDF_EXPORT_NOTES.md).
- [MCP opcional](project_root/MCP_OPTIONAL.md) y [privacidad](PRIVACY.md).
- [Actualizaciones](docs/user/UPDATES.md), [distribución Windows](docs/release/WINDOWS_DISTRIBUTION.md) y [preparar una release](docs/RELEASING.md).
