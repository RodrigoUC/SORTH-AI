# Manual de usuario de SORTH

Para una primera prueba, consulta el [inicio rápido](../QUICKSTART.md). El [aviso de privacidad](../../PRIVACY.md) explica los datos locales y el soporte público.

## 1. ¿Qué es SORTH?

SORTH genera horarios académicos automáticamente, asignando grupos de cursos a aulas y franjas horarias disponibles. El sistema intenta respetar preferencias de aula, día y hora, y permite configurar restricciones exclusivas por aula. Este manual explica cómo preparar el Excel, revisar el horario y exportarlo.

---

## 2. Qué necesitas antes de comenzar

- La carpeta completa de la distribución de SORTH, extraída del ZIP. No separes `SORTH.exe` de sus dependencias.
- Un archivo Excel (`.xlsx`) con dos hojas: **`Aulas`** y **`Cursos`**.

> Los nombres de las hojas deben ser exactamente `Aulas` y `Cursos` (con mayúscula inicial). El orden de las hojas dentro del archivo no importa.

---

## 3. Cómo abrir la aplicación

1. Haz doble clic en `SORTH.exe`.
2. Espera a que aparezca la ventana principal.

Si Windows muestra una advertencia o bloquea el archivo, detente y comunica al responsable de la distribución el texto exacto, el nombre de la detección y la versión de SORTH. Mantén activas las protecciones de Windows.

Una advertencia de reputación de SmartScreen y una detección de malware de Defender son situaciones distintas. No se puede afirmar que sea un falso positivo sin investigar el archivo concreto. El responsable debe verificar la compilación y, si corresponde, solicitar una revisión a Microsoft. Consulta [Distribución para Windows](../release/WINDOWS_DISTRIBUTION.md).

---

## Idioma de la interfaz

El selector **Idioma / Language** del encabezado permite elegir **Español** o **English**. La preferencia se guarda localmente y se recuerda al abrir SORTH. Español es el idioma inicial y la alternativa si una preferencia o traducción no está disponible.

El cambio es inmediato y conserva los cursos, aulas, restricciones, horario, filtros, selección y formularios sin guardar. También puede cambiarse durante la generación sin desbloquear controles ni reiniciar el algoritmo. Los nombres que escribiste o importaste nunca se traducen.

La interfaz cambia de idioma, pero los archivos conservan el formato compatible: hojas de entrada **Aulas** y **Cursos**, columnas y días de exportación en español, horas **HH:mm** y los mismos alcances de **Exportar todas las asignaciones / Export all assignments** y **Exportar filtrado / Export filtered**. El selector de archivos del sistema puede aparecer en el idioma de Windows. Los detalles técnicos de errores de bibliotecas externas pueden conservar su texto original.

**Reducir animaciones** elimina las transiciones y utiliza un indicador estático durante la generación. La preferencia se guarda localmente; no cambia el resultado del planificador.

Para elegir o importar un tema desde Configuración, consulta [Apariencia y temas propios](APPEARANCE.md).

## 4. Flujo de uso paso a paso

### Paso 1 - Cargar el archivo Excel

