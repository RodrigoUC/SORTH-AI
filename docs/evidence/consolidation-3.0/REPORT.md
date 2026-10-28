# Consolidación de SORTH 3.0.0

Fecha: 27 de octubre de 2026. Revisión local sobre la base `7ff09f8`.

## Alcance

Corregir los defectos de restauración, retirar implementaciones y formatos antiguos,
consolidar responsabilidades y comprobar las funcionalidades vigentes. No se ha
publicado una release. Los cambios se integran mediante commits y una rama de revisión.

## Cambios verificables

| Requisito | Implementación y evidencia |
| --- | --- |
| Conservar estados sin generar y generado vacío | Esquema SQLite 5 con `schedule_present`; pruebas `test_current_session_contract.py` y `test_result_presence.py` |
| No mantener formatos antiguos | Rechazo sin mutación de sesiones fuera de esquema 5, catálogos fuera de esquema 2 y metadatos fuera de formato 2 |
| Una interfaz vigente | Eliminada la interfaz Tkinter; PyQt6 conserva las funciones actuales |
| Una fuente por responsabilidad | Eliminados lector JSON antiguo, asignaciones por bloques, escritor vacío, scripts de reenvío, spec de build obsoleto, copias PNG y configuración JSON redundante |
| Dependencias hacia el interior | Aplicación sin imports de infraestructura, Qt o composición; guard AST comprueba dirección y módulos existentes |
| Ventana principal con responsabilidades delimitadas | `ImportController`, `ExportController` y `SessionController`; sin métodos de reenvío de las rutas retiradas |
| Preferencias consolidadas | JSON único, `write_record` atómico compartido por GUI/CLI e inyección de `FeaturePreferences` en la ventana |
| Restauración independiente del Excel | Mapa de sugerencias derivado de cursos aceptados; no se reimporta el archivo original |
| Catálogos conservados al fallar | Apertura de catálogos actuales sin DDL ni reparación implícita de tablas faltantes |
| Traducciones sin sobrescrituras | Un diccionario por catálogo ES/EN, conservando también las traducciones Qt |
| Portabilidad de revisión | UTF-8 explícito y normalización de rutas Windows/POSIX en las identidades de Bandit |
| Dependencias revisadas | Pillow 13.0.0, pypdf 6.21.2, setuptools 84.1.0 y certifi 2026.10.19; wheels, hashes e inventarios sincronizados |
| Identidad consistente | `VERSION` 3.0.0 y plantilla Windows sin otra versión fija |

## Incompatibilidades deliberadas

No se convierten bases anteriores ni se leen flags de funciones desde QSettings.
Los archivos de usuario incompatibles se conservan intactos. Para una sesión nueva,
use el Excel de origen y una ubicación de datos independiente; no sobrescriba las
bases antiguas. Los encabezados Excel interpretados son los documentados, con
normalización de espacios, mayúsculas y acentos. Las columnas no documentadas se ignoran.

Los controles opcionales actuales, MCP, edición reversible, recursos, calendario,
escenarios y exportaciones se conservan. El campo `protocol: legacy` de la guía
OpenCode identifica el transporte que usa ese cliente; no mantiene un adaptador
antiguo dentro de SORTH.

## Estado de las funcionalidades

| Área | Estado y alcance actual |
| --- | --- |
| Importación | Excel `.xlsx`, validación previa, avisos y cancelación sin perder la sesión abierta; hojas y encabezados documentados |
| Generación | Greedy con reintentos, restricciones modeladas, recursos y calendario; puede dejar grupos sin asignar |
| Revisión y edición | Vistas de resultados, cambios reversibles y validación de conflictos; requiere revisión humana |
| Proyectos y escenarios | Catálogo local, persistencia, recuperación y comparación; formatos actuales estrictos |
| Exportación | Excel, CSV y PDF, escritura atómica y confirmación de sobrescritura |
| Apariencia | Temas, preferencias e idiomas ES/EN con catálogos consolidados |
| MCP opcional | Componente aislado, permisos revocables y contratos probados por separado |
| Distribución Windows | Pipeline para paquete, recuperación e instalador; la aceptación depende de sus comprobaciones y de revisión nativa |

