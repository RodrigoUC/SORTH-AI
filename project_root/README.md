# SORTH - Sistema de Organización de Horarios

## Repositorio de GITHUB
https://github.com/RodrigoUC/SORTH-AI

## Descripción

SORTH es una aplicación de escritorio con interfaz gráfica para la generación automática de horarios académicos. Utiliza un **algoritmo Greedy con reintentos** y contadores incrementales para asignar grupos de cursos a aulas disponibles en tiempo real, considerando capacidad y aulas reservadas, con tipo de sala y horarios como preferencias según las reglas del planificador. Puede dejar grupos sin asignar y requiere revisión humana.

---

Consulta [contribución y pruebas](../CONTRIBUTING.md), [soporte](../SUPPORT.md), [seguridad](../SECURITY.md) y [limitaciones](../docs/KNOWN_LIMITATIONS.md). El código propio está bajo [GPL-3.0-only](../LICENSING.md); los recursos de terceros conservan sus licencias.

## Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/RodrigoUC/SORTH-AI.git
cd SORTH-AI/project_root
```

### 2. Crear entorno virtual
```powershell
python -m venv venv
. venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias
```powershell
python -m pip install -r requirements.txt
```

---

## Uso

### Interfaz Gráfica
```powershell
python gui_app.py
```

#### Pasos:
1. **Cargar archivo Excel** con las hojas `Aulas` y `Cursos`
2. **Revisar cursos importados** — cada fila del Excel es un grupo sugerido. Filtrar por código o nombre con la barra de búsqueda
3. **Agregar aulas nuevas** (opcional) — desde el botón "Agregar Aula", con tipo auto-detectado pero editable
4. **Configurar restricciones de aulas** (opcional) — reservar un aula para ciertos cursos específicos con checkboxes individuales
5. **Generar horario** con el botón verde — corre en hilo separado, la GUI no se congela
6. **Ver resultados** en las pestañas: Lista Detallada, Vista de Cuadrícula, Por Aula
7. **Editar o eliminar grupos** desde el horario generado con los botones al pie de cada tabla
8. **Exportar** a Excel (con grilla visual por aula) o CSV

Para personalizar la interfaz, consulta [Apariencia y temas propios](../docs/user/APPEARANCE.md).

---

## Formato del Excel de Entrada

El sistema lee un único archivo Excel con **dos hojas**.

> **Importante**: el sistema busca las hojas **por nombre exacto** (`Aulas` y `Cursos`), respetando mayúsculas y minúsculas. El **orden de las hojas** dentro del archivo **no importa**.

### Validación antes de importar

Use un archivo **.xlsx**; los archivos antiguos .xls deben guardarse como Libro de Excel (.xlsx).
Los encabezados van en la primera fila. Se permiten columnas reordenadas y diferencias de
mayúsculas, espacios exteriores o acentos en los encabezados. Los nombres de hojas siguen
siendo exactamente `Aulas` y `Cursos`; las hojas adicionales se ignoran.

Antes de materializar las tablas se comprueban las referencias reales de filas y celdas: cada hoja importada admite hasta 10.000 filas de datos, 128 columnas y 500.000 celdas en su rectángulo (incluido el encabezado). Una celda aislada muy lejos también cuenta para ese rectángulo; elimine filas/columnas sobrantes o divida el archivo si supera el límite. Se mantienen además los límites de 25 MiB de archivo y 100 MiB descomprimidos.

Se rechaza XML de hoja mal formado: celdas fuera de sus filas, etiquetas de celda inesperadas, coordenadas duplicadas o filas que no avanzan. Las filas y columnas vacías intermedias siguen admitiéndose; si el archivo se rechaza, guarde una copia válida desde Excel antes de volver a importar.

- `Aulas` requiere `# DE AULA`; `Cursos` requiere `Curso`. Debe haber al menos un aula y un curso.
- Las filas completamente vacías se ignoran. Una fila de datos sin identificador debe corregirse.
- No se admiten encabezados duplicados ni códigos de aula repetidos. Los códigos de curso repetidos sí representan grupos distintos.
- `CAPACIDAD` debe ser un entero no negativo. Si falta, se avisa que se usará 0.
- `Horas` y `Días` vacíos o `-` mantienen los valores predeterminados; los valores no vacíos mal escritos muestran la hoja y fila que debe corregirse.
- Los alias históricos no ambiguos (por ejemplo `Horas sugeridas`, `Días sugeridos` o `Aula sugerida`) reciben la misma validación y avisos. El encabezado exacto tiene prioridad, incluso vacío; si faltara y hubiera varios alias para el mismo campo, se pide corregirlos.
- Las referencias a aulas desconocidas siguen importándose sin esa preferencia, pero ahora se muestran como avisos antes de confirmar.
- Cancelar la selección, cancelar los avisos o recibir un error de validación conserva los datos y el horario abierto.

