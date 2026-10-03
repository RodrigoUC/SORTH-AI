# SORTH - Sistema de Organización de Horarios

## Comunidad y estado del proyecto

El código propio de SORTH está bajo [GPL-3.0-only](LICENSING.md). Los recursos de terceros conservan sus licencias; la revisión de módulos nativos y del paquete final sigue pendiente antes de una release pública.

- [Contribuir](CONTRIBUTING.md) · [Soporte por Issues](SUPPORT.md) · [Seguridad](SECURITY.md)
- [Guía de convivencia](CODE_OF_CONDUCT.md) · [Créditos](CREDITS.md) · [Revisión de licencias](docs/LICENSING_REVIEW.md)
- [Documentación](docs/README.md) · [Inicio rápido](docs/QUICKSTART.md) · [Privacidad](PRIVACY.md)
- [Limitaciones conocidas](docs/KNOWN_LIMITATIONS.md) · [Checklist de releases](docs/RELEASING.md)
- [Instalar y ejecutar desde código](project_root/README.md) · [Distribución Windows](docs/release/WINDOWS_DISTRIBUTION.md)

Los reportes pueden escribirse en español o inglés. Utiliza datos sintéticos: los issues son públicos.

## Repositorio de GITHUB
https://github.com/RodrigoUC/SORTH-AI

## Descripción del Proyecto

SORTH es una aplicación de escritorio especializada en la generación automática de horarios académicos. El sistema resuelve el problema de asignación de cursos a aulas y bloques horarios utilizando técnicas avanzadas de optimización combinatoria, permitiendo automatizar un proceso que tradicionalmente requiere intervención manual y es propenso a conflictos de programación.

## Problema y Solución

### Desafío
La creación manual de horarios académicos es un problema complejo que implica:
- Asignación de cientos de grupos de cursos a aulas limitadas
- Respeto de disponibilidad de salas
- Minimización de conflictos de horario
- Cumplimiento de restricciones múltiples (aulas reservadas, horarios preferidos, etc.)

### Solución
SORTH implementa un **algoritmo Greedy con reintentos** y heurísticas inteligentes para resolver automáticamente estas asignaciones en tiempo real, buscando asignaciones que respeten las restricciones implementadas. Puede dejar grupos sin asignar; no garantiza una solución completa ni óptima.

## Características Técnicas Principales

- **Algoritmo Greedy con reintentos** — evita explorar todo el árbol de backtracking. Ordena grupos por dominio más pequeño (MRV), asigna el mejor candidato disponible, y hace hasta 3 reintentos con preferencias relajadas para grupos sin asignar
- **Contadores incrementales** — scoring O(1) por lookup en lugar de O(n²) por iteración sobre asignaciones
- **Modelo de intervalos en minutos** — soporta horarios con cualquier granularidad (ej: 08:00–10:55)
- **Preferencias blandas** — día y hora preferidos son sugerencias, no restricciones duras. Si no hay espacio en el slot preferido, el grupo se asigna en otro horario
- **Sugerencias por grupo individual** — cada fila del Excel puede tener su propia aula/día/hora sugerida, preservada por grupo
- **Laboratorio obligatorio en generación automática** — un curso LAB nunca se coloca automáticamente en un aula regular. Si queda pendiente, se muestra el motivo. El usuario puede asignarlo manualmente y confirmar una excepción registrada, respetando capacidad, horario y conflictos. Para cursos REGULAR se conserva la preferencia de tipo
- **Aulas con restricción de cursos** — un aula puede reservarse exclusivamente para ciertos cursos (bidireccional)
- **Horario máximo 22:00** — soporta cursos nocturnos que terminan después de las 21:00
- **Split automático de sesiones largas** — cursos > 270 min se dividen en bloques de 120 min con chunk mínimo de 60 min. El usuario puede forzar o desactivar el split por curso desde la GUI
- **Generación reproducible** — semilla configurable para resultados deterministas
- **Persistencia de sesión** — la sesión activa (cursos, aulas, restricciones y horario generado) se guarda automáticamente en SQLite (la carpeta de datos del usuario (`%LOCALAPPDATA%/SORTH/sorth_session.db` en Windows)) y se ofrece restaurar al abrir la aplicación
- **Exportación** en Excel (grilla visual por aula con colores por curso) y CSV