Si aún no tienes el archivo, pulsa **Plantilla Excel…** junto a **Cargar Excel**.
Guarda la plantilla, lee sus instrucciones y reemplaza los ejemplos ficticios
por tus aulas y cursos. Consulta [la guía de importación](EXCEL_IMPORT_WORKFLOW.md#crear-un-archivo-con-la-plantilla).

1. Haz clic en **Cargar Excel**.
2. Selecciona el archivo `.xlsx` con las hojas `Aulas` y `Cursos`.
3. El nombre del archivo aparecerá en verde junto al botón si la carga fue exitosa.

Los cursos se importan automáticamente a la pestaña **Gestión de Cursos**.

---

### Paso 2 - Revisar y editar cursos

En la pestaña **Gestión de Cursos** verás todos los cursos importados.

**Buscar cursos**: usa la barra de búsqueda para filtrar por código o nombre en tiempo real.

**Editar un curso**: selecciona la fila y haz clic en **Editar**. Puedes modificar:
- Código y nombre del curso.
- Número de grupos.
- Duración (horas + minutos).
- Aula sugerida.
- Día preferido.
- Hora preferida - activa el checkbox y selecciona la hora con el selector `HH:mm`.
- **División en días** - controla si el curso se divide en múltiples sesiones:
  - **Automático** (por defecto): se divide solo si la duración supera 4.5 horas.
  - **Forzar división**: divide la duración en sesiones para días distintos. Se usan bloques de 2 horas; un resto menor de 1 hora se incorpora al bloque anterior. Una duración de hasta 2 horas sigue siendo una sola sesión.
  - **No dividir**: se asigna completo en un solo día, sin importar la duración.

> Al importar, el tipo de sala (LAB / REGULAR) se toma del aula sugerida, si se conoce. En caso contrario se infiere del código del curso (sufijo `L` o `P`: LAB). El formulario muestra el tipo de sala detectado.

**Agregar un curso manualmente**: haz clic en **Agregar Curso** y completa el formulario.

**Eliminar un curso**: selecciona la fila y haz clic en **Eliminar**.

**Limpiar todo**: elimina todos los cursos de la lista con **Limpiar Todo**.

Al cambiar los cursos o las aulas, el horario anterior se invalida. Debes generar un horario nuevo antes de exportar.

---

### Paso 3 - Agregar aulas nuevas (opcional)

Si necesitas incluir aulas que no están en el Excel:

1. Haz clic en **Agregar aula**.
2. Completa el código, descripción, campus y capacidad.
3. El tipo (LAB / REGULAR) se detecta automáticamente por el código, pero puedes cambiarlo manualmente.
4. Haz clic en **OK**.

---

### Paso 4 - Configurar restricciones de aulas (opcional)

Permite reservar un aula exclusivamente para ciertos cursos.

1. Haz clic en **Restricciones de aulas**.
2. En el panel izquierdo, activa el checkbox del aula que deseas restringir.
3. En el panel derecho aparecen los cursos asociados a esa aula en el Excel. Marca solo los cursos que deben usar esa aula exclusivamente.
   - Usa **Marcar todos** / **Desmarcar todos** para agilizar la selección.
4. Haz clic en **OK**.

> Cuando un aula está restringida, los grupos de los cursos marcados **solo** pueden asignarse a esa aula, y esa aula **solo** acepta esos cursos.

---

### Paso 5 - Configurar semilla (opcional)

En la barra inferior:

- **Semilla fija** (por defecto): permite reproducir resultados con los mismos datos, configuración, semilla y versión del programa.
- **Aleatoria**: cada ejecución puede generar una distribución distinta.

---

### Paso 6 - Generar el horario

1. Haz clic en **Generar horario**.
2. Aparece una barra de progreso animada mientras el algoritmo trabaja en segundo plano. Durante la generación, los controles de edición se deshabilitan; espera a que termine antes de cerrar.
3. Al terminar, un diálogo muestra el resumen: grupos asignados, aulas utilizadas y cursos programados.

> Si quedan sesiones sin asignar, se indican en el resumen y en el filtro **Estado: Sin asignar** de Lista detallada. Los motivos ayudan a revisar datos y restricciones; no demuestran que no exista una solución.

---

### Paso 7 - Revisar el horario generado

En la pestaña **Horario Generado** tienes tres vistas:

#### Lista Detallada
- Muestra todos los grupos asignados con código, nombre, aula, día y horario.
- **Buscar**: filtra por código o nombre de curso en tiempo real.
- **Ordenar**: haz clic en cualquier encabezado de columna para ordenar ascendente o descendente. Los días se ordenan en orden de semana (Lunes a Sábado).
- **Editar curso**: selecciona una fila y haz clic en **Editar Curso** para modificar el curso en Gestión de Cursos.
- **Quitar del horario**: selecciona una fila y confirma para dejar esa sesión sin asignar. Las tres vistas se actualizan. **Asignar manualmente** permite elegir aula, día y hora; se validan las restricciones. Un LAB en aula regular exige confirmación explícita y muestra **Excepción manual LAB**; no se permite ignorar capacidad ni conflictos.
- También puedes hacer **clic derecho** sobre una fila para acceder a estas opciones.

#### Vista de Cuadrícula
- Muestra el horario del aula seleccionada en una grilla de 07:00 a 22:00 en franjas de 30 minutos.
- Cada bloque ocupa el espacio proporcional a su duración real.
- Los colores identifican cada curso (consistentes en todas las vistas y en el Excel exportado).
- Selecciona el aula con el selector desplegable en la parte superior.

#### Por Aula
- Lista todos los grupos ordenados por aula, día y hora.
- **Buscar**: filtra por nombre de aula o código de grupo.
- **Ordenar**: clic en encabezado de columna.
- **Editar / Eliminar**: mismos botones que en Lista Detallada.

#### Ver Resumen
Haz clic en **Ver Resumen** para ver:
- Tarjetas con grupos asignados (y porcentaje), sin asignar, aulas utilizadas y cursos programados.
- Tabla de grupos por día.
- Tabla de grupos por aula (ordenada de mayor a menor carga).
- Lista de grupos sin asignar (si los hay).

---

### Paso 8 - Exportar resultados

1. Elige **Exportar todas las asignaciones** o **Exportar filtrado (N)** según el alcance que necesitas.
2. Elige el formato y la ubicación:
   - **Excel (`.xlsx`)**: incluye una hoja por aula con grilla visual, más hojas de lista detallada y por aula. Conserva la identidad y los patrones de los cursos con una paleta estable para papel blanco; los tonos de pantalla se adaptan al tema.
   - **CSV (`.csv`)**: lista detallada en formato plano.
   - **PDF (`.pdf`)**: tablas cronológicas por aula listas para imprimir, con texto seleccionable, horas exactas, nombres completos, páginas y encabezados repetidos. No necesita Excel. El documento identifica el alcance, filtros aplicados, pendientes globales y excepciones LAB.
3. Haz clic en **Guardar**.

---

### Consulta y exportación

La versión actual distingue **Exportar todas las asignaciones** y **Exportar filtrado (N)**:

- **Buscar** combina todas las palabras sin distinguir mayúsculas ni acentos. Los filtros compartidos **Aula**, **Día** y **Estado** se aplican a las tres vistas.
- **Restablecer filtros** vacía Buscar y devuelve Aula, Día y Estado a sus opciones generales.
- **Exportar todas las asignaciones** y **Ctrl+S** incluyen todas las sesiones asignadas, independientemente de los filtros.
- **Exportar filtrado (N)** incluye solo las sesiones asignadas que cumplen los filtros compartidos. N indica la cantidad; el diálogo de guardado y el mensaje final también muestran alcance y cantidad.
- Las sesiones **Sin asignar** se consultan en Lista detallada y no se exportan como filas de horario. Sin coincidencias asignadas, la exportación filtrada no está disponible.
- Cambiar de pestaña o elegir un aula en el selector local de la cuadrícula no restringe la exportación. Para exportar un aula, usa el filtro compartido **Aula**.
- Ambas opciones permiten Excel, CSV o PDF. Durante la generación o cuando los datos cambian e invalidan el horario, no están disponibles. Cancelar el guardado conserva los filtros y el horario.

---

El PDF conserva el total global de sesiones asignadas y pendientes incluso al exportar sólo una vista filtrada. Las etiquetas, días y leyenda del documento siguen el idioma seleccionado; los nombres e identificadores de los datos no se traducen. Los acentos, griego y cirílico se incluyen mediante una fuente incrustada; escrituras o glifos no compatibles se rechazan sin modificar un destino existente. En ese caso, usa Excel o CSV. El PDF se genera primero en memoria y reemplaza el destino sólo al terminar correctamente. Consulta [Notas de exportación PDF](PDF_EXPORT_NOTES.md) para los límites de impresión y Unicode.

## 5. Formato del Excel de entrada

### Hoja `Aulas`

| # DE AULA | DESCRIPCIÓN | CAMPUS | CAPACIDAD | CAPACIDAD 80% |
|-----------|-------------|--------|-----------|---------------|
| L-DEMO-1 | Laboratorio de ejemplo | DEMO | 16 | 13 |
| A-DEMO-1 | Aula General | DEMO | 60 | 48 |
| A-DEMO-2 | Aula General | DEMO | 60 | 48 |

- Aulas cuyo código comienza con `L`: tipo **LAB**.
- El resto: tipo **REGULAR**.
- La columna `CAPACIDAD 80%` es opcional e informativa.
- Las celdas importadas con errores de Excel (por ejemplo `#N/A` o `#DIV/0!`) se rechazan indicando hoja y celda. Corrige el error y guarda el libro de nuevo. No se calculan fórmulas durante la importación.
- Si usas fórmulas, recalcula y guarda el libro en Excel antes de importar, o pega los valores. Una fórmula sin resultado guardado se lee como una celda vacía.
- Guarda como texto los códigos con ceros iniciales, como `001`, y usa exactamente el mismo código en ambas hojas.
- Aulas referenciadas en `Cursos` que no existen aquí se ignoran (el grupo queda sin preferencia de aula).

### Hoja `Cursos`

| Curso   | Nombre de Curso  | Cantidad de Grupos | Horas     | Aula   | Días |
|---------|------------------|--------------------|-----------|--------|------|
| DEM101  | Pensamiento lógico (ejemplo) | -                  | 0800-1030 | A-DEMO-2   | L    |
| DEM101  | Pensamiento lógico (ejemplo) | -                  | 1000-1230 | A-DEMO-1   | M    |
| DEM111L | Laboratorio de modelos (ejemplo)  | -                  | 0700-0930 | L-DEMO-1 | I    |

- **Cada fila = un grupo sugerido**. Dos filas con el mismo código = 2 grupos distintos. La cantidad se obtiene contando filas; la columna `Cantidad de Grupos` no determina ese número.
- `Horas`: formato `HHMM-HHMM` (ej: `0800-1055`). Vacío o `-` = sin preferencia de hora.
- `Días`: `L`=Lunes, `I`=Martes, `M`=Miércoles, `J`=Jueves, `V`=Viernes, `S`=Sábado.
- `Aula` y `Días` son opcionales.

---

## 6. Comportamiento del algoritmo

- El sistema usa una heurística greedy con reintentos: no garantiza solución completa u óptima ni demuestra inviabilidad. Intenta respetar las preferencias de aula, día y hora indicadas en el Excel.
- En generación automática, LAB requiere laboratorio. Una asignación manual a aula regular necesita una excepción confirmada y registrada; las demás restricciones siguen vigentes.
- Si no hay espacio disponible en el slot preferido, el grupo se asigna en otro horario (preferencias blandas).
- El horario cubre de **07:00 a 22:00**, excluyendo el almuerzo (12:00-13:00).
- Cursos con duración mayor a 4.5 horas se dividen automáticamente en sesiones para días distintos. Se usan bloques de 2 horas; un resto menor de 1 hora se incorpora al bloque anterior. Puedes cambiar este comportamiento por curso desde el campo **División en días** al editar el curso.
- La reproducibilidad requiere los mismos cursos, aulas, restricciones, semilla y versión del programa. Un cambio en esos datos puede cambiar el horario.

---

## 7. Persistencia de datos

SORTH guarda automáticamente la sesión en la carpeta de datos del usuario: `%LOCALAPPDATA%/SORTH/sorth_session.db` en Windows. No se guarda junto al ejecutable en las versiones actuales. Consulta [Guardado y recuperación](SESSION_RECOVERY.md) para las rutas de otras plataformas, migración y copias.

Al abrir, acepta restaurar para recuperar cursos, aulas, restricciones, asignaciones, excepciones LAB, ruta del Excel y semilla. Rechazar la restauración no borra la sesión anterior; antes de sustituirla al editar, SORTH intenta crear una copia independiente.

**Sin cambios pendientes** confirma el último guardado. Si aparece **Cambios sin guardar**, corrige espacio/permisos y usa **Reintentar**. Al cerrar con un error puedes reintentar, cancelar el cierre o descartar cambios no guardados. Una exportación no sustituye el respaldo completo de la sesión. Ante **Sesión no disponible**, sigue la guía de recuperación y conserva los archivos; no borres la base para forzar el inicio.

La base, sus copias, el Excel y las exportaciones pueden contener información privada. Protégelos y no los adjuntes a issues públicos. Consulta [Privacidad](../../PRIVACY.md).

---

## 8. Problemas frecuentes

### No se pudo generar un horario válido
**Causas posibles:**
- No hay aulas disponibles para algún tipo de curso.
- Restricciones de aula demasiado estrictas.

**Qué hacer:**
- Revisar que existan aulas suficientes en la hoja `Aulas`.
- Corregir restricciones de aulas sólo si no representan los requisitos reales.
- Agregar aulas adicionales con el botón **Agregar aula**.

### Algunos grupos quedan sin asignar
Consulta **Estado: Sin asignar** en Lista detallada y lee el motivo. Puede faltar un laboratorio compatible, capacidad o un hueco permitido, o la heurística puede no haber encontrado una combinación. Revisa datos y restricciones; prueba otra semilla o una asignación manual válida. No elimines un requisito real sólo para completar el horario.

### Error al cargar Excel
**Qué hacer:**
- Verificar que las hojas se llamen exactamente `Aulas` y `Cursos` (con mayúscula inicial).
- Cerrar el archivo si está abierto en Excel.
- Verificar que el archivo no esté dañado.

### Error al exportar
**Qué hacer:**
- Cerrar el archivo de salida si ya estaba abierto en Excel.
- Guardar en otra carpeta con permisos de escritura.

---

## 9. Recomendaciones

- Cargar el Excel antes de agregar cursos manualmente para no perder los datos importados.
- Usar semilla fija para resultados reproducibles; cambiar la semilla si el resultado no es satisfactorio.
- Configurar las restricciones de aulas **antes** de generar el horario.
- Exportar el resultado si se necesita compartirlo o archivarlo; elegir Excel, CSV o PDF según el uso.
- Mantener una copia de respaldo del Excel original.

---

## 10. Cierre

Para salir, espera a que termine cualquier generación y cierra la ventana de la aplicación. SORTH intenta guardar la sesión al cerrar. Exporta los resultados que quieras conservar y mantén una copia del Excel original; la restauración depende de que el archivo de sesión se haya guardado correctamente.

---

## 11. Repositorio y documentación

El código fuente y la documentación se encuentran en el [repositorio de SORTH](https://github.com/RodrigoUC/SORTH-AI).

### Generar el PDF desde el código fuente

`docs/user/MANUAL_USUARIO.md` (desde la raíz del repositorio) es la fuente editable. El PDF se genera desde ella; no edites ni reutilices copias históricas del PDF. Para prepararlo, abre una terminal en `project_root`, activa un entorno virtual e instala las dependencias de documentación:

```console
python -m pip install -r requirements-docs.txt
python tools/build_manual.py --output build/docs/MANUAL_USUARIO.pdf
```

El generador no descarga recursos. Produce un PDF con tablas, enlaces y páginas numeradas. Si se ejecuta sin `--output`, utiliza la misma carpeta `build/docs` del proyecto. Los documentos enlazados con rutas relativas apuntan a la documentación del repositorio en la rama `main`; abrir esos enlaces requiere conexión.

Antes de distribuir el manual, revisa el PDF generado y confirma que corresponde al mismo código que la aplicación. El archivo generado es un artefacto de compilación y no debe sustituir la fuente Markdown.

## Ejemplo incluido

`data/input/Cursos_Ejemplo.xlsx` contiene 8 aulas ficticias y 12 cursos de demostración. Sus 36 grupos producen 42 sesiones al dividir los proyectos largos. Todos los datos son sintéticos; no corresponden a una institución. La procedencia se describe en `data/input/PROVENANCE.md` (rutas relativas a `project_root`).