### Hoja `Aulas`
| # DE AULA | DESCRIPCIÓN | CAMPUS | CAPACIDAD | CAPACIDAD 80% |
|-----------|-------------|--------|-----------|---------------|
| L-DEMO-1  | Laboratorio de ejemplo | DEMO | 16 | 13 |
| A-DEMO-1       | Aula        | DEMO     | 60        | 48            |

- Nombre comienza con `L` → tipo **LAB** (editable desde GUI al agregar aulas manualmente)
- Resto → tipo **REGULAR**
- Disponibilidad por defecto: **07:00–22:00**, Lunes a Sábado
- Aulas referenciadas en `Cursos` que no existen aquí → ignoradas (sin preferencia de aula)

### Hoja `Cursos`
| Curso   | Nombre de Curso  | Cantidad de Grupos | Horas     | Aula   | Días |
|---------|------------------|--------------------|-----------|--------|------|
| DEM101  | Pensamiento lógico (ejemplo) | —                  | 0800-1030 | A-DEMO-2   | L    |
| DEM101  | Pensamiento lógico (ejemplo) | —                  | 1000-1230 | A-DEMO-1   | M    |
| DEM111L | Laboratorio de modelos (ejemplo)  | —                  | 0700-0930 | L-DEMO-1 | I    |

- **Cada fila = un grupo sugerido**. Dos filas con el mismo código → 2 grupos de ese curso, cada uno con su propia sugerencia de aula/día/hora
- Los valores predeterminados del curso usan el valor más frecuente; si hay empate, se conserva el primero según el orden de las filas. Esto también estabiliza el tipo de aula inferido al volver a importar el mismo archivo.
- `Horas`: formato `HHMM-HHMM` (ej: `0800-1055`). Vacío o `-` = sin preferencia
- `Días`: `L`=Lunes, `I`=Martes, `M`=Miércoles, `J`=Jueves, `V`=Viernes, `S`=Sábado. Puede ser múltiple: `L,M`
- `Aula` y `Días` son opcionales — vacío = sin preferencia

---

## Arquitectura

La organización conserva estas cuatro capas. El árbol muestra sus módulos principales;
[el índice de documentación](../docs/README.md) reúne las guías por audiencia.
El [mapa de responsabilidades y guardas](../docs/architecture/ARCHITECTURE.md)
explica los límites, adaptadores opcionales y excepciones de compatibilidad.

```
src/
├── scheduling/              # Dominio — algoritmo y modelo
│   ├── time_model.py        # Modelo de tiempo en minutos (07:00–22:00)
│   ├── classroom.py         # Aula con ocupación por intervalos y restricciones
│   ├── group.py             # Grupo de curso (unidad de asignación)
│   ├── course.py            # Curso → genera grupos, split si duración > 270 min
│   ├── schedule_state.py    # Estado del horario (assign/unassign)
│   └── scheduler.py         # Algoritmo Greedy con reintentos + contadores O(1)
├── application/
│   └── scheduling_service.py  # Orquestador: carga datos, ejecuta scheduler
├── infrastructure/
│   ├── excel_reader.py        # Lee hojas Aulas y Cursos del Excel
│   ├── session_repository.py  # Persistencia SQLite de la sesión activa
│   └── schedule_exporter.py   # Exporta a Excel (grilla visual) / CSV
└── gui/
    ├── main_window.py           # Ventana principal + QThread worker
    ├── course_manager_widget.py # Gestión de cursos con búsqueda
    └── schedule_viewer_widget.py# Visualización: lista, cuadrícula, por aula
```

---

## Modelo de Tiempo

El sistema trabaja con **intervalos en minutos desde medianoche**:

| Concepto | Valor |
|----------|-------|
| Inicio del día | 420 (07:00) |
| Fin del día | 1320 (22:00) |
| Almuerzo excluido | 720–780 (12:00–13:00) |
| Paso sin preferencia | 30 min |
| Paso con preferencia | 5 min (±30 min alrededor de la preferencia) |
| Fallback si ±30 min vacío | día completo con paso de 30 min |

```python
TimeModel.hhmm_to_minutes("0800")  # → 480
TimeModel.minutes_to_hhmm(655)     # → "10:55"
```