## Formato del Excel de Entrada

El sistema lee un único archivo Excel con dos hojas:

> **Importante**: el sistema busca las hojas **por nombre exacto** (`Aulas` y `Cursos`), respetando mayúsculas y minúsculas. El orden de las hojas dentro del archivo no importa.

### Hoja `Aulas`
| # DE AULA | DESCRIPCIÓN | CAMPUS | CAPACIDAD | CAPACIDAD 80% |
|-----------|-------------|--------|-----------|---------------|
| L-DEMO-1  | Laboratorio de ejemplo | DEMO | 16 | 13 |
| A-DEMO-1       | Aula        | DEMO     | 60        | 48            |

- Aulas que comienzan con `L` → tipo LAB (por defecto, editable en GUI)
- Resto → tipo REGULAR
- Disponibilidad por defecto: **07:00 a 22:00**, todos los días (Lunes–Sábado)
- Aulas referenciadas en `Cursos` que no existen en esta hoja → ignoradas (tratadas como sin preferencia)

### Hoja `Cursos`
| Curso   | Nombre de Curso | Cantidad de Grupos | Horas       | Aula     | Días |
|---------|-----------------|--------------------|-------------|----------|------|
| DEM101  | Pensamiento lógico (ejemplo) | —                 | 0800-1030   | A-DEMO-2     | L    |
| DEM101  | Pensamiento lógico (ejemplo) | —                 | 1000-1230   | A-DEMO-1     | M    |
| DEM111L | Laboratorio de modelos (ejemplo)  | —                 | 0700-0930   | L-DEMO-1   | I    |

- Cada fila representa **un grupo sugerido** del curso
- Múltiples filas con el mismo código → múltiples grupos, cada uno con su propia sugerencia de aula/día/hora
- `Horas`: formato `HHMM-HHMM`. Vacío o `-` = sin preferencia
- `Días`: `L`=Lunes, `I`=Martes, `M`=Miércoles, `J`=Jueves, `V`=Viernes, `S`=Sábado
- `Aula` y `Días` son opcionales

## Tecnologías Utilizadas

- **Python**: referencia de empaquetado Windows CPython 3.12.10 x64
- **PyQt6**: Framework para interfaz gráfica de escritorio
- **pandas**: Procesamiento y manipulación de datos
- **openpyxl**: Lectura y escritura de archivos Excel
- **sqlite3** (stdlib): Persistencia de sesión
- **PyInstaller**: Empaquetado como ejecutable de Windows
- **pytest**: Framework de testing

## Arquitectura del Sistema

El proyecto sigue la arquitectura en capas descrita abajo. El
[mapa de archivos y dependencias](docs/architecture/ARCHITECTURE.md) amplía estas
responsabilidades, y la [decisión investigada](docs/architecture/decisions/0001-modular-layers.md)
explica su evolución incremental sin cambiar las cuatro capas:

- **Presentation Layer** (`src/gui/`): Interfaz gráfica PyQt6 con gestión de cursos y visualización de horarios
- **Application Layer** (`src/application/`): Servicios de orquestación y lógica de negocio
- **Domain Layer** (`src/scheduling/`): Algoritmo Greedy, modelo de intervalos, representación de cursos y aulas
- **Infrastructure Layer** (`src/infrastructure/`): Lectura de Excel, exportación de resultados, persistencia SQLite de sesión

## Flujo de Operación