## Trabajo pendiente y límites de aceptación

Las [limitaciones del producto](../../KNOWN_LIMITATIONS.md) siguen vigentes. La
heurística no demuestra optimalidad ni inviabilidad; el horario necesita revisión
antes de uso institucional. No hay gestión multiusuario ni sincronización, y no
se modela un sistema completo de matrícula o disponibilidad docente/estudiantil.
Son límites de alcance, no funcionalidades implementadas.

El piloto con personas nuevas continúa pendiente. La ejecución offscreen no
acredita lectores de pantalla ni la experiencia en un escritorio real. Los
paquetes de revisión no están firmados. La [revisión de licencias](../../LICENSING_REVIEW.md)
mantiene pendientes de recursos de terceros y del canal privado de seguridad
antes de anunciar una distribución lista para terceros.

## Validación

La revisión Windows de `de24bd6e1e53ba2bcf244b94991244af266b4d4a` terminó
correctamente con CPython 3.12.10. La colección y la unión exacta de los cuatro
inventarios verificaron 3.875 casos únicos, sin omisiones ni duplicados.

| Lote Windows | Aprobadas | Omitidas informadas por pytest |
| --- | ---: | ---: |
| Interfaz | 1.793 | 6 |
| Distribución visual | 566 | 2 |
| Temas en ejecución | 24 | 2 |
| Resto | 1.478 y 3 subpruebas | 12 |

Las omisiones de módulos durante la colección se informan en cada proceso; no
deben sumarse como casos únicos entre lotes. Los inventarios seleccionados son
1.797, 566, 24 y 1.488 casos, respectivamente.

La misma ejecución generó el manual y los binarios, validó el MCP congelado sin
Python en el PATH del proceso hijo, probó la aplicación empaquetada y su comando
de recuperación, construyó el instalador y verificó la instalación y la
desinstalación conservando datos.

- [Windows, regresión, paquete e instalador: aprobado](https://github.com/RodrigoUC/SORTH-AI/actions/runs/40601880542).
- [Contrato MCP: aprobado](https://github.com/RodrigoUC/SORTH-AI/actions/runs/40601880553).
- [Seguridad: aprobado](https://github.com/RodrigoUC/SORTH-AI/actions/runs/40601880471).

La comprobación local aislada de MCP aprobó 106 pruebas y omitió dos casos POSIX
en Windows. Los 13 contratos del control de seguridad pasaron. La auditoría de
los inventarios exactos de dependencias (29 de base, 38 de MCP universal y 40 del
componente Windows) no encontró vulnerabilidades ni omisiones. Los informes
locales se encuentran en `project_root/build/reports` y
`project_root/build/security/consolidation`.

El entorno de revisión local utiliza Python 3.13.14 y Qt sin pantalla con las fuentes
de Windows. No sustituye la aceptación del instalador en CPython 3.12.10, equipos
sin Python, lectores de pantalla, firma o revisión legal de distribución.

## Integración

Los commits `0ea2d4a` y `de24bd6` están publicados en
`codex/consolidate-current-architecture`. La [PR 60](https://github.com/RodrigoUC/SORTH-AI/pull/60)
mantiene la revisión separada de `main`. No se ha fusionado ni publicado una
release. Las actualizaciones documentales posteriores vuelven a activar los
controles de la PR; los enlaces anteriores identifican la revisión de código
exacta a la que corresponden estos resultados.

## Referencias

Pillow. (2026). *Pillow (versión 13.0.0)* [Software]. PyPI. https://pypi.org/project/pillow/13.0.0/

pypdf. (2026). *pypdf (versión 6.21.2)* [Software]. PyPI. https://pypi.org/project/pypdf/6.21.2/

Python Packaging Authority. (2026). *setuptools (versión 84.1.0)* [Software]. PyPI. https://pypi.org/project/setuptools/84.1.0/

Certifi. (2026). *certifi (versión 2026.10.19)* [Software]. PyPI. https://pypi.org/project/certifi/2026.10.19/