---

## Algoritmo Greedy con Reintentos

### Flujo
1. **`_build_domains`**: genera candidatos `(aula, día, start_min)` por grupo
   - Pass 1 (estricto): respeta `suggested_classroom`, `preferred_day` y `preferred_start_min`
   - Reintentos (relajado): ignora preferencias de día/hora para grupos sin asignar
   - Restricción bidireccional por grupo: si el aula sugerida del grupo está restringida, solo esa aula aplica; otros grupos del mismo curso no se ven afectados
2. **`_greedy_pass`**: ordena grupos por dominio más pequeño (MRV), asigna el mejor candidato según scoring
3. **Reintentos** (hasta 3): reconstruye dominios relajados para grupos sin asignar y repite

### Scoring de candidatos (menor = mejor)
| Prioridad | Criterio |
|-----------|----------|
| 1 | Tipo de sala coincide (LAB/REGULAR) |
| 2 | Aula sugerida del grupo coincide |
| 3 | Anti-copia: consecutivo mismo día > mismo horario > distinto día mismo horario |
| 4 | Preferencia de día y hora |
| 5 | Distribución equitativa por día (penaliza >2 grupos/día, sábado penalizado) |
| 6 | Distribución equitativa por hora (favorece ≤16:00) |
| 7 | Menor número de grupos en el aula |

### Restricciones de aula (bidireccional)
Un aula puede tener una lista de cursos permitidos (`allowed_courses`). Si está definida:
- Solo esos cursos pueden asignarse a esa aula
- Los grupos de esos cursos cuya `suggested_classroom` coincide con el aula restringida **solo** pueden ir a esa aula
- Grupos del mismo curso con distinta `suggested_classroom` no se ven afectados

---

## Detección de Tipo de Sala

| Código / Aula | Tipo | Regla |
|---------------|------|-------|
| DEM101 | REGULAR | No termina en L ni P, sin aula sugerida LAB |
| DEM111L | LAB | Termina en L |
| DEM112P | LAB | Termina en P |
| DEM112 con aula L-DEMO-1 | LAB | Aula sugerida es LAB |
| L-DEMO-1 (aula) | LAB | Nombre del aula comienza con L |

El tipo se infiere primero del aula sugerida en el Excel; si no hay aula sugerida, se usa el sufijo del código. El usuario puede sobreescribir el tipo al agregar aulas manualmente desde la GUI.

---

## Split de Cursos Largos

Cursos con duración > 270 min se dividen automáticamente en sesiones de 120 min:

| Duración total | Sesiones generadas |
|----------------|-------------------|
| 300 min | 120 + 120 + 60 |
| 360 min | 120 + 120 + 120 |
| 400 min | 120 + 160 (chunk mínimo 60 min) |

El usuario puede sobreescribir este comportamiento por curso desde el diálogo de edición:

| Opción | `force_split` | Comportamiento |
|--------|--------------|----------------|
| Automático (default) | `None` | Divide solo si duración > 270 min |
| Forzar división | `True` | Siempre divide en bloques de 2h |
| No dividir | `False` | Asigna completo en un solo día |

Las sesiones divididas deben cumplir:
- Días distintos entre sí
- Misma hora de inicio
- Preferentemente la misma aula

---

## GUI — Funcionalidades

### Gestión de Cursos
- Importación desde Excel con sugerencias por grupo preservadas
- Búsqueda en tiempo real por código o nombre
- Agregar/editar/eliminar cursos manualmente
- `QTimeEdit` para hora preferida (formato HH:mm, más intuitivo que spinners)
- Tipo de sala auto-detectado, editable al agregar aulas

### Horario Generado
- **Lista Detallada**: búsqueda por código/nombre, ordenamiento por cualquier columna (días en orden Lunes→Sábado, horas numéricamente), grupos sin asignar marcados en rojo
- **Vista de Cuadrícula**: grilla 07:00–22:00 en slots de 30 min, bloques con span proporcional a la duración, colores por curso
- **Por Aula**: búsqueda por aula o grupo, ordenamiento por columnas
- **Editar/Eliminar** desde cualquier tabla: botones al pie + menú contextual (clic derecho)
- Eliminar un grupo actualiza las 3 vistas en tiempo real
- **Resumen**: tarjetas KPI + tabla por día + tabla por aula + lista de sin asignar