1. Carga del archivo Excel (hojas `Aulas` y `Cursos`)
2. Revisión y edición de cursos importados en la GUI
3. Configuración opcional de aulas con restricciones y/o agregar aulas nuevas
4. Ejecución del algoritmo de programación (en hilo separado, sin congelar la GUI)
5. Visualización de resultados en 3 vistas: Lista Detallada, Cuadrícula por Aula, Por Aula
6. Edición/eliminación de grupos directamente desde el horario generado
7. Exportación del horario finalizado

## Distribución

La distribución predeterminada para Windows es una carpeta con `SORTH.exe` y sus dependencias; no requiere instalar Python en el equipo destino. Debe extraerse y conservarse completa. Consulta [Distribución para Windows](docs/release/WINDOWS_DISTRIBUTION.md) para compilar, verificar y publicar sin desactivar las protecciones de seguridad. El workflow **Windows review build** genera paquetes de revisión sin firma y un manual PDF actualizado como artefactos temporales de Actions; no publica versiones. Los ejecutables y PDF antiguos ya no se guardan en el árbol fuente.

## Historial de Cambios

### v2.0

#### Algoritmo
- **Reemplazo de backtracking por Greedy con reintentos**: elimina el congelamiento de la GUI con datasets grandes (250+ grupos). El tiempo depende de grupos, aulas, candidatos y restricciones
- **Contadores incrementales**: `_day_load`, `_time_load`, `_classroom_uses`, `_course_slots` se actualizan en O(1) al asignar, eliminando el O(n²) oculto en el scoring
- **Preferencias blandas**: día y hora preferidos ya no son restricciones duras en `_build_domains`. Pass 1 respeta preferencias; reintentos las relajan para grupos sin asignar
- **Sugerencias por grupo individual**: cada grupo lleva su propia `suggested_classroom`, `preferred_day` y `preferred_start_min` desde el Excel, en lugar de compartir el valor más común del curso
- **Restricción bidireccional por grupo**: si un aula está restringida, solo aplica a los grupos cuya `suggested_classroom` coincide con esa aula, evitando forzar otros grupos del mismo curso
- **Tipo de sala**: LAB es obligatorio en generación automática. Las excepciones en aula regular son manuales, confirmadas y registradas; REGULAR conserva la preferencia de ordenamiento.
- **Horario extendido a 22:00**: `DEFAULT_DAY_END = 22 * 60` para soportar cursos nocturnos
- **Umbral de split aumentado a 270 min**: sesiones de hasta 4.5h se asignan como bloque único. Chunk mínimo de 60 min para evitar fragmentos inútiles
- **Fallback en generación de candidatos**: si la ventana ±30 min alrededor de la preferencia no produce candidatos (ej: solapamiento con almuerzo), se usa el día completo con paso de 30 min

#### Infraestructura
- **Persistencia SQLite** (`src/infrastructure/session_repository.py`): reemplaza cualquier mecanismo anterior. La sesión completa (aulas, cursos con sugerencias por grupo, restricciones, asignaciones y metadatos) se guarda en la carpeta de datos del usuario (`%LOCALAPPDATA%/SORTH/sorth_session.db` en Windows)
- **Esquema relacional**: tablas `session`, `classrooms`, `courses`, `course_group_suggestions`, `restrictions`, `assignments`
- **Guardado automático**: se invoca tras cada acción relevante (cargar Excel, editar cursos, generar horario, eliminar grupo)
- **Restauración al inicio**: si existe sesión guardada con cursos, se ofrece restaurarla mediante diálogo al abrir la aplicación
- Aulas referenciadas en `Cursos` que no existen en la hoja `Aulas` se ignoran silenciosamente (tratadas como sin preferencia de aula)
- `load_course_classroom_map()` filtra correctamente con `known_classrooms`
- Sugerencias por grupo preservadas individualmente en `group_suggestions`

