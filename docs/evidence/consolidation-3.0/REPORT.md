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

## Validación

Los informes de la ejecución se encuentran en `project_root/build/reports` y
`project_root/build/security/consolidation`. La validación completa exige colección,
los cuatro procesos seriales y la unión exacta de sus inventarios. Este informe
se completa con los resultados al terminar esa secuencia.

El entorno de revisión local utiliza Python 3.13.14 y Qt sin pantalla con las fuentes
de Windows. No sustituye la aceptación del instalador en CPython 3.12.10, equipos
sin Python, lectores de pantalla, firma o revisión legal de distribución.

## Referencias

Pillow. (2026). *Pillow (versión 13.0.0)* [Software]. PyPI. https://pypi.org/project/pillow/13.0.0/

pypdf. (2026). *pypdf (versión 6.21.2)* [Software]. PyPI. https://pypi.org/project/pypdf/6.21.2/

Python Packaging Authority. (2026). *setuptools (versión 84.1.0)* [Software]. PyPI. https://pypi.org/project/setuptools/84.1.0/

Certifi. (2026). *certifi (versión 2026.10.19)* [Software]. PyPI. https://pypi.org/project/certifi/2026.10.19/