### Restricciones de Aulas
- Diálogo con panel izquierdo (aulas checkables) y panel derecho (cursos con checkboxes individuales)
- Permite desmarcar cursos específicos (ej: excluir DEM112 teórico, mantener solo DEM112P)
- Botones "Marcar todos" / "Desmarcar todos"
- Restricciones persistentes entre reaperturas del diálogo

---

## Exportación

### Excel (`.xlsx`)
- Una hoja por aula con grilla visual 07:00–22:00
- Bloques de cursos con `merge_cells` proporcional a la duración
- Colores por curso (consistentes con la GUI)
- Hoja "Asignaciones": lista detallada con código, nombre, grupo, aula, día, hora inicio/fin
- Hoja "Por Aula": misma información ordenada por aula → día → hora

### CSV
- Lista detallada en formato plano, codificación UTF-8 con BOM

---

## Pruebas

Ejecuta desde `project_root` con el entorno de desarrollo activado. La suite
completa usa [cuatro procesos en serie y verificación de inventarios](../docs/development/WORKFLOW.md#suite-completa-en-cuatro-procesos).
Esa guía incluye la configuración offscreen para PowerShell y Bash/POSIX.
El aislamiento es la invocación validada; no demuestra que esté corregido el
problema intermitente de ciclo de vida de la suite Qt monolítica.

Para pruebas focalizadas, por ejemplo sólo el dominio scheduling:

```sh
python -m pytest -c pytest.ini --rootdir=. tests/test_scheduling/ -v --tb=short
```

---

## Generar `.exe` para Windows

```powershell
.\build_exe.ps1
```

Salida predeterminada: carpeta `dist/SORTH/` con `SORTH.exe` y sus dependencias. Distribuye la carpeta completa. El modo de archivo único es opcional: `.\build_exe.ps1 -OneFile`.

Antes de compilar en Python 3.12 x64, instala `requirements-windows.lock` con `--require-hashes` en `.venv-build`; el script no instala ni actualiza paquetes automáticamente. El workflow **Windows review build** ejecuta pruebas, genera el manual PDF, compila y valida el ejecutable, y conserva ZIP/checksums de revisión por siete días. No firma ni publica releases. Consulta [Distribución para Windows](../docs/release/WINDOWS_DISTRIBUTION.md) para preparación, firmas y validación con las protecciones activadas.

---

## Estructura de Archivos

```
project_root/
├── src/
│   ├── application/
│   ├── scheduling/
│   ├── infrastructure/
│   └── gui/
├── tests/
│   └── test_scheduling/
├── data/
│   ├── input/           # Excel de entrada
│   └── output/          # Resultados exportados
├── assets/              # Icono de la aplicación
├── main.py              # Punto de entrada CLI
├── gui_app.py           # Punto de entrada GUI (con stylesheet global 10pt)
└── requeriments.txt
```

---

## Historial de Cambios

### v2.0

#### Algoritmo (`src/scheduling/scheduler.py`)
- **Reemplazo de backtracking por Greedy con reintentos**: evita explorar el árbol completo. El tiempo depende de grupos, aulas, candidatos y restricciones
- **Contadores incrementales**: `_day_load`, `_time_load`, `_classroom_uses`, `_course_slots` actualizados en O(1) al asignar
- **Preferencias blandas**: pass 1 estricto + hasta 3 reintentos relajados para grupos sin asignar
- **Sugerencias por grupo individual**: cada grupo lleva su propia `suggested_classroom`, `preferred_day` y `preferred_start_min`
- **Restricción bidireccional por grupo**: evalúa `suggested_classroom` del grupo, no solo el `course_code`
- **Tipo de sala**: LAB es obligatorio para la generación automática; REGULAR conserva la preferencia de ordenamiento. Una excepción LAB en aula regular requiere asignación manual confirmada.
- **Horario extendido a 22:00**
- **Umbral de split a 270 min**, chunk mínimo de 60 min
- **Control de split por curso**: `force_split=True` fuerza división, `force_split=False` la desactiva, `None` usa el umbral automático
- **Fallback de candidatos**: si ±30 min produce dominio vacío, usa día completo con paso 30 min

#### Lectura de Excel (`src/infrastructure/excel_reader.py`)
- Aulas inexistentes en `Cursos` ignoradas silenciosamente
- `load_courses()` acepta `known_classrooms` para filtrar referencias inválidas
- `load_course_classroom_map()` filtra con `known_classrooms`
- `group_suggestions` preserva sugerencia individual de cada fila
- Tipo de sala inferido desde el aula sugerida real, no solo del sufijo del código

#### Exportador (`src/infrastructure/schedule_exporter.py`)
- Reescrito completamente para modelo de minutos
- Grilla con `merge_cells` proporcional a duración
- Colores por curso (no por aula)
- Hojas: una por aula + "Asignaciones" + "Por Aula"

#### Aplicación (`src/application/scheduling_service.py`)
- Acepta `classrooms` externo para incluir aulas agregadas desde GUI
- Resetea `occupancy` y `allowed_courses` al inicio de cada run
- `TimeModel` con `DAY_END = 22 * 60`

#### Persistencia (`src/infrastructure/session_repository.py`)
- **SQLite** (la carpeta de datos del usuario (`%LOCALAPPDATA%/SORTH/sorth_session.db` en Windows)): almacena aulas, cursos con sugerencias por grupo, restricciones, asignaciones y metadatos (ruta Excel, semilla)
- **Esquema relacional**: tablas `session`, `classrooms`, `courses`, `course_group_suggestions`, `restrictions`, `assignments`
- **Guardado automático**: se invoca tras cada acción relevante (cargar Excel, editar cursos, generar horario, eliminar grupo)
- **Restauración al inicio**: si existe sesión guardada con cursos, se ofrece restaurarla mediante diálogo al abrir la aplicación

#### GUI
- **`QThread` worker**: scheduler en hilo separado, barra de progreso indeterminada
- **Diálogos con header coloreado**: reemplazan `QMessageBox` en toda la app
- **Pestañas con contraste**: activa en azul `#1967D2` texto blanco, inactiva gris
- **Fuente global 10pt** via stylesheet en `gui_app.py`
- **`QTimeEdit`** para hora preferida en `CourseDialog`
- **Control de split por curso** en `CourseDialog`: combo con tres opciones (Automático / Forzar división / No dividir)
- **Tipo de aula editable** en `AddClassroomDialog` (auto-detectado pero modificable)
- **Colores por curso** en cuadrícula y Excel exportado
- **`_SortableItem`**: ordenamiento correcto de días (Lunes→Sábado) y horas (numérico)
- **Búsqueda en tiempo real**: código/nombre en Gestión de Cursos y Lista Detallada; aula/grupo en Por Aula
- **Botones Editar/Eliminar** al pie de Lista Detallada y Por Aula + menú contextual
- **Eliminar grupo**: actualiza lista, por aula y cuadrícula en tiempo real
- **Resumen**: tarjetas KPI + tablas por día/aula + grupos sin asignar
- **Restricciones**: panel con checkboxes individuales por curso por aula

### v1.0
- Versión inicial con modelo de bloques de 1 hora
- Lectura de Excel con hojas `Capacidad aulas` y `Aulas`
- Configuración de cursos mediante JSON
- Algoritmo CSP con backtracking, MRV y LCV
- Exportación a Excel y CSV

---

## Tecnologías

- **Python 3.12.10 x64** como referencia del paquete Windows
- **PyQt6**: Interfaz gráfica
- **pandas**: Procesamiento de datos
- **openpyxl**: Lectura/escritura de Excel
- **sqlite3** (stdlib): Persistencia de sesión
- **PyInstaller**: Empaquetado como `.exe`
- **pytest**: Testing

---

## Autor

RodrigoUC


## Laboratorios y asignación manual

Los cursos LAB solo se asignan automáticamente a laboratorios. Si no se encuentra
un horario, la sesión permanece visible en la lista. Seleccione la fila para leer
el motivo; una búsqueda greedy sin resultado no prueba que el problema sea imposible.

Use **Asignar manualmente** para seleccionar aula, día y hora, también para sesiones
sin asignar. Elegir un aula regular para LAB requiere confirmar una excepción
(default: No). La excepción se marca en la lista y se conserva al guardar/restaurar
la sesión. No evita capacidad, horario, almuerzo, restricciones de aula, conflictos
ni las reglas de sesiones divididas. Una asignación antigua LAB en aula regular sin
confirmación guardada queda pendiente al restaurar: revísela y confírmela manualmente.

Antes de exportar se valida el horario completo. Los archivos mantienen sus siete
columnas compatibles: la marca de excepción se consulta en la sesión de SORTH.

## Ejemplo incluido

`data/input/Cursos_Ejemplo.xlsx` contiene 8 aulas ficticias y 12 cursos de demostración. Sus 36 grupos producen 42 sesiones al dividir los proyectos largos. Todos los datos son sintéticos; no corresponden a una institución. Véase `data/input/PROVENANCE.md`.