#### GUI
- **Hilo separado (`QThread`)**: el scheduler corre en `SchedulerWorker`, la GUI nunca se congela
- **Barra de progreso indeterminada** visible durante la generación
- **Diálogos personalizados** con header coloreado (azul/rojo) reemplazando `QMessageBox`
- **Pestañas con contraste visual**: pestaña activa en azul `#1967D2` con texto blanco en negrita
- **Fuente global 10pt** aplicada via stylesheet en `gui_app.py`
- **Agregar Aula**: tipo LAB/REGULAR se detecta automáticamente por el código pero es editable por el usuario
- **Hora preferida**: reemplazados spinners por `QTimeEdit` con formato `HH:mm`
- **Colores por curso** en vista de cuadrícula y Excel exportado (no por aula)
- **Ordenamiento por columnas** en Lista Detallada y Por Aula con `_SortableItem` para días (orden Lunes→Sábado) y horas (orden numérico)
- **Búsqueda en tiempo real**: por código/nombre en Lista Detallada; por aula/grupo en Por Aula
- **Botones Editar/Eliminar** en Lista Detallada y Por Aula + menú contextual (clic derecho)
- **Editar desde el horario**: abre `CourseDialog` del curso correspondiente en Gestión de Cursos
- **Eliminar grupo del horario**: actualiza lista, tabla por aula y cuadrícula en tiempo real
- **Resumen visual** con tarjetas KPI (grupos asignados, sin asignar, aulas, cursos), tabla por día, tabla por aula y lista de grupos sin asignar
- **Restricciones de aulas**: diálogo con panel izquierdo (aulas) y panel derecho (cursos individuales con checkbox), permite desmarcar cursos específicos

#### Exportador
- Reescrito completamente para el modelo de minutos
- Grilla visual con `merge_cells` proporcional a la duración del curso
- Colores por curso (no por aula) consistentes con la GUI

### v1.0
- Versión inicial con modelo de bloques de 1 hora
- Lectura de Excel con hojas `Capacidad aulas` y `Aulas` (disponibilidad)
- Configuración de cursos mediante JSON
- Algoritmo CSP con backtracking, MRV y LCV
- Exportación a Excel y CSV

## Ejemplo incluido

`data/input/Cursos_Ejemplo.xlsx` contiene 8 aulas ficticias y 12 cursos de demostración. Sus 36 grupos producen 42 sesiones al dividir los proyectos largos. Todos los datos son sintéticos; no corresponden a una institución. La procedencia se describe en `data/input/PROVENANCE.md` (rutas relativas a `project_root`).

## Calidad y exportación local

La GUI incluye [indicadores explicables de cobertura, preferencias y uso de recursos](docs/user/QUALITY_METRICS.md), sin nota global ni promesa de optimalidad, y [exportación PDF en español o inglés](docs/user/PDF_EXPORT_NOTES.md). Estas funciones son locales y no requieren MCP ni un proveedor de IA.

## Integración MCP opcional

Un cliente MCP elegido por el usuario puede solicitar validar datos y generar una propuesta local mediante el [adaptador stdio opcional](project_root/MCP_OPTIONAL.md). El permiso se puede activar o desactivar en Configuración tras verificar disponibilidad local. En Windows, **Preparar complemento MCP** copia y verifica el compañero incluido tras una confirmación explícita, sin red ni instalación en Python del sistema. Preparar no activa el permiso; Cancelar Configuración conserva el complemento preparado. La guía ofrece configuración para OpenCode V2 y Claude Desktop y explica la conexión separada que necesita ChatGPT. Una compilación sin el paquete lo indica; se conserva la ruta Python/CLI para desarrollo. Está desactivado por defecto y el cliente inicia el proceso: no requiere un modelo, claves ni pagos para usar SORTH. El adaptador pide al host aclarar información faltante y puede devolver un Excel temporal mediante recursos MCP, reutilizando el formato de escritorio; la descarga visible depende del host. No guarda ni aplica propuestas a la sesión y conserva LAB estricto. Revisa [privacidad](PRIVACY.md) antes de compartir datos con un host o proveedor externo.
