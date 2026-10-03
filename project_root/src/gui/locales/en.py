"""en presentation catalog. Keep keys stable; edit values to revise wording."""

MESSAGES = {
    'El PDF filtrado requiere el total global de asignaciones.': 'A filtered PDF requires the global assignment count.',
    'El alcance y el total de asignaciones no coinciden.': 'The scope and assignment count do not match.',
    'El número de sesiones pendientes no puede ser negativo.': 'The pending session count cannot be negative.',
    'El PDF no admite algunos caracteres o escrituras de los datos. Use Excel/CSV para conservarlos.': 'The PDF does not support some characters or scripts in the data. Use Excel/CSV to preserve them.',
    'Vista filtrada': 'Filtered view',
    'Todas las asignaciones': 'All assignments',
    'Estado global: pendientes no informados': 'Global status: pending count not provided',
    'Horario PARCIAL: {pending} pendientes': 'PARTIAL schedule: {pending} pending',
    'Horario completo: 0 pendientes': 'Complete schedule: 0 pending',
    '{scope} | {count} exportadas de {total} asignadas | {state}': '{scope} | {count} exported of {total} assigned | {state}',
    'SORTH - Horario por aula': 'SORTH - Classroom timetable',
    'SORTH {version} | Horario por aula': 'SORTH {version} | Classroom timetable',
    'Horas exactas HH:mm | Texto seleccionable | SORTH': 'Exact times HH:mm | Selectable text | SORTH',
    'Página {page}': 'Page {page}',
    'Un texto es demasiado largo para la página PDF.': 'Text is too long for the PDF page.',
    'No aplicados (se exportan todas las asignaciones).': 'Not applied (all assignments are exported).',
    'Filtros no informados por el solicitante.': 'Filters not provided by the caller.',
    'Alcance y leyenda': 'Scope and legend',
    'Filtros: {filters}': 'Filters: {filters}',
    'Un color por curso; los nombres completos aparecen en cada fila. CONFLICTO identifica sesiones simultáneas. EXCEPCIÓN LAB identifica una autorización de aula registrada. Continuación repite día, horas y grupo cuando un nombre ocupa varias páginas. Los pendientes corresponden al horario global, no sólo a esta vista.': 'One color per course; full names appear in every row. CONFLICT identifies simultaneous sessions. LAB EXCEPTION identifies a recorded classroom authorization. Continued repeats day, times and group when a name spans pages. Pending counts describe the global schedule, not only this view.',
    'Día no válido para {group}.': 'Invalid day for {group}.',
    'Sin sesiones asignadas en este alcance.': 'No assigned sessions in this scope.',
    'Aula: {room} | Sesiones: {count}': 'Classroom: {room} | Sessions: {count}',
    'El nombre del aula es demasiado largo para el encabezado PDF.': 'The classroom name is too long for the PDF header.',
    'Inicio - Fin': 'Start - End',
    'Nombre completo del curso': 'Full course name',
    'Avisos': 'Notices',
    'CONFLICTO': 'CONFLICT',
    'EXCEPCIÓN LAB': 'LAB EXCEPTION',
    '(Sin nombre de curso)': '(No course name)',
    'Continuación': 'Continued',
    'Buscar': 'Search',
    '(sin búsqueda)': '(no search)',
    'Guardar el horario generado en Excel (.xlsx), CSV o PDF.\nEl Excel incluye una grilla visual; el PDF, tablas por aula para imprimir.': 'Save the generated schedule as Excel (.xlsx), CSV or PDF.\nExcel includes a visual grid; PDF has printable classroom tables.',
    "Archivos Excel (*.xlsx);;Archivos CSV (*.csv);;Documentos PDF (*.pdf)": 'Excel files (*.xlsx);;CSV files (*.csv);;PDF documents (*.pdf)',
    'El libro supera el límite de importación. Divídalo en archivos más pequeños.': 'The workbook exceeds the import limit. Split it into smaller files.',
    '⚠️ Horario parcial: {p1}/{p3} grupos; {pending} pendientes': '⚠️ Partial schedule: {p1}/{p3} groups; {pending} pending',
    'Sin resultado': 'No result',
    'No se obtuvo un resultado. Revise los datos y vuelva a generar el horario.': 'No result was produced. Review the inputs and generate the schedule again.',

    '{scope} · horario parcial, {pending} pendientes': '{scope} · partial schedule, {pending} pending',
    '{gid}: identificador de grupo duplicado': '{gid}: duplicate group identifier',
    '{gid}: asignación mal formada': '{gid}: malformed assignment',
    'Exportar todas las asignaciones': 'Export all assignments',
    'todas las asignaciones': 'all assignments',

    "\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.": "\n\nReview the details before continuing. Cancel keeps the current session.",
    "\n⚠️  {p1} grupo(s) sin asignar.\nRevisa la Lista Detallada (marcados en rojo).": "\n⚠️  Unassigned groups: {p1}.\nReview the Detailed list (highlighted in red).",
    "  {p1}  {p3}": "  {p1}  {p3}",
    "  ·  Cargue un Excel para comenzar": "  ·  Load an Excel file to get started",
    "  ·  Listo para generar": "  ·  Ready to generate",
    "  ·  {p1}/{p3} sesiones asignadas": "  ·  {p1}/{p3} sessions assigned",
    "  ⚠️  {p1}": "  ⚠️  {p1}",
    "  💾  Sesión anterior encontrada": "  💾  Previous session found",
    " Consulte las sesiones sin asignar en Lista detallada.": " View unassigned sessions in Detailed list.",
    " · {p1} tramo(s) con conflicto": " · Conflicting intervals: {p1}",
    "&Aula:": "&Classroom:",
    "&Buscar:": "&Search:",
    "&Día:": "&Day:",
    "&Estado:": "S&tatus:",
    "(Sin preferencia)": "(No preference)",
    ". No hay coincidencias; cambie o restablezca los filtros.": ". No matches; change or reset the filters.",
    "1. Cargue un Excel con las hojas Aulas y Cursos (nombres exactos).\n2. Revise los cursos y configure aulas o restricciones.\n3. Genere el horario, revise los grupos pendientes y exporte.": "1. Load an Excel file with sheets named Aulas and Cursos (exact names).\n2. Review courses and configure classrooms or restrictions.\n3. Generate the schedule, review unassigned sessions and export.",
    "Abrir": "Open",
    "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: # DE AULA y CAPACIDAD (entero ≥ 0)\n  • Cursos: Curso; cada fila es un grupo sugerido\nOpcionales: Nombre de Curso, Horas (0800-1055), Aula y Días (L,I,M,J,V,S).\nLos encabezados van en la fila 1; el orden de columnas no importa.": "Open an Excel file (.xlsx) with these sheets:\n  • Aulas: # DE AULA and CAPACIDAD (integer ≥ 0)\n  • Cursos: Curso; each row is a suggested group\nOptional: Nombre de Curso, Horas (0800-1055), Aula and Días (L,I,M,J,V,S).\nHeaders belong in row 1; column order does not matter.",
    "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: código, descripción, campus, capacidad\n  • Cursos: cada fila es un grupo sugerido": "Open an Excel file (.xlsx) with these sheets:\n  • Aulas: code, description, campus, capacity\n  • Cursos: each row is a suggested group",
    "Aceptar": "OK",
    "Activar hora preferida": "Enable preferred time",
    "Activar para usar una semilla aleatoria en cada generación": "Use a random seed each time a schedule is generated",
    "Active un aula para restringirla. Luego marque los cursos que pueden usarla (los desmarcados quedan libres).": "Enable a classroom to restrict it. Then select the courses that may use it (unchecked courses remain unrestricted).",
    "Advertencia": "Warning",
    "Agregar Aula": "Add Classroom",
    "Agregar Curso": "Add Course",
    "Agregar aula": "Add classroom",
    "Agregar un aula nueva a la sesión actual.\nÚtil para aulas que no están en el Excel pero deben estar disponibles.": "Add a classroom to the current session.\nUseful for classrooms that are not in the Excel file but must be available.",
    "Agregar un nuevo curso manualmente a la lista": "Manually add a new course to the list",
    "Aleatoria": "Random",
    "Archivo Excel:": "Excel file:",
    "Asignaciones ordenadas por aula": "Assignments sorted by classroom",
    "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual.": "Previous regular-classroom assignment removed: a manual exception must be confirmed.",
    "Asignado": "Assigned",
    "Asignados": "Assigned",
    "Asignar": "Assign",
    "Asignar manualmente": "Assign manually",
    "Asignar sesión manualmente": "Assign session manually",
    "Aula": "Classroom",
    "Aula Sugerida": "Suggested classroom",
    "Aula Sugerida:": "Suggested classroom:",
    "Aula de la &cuadrícula:": "&Grid classroom:",
    "Aula de la cuadrícula": "Grid classroom",
    "Aulas con Restricciones": "Classroom Restrictions",
    "Aulas utilizadas": "Classrooms used",
    "Aulas utilizadas:    {p1}": "Classrooms used:     {p1}",
    "Aulas, fila {row}: '{room}' no tiene capacidad; se usará 0.": "Aulas, row {row}: '{room}' has no capacity; 0 will be used.",
    "Aulas, fila {row}: CAPACIDAD debe ser un entero mayor o igual a 0.": "Aulas, row {row}: CAPACIDAD must be an integer greater than or equal to 0.",
    "Aulas, fila {row}: el aula '{room}' está duplicada.": "Aulas, row {row}: classroom '{room}' is duplicated.",
    "Aulas, fila {row}: falta # DE AULA.": "Aulas, row {row}: missing # DE AULA.",
    "Aulas:": "Classrooms:",
    "Aulas: agregue al menos un aula con # DE AULA.": "Aulas: add at least one classroom with # DE AULA.",
    "Automático (dividir si > 4.5h)": "Automatic (split if > 4.5 h)",
    "Automático: se divide solo si la duración supera 4.5 horas.\nForzar división: siempre se divide en bloques de 2h en días distintos.\nNo dividir: se asigna completo en un solo día sin importar la duración.": "Automatic: split only when duration exceeds 4.5 hours.\nForce split: split into 2-hour blocks on different days.\nDo not split: assign the full duration on one day.",
    "Avisos del archivo: {count}": "File warnings: {count}",
    "Aún no hay cursos. Cargue un Excel o agregue su primer curso.": "No courses yet. Load an Excel file or add your first course.",
    "Buscar cursos": "Search courses",
    "Buscar en todo el horario": "Search the entire schedule",
    "Buscar por código o nombre de curso…": "Search by course code or name…",
    "Cambiar idioma sin modificar los datos ni los formatos de exportación": "Change language without modifying data or export formats",
    "Cambios sin guardar": "Unsaved changes",
    "Campus:": "Campus:",
    "Cancelar": "Cancel",
    "Capacidad *:": "Capacity *:",
    "Cargar Excel": "Load Excel",
    "Cargue un Excel o agregue al menos un aula primero.": "Load an Excel file or add at least one classroom first.",
    "Cargue un Excel o agregue cursos y aulas para comenzar.": "Load an Excel file or add courses and classrooms to get started.",
    "Cerrar": "Close",
    "Configurar qué aulas están reservadas exclusivamente para ciertos cursos.\nLos cursos restringidos SOLO pueden asignarse a su aula designada.": "Configure classrooms reserved exclusively for particular courses.\nRestricted courses can ONLY be assigned to their designated classroom.",
    "Confirmar": "Confirm",
    "Confirmar eliminación": "Confirm deletion",
    "Confirmar excepción de laboratorio": "Confirm laboratory exception",
    "Conflicto de aula\n": "Classroom conflict\n",
    "Controla la aleatoriedad del algoritmo.\nSemilla fija → mismo horario cada vez (reproducible).\nSemilla aleatoria → resultados distintos en cada ejecución.": "Controls the scheduling algorithm's randomness.\nFixed seed → same schedule each time (reproducible).\nRandom seed → different results each run.",
    "Corrija el archivo y vuelva a cargarlo:": "Correct the file and load it again:",
    "Cuadrícula por aula": "Classroom grid",
    "Cuadrícula semanal por aula": "Weekly classroom grid",
    "Curso ya existe": "Course already exists",
    "Cursos a programar": "Courses to schedule",
    "Cursos para {p1}:": "Courses for {p1}:",
    "Cursos programados": "Scheduled courses",
    "Cursos programados:  {p1}": "Courses scheduled:   {p1}",
    "Cursos, fila {row}: Días admite L, I, M, J, V, S separados por comas; I=martes y M=miércoles.": "Cursos, row {row}: Días accepts L, I, M, J, V, S separated by commas; I=Tuesday and M=Wednesday.",
    "Cursos, fila {row}: Horas debe ser HHMM-HHMM, con fin posterior al inicio (ej. 0800-1055).": "Cursos, row {row}: Horas must be HHMM-HHMM, ending after the start (e.g. 0800-1055).",
    "Cursos, fila {row}: el aula '{room}' no aparece en Aulas; se importará sin esa preferencia.": "Cursos, row {row}: classroom '{room}' is not listed in Aulas; this preference will not be imported.",
    "Cursos, fila {row}: falta Curso (código).": "Cursos, row {row}: missing Curso (code).",
    "Cursos: agregue al menos una fila con Curso (código).": "Cursos: add at least one row with Curso (code).",
    "Código": "Code",
    "Código *:": "Code *:",
    "Código del Curso:": "Course code:",
    "Código, nombre de curso, grupo o aula": "Code, course name, group or classroom",
    "Datos actualizados. Genere un nuevo horario para exportar.": "Data updated. Generate a new schedule to export.",
    "Dejar la sesión seleccionada sin asignar": "Leave the selected session unassigned",
    "Desactiva las transiciones y el indicador animado.": "Disable transitions and the animated indicator.",
    "Descartar": "Discard",
    "Descripción:": "Description:",
    "Desmarcar todos": "Deselect all",
    "Detectado automáticamente por el código (L al inicio → LAB).\nPuedes cambiarlo manualmente si es necesario.": "Detected automatically from the code (starts with L → LAB).\nYou can change it manually if needed.",
    "División en días:": "Split across days:",
    "Domingo": "Sunday",
    "Duplicado": "Duplicate",
    "Duración": "Duration",
    "Duración:": "Duration:",
    "Día": "Day",
    "Día Preferido": "Preferred day",
    "Día Preferido:": "Preferred day:",
    "Editar Curso": "Edit Course",
    "Editar curso": "Edit course",
    "Editar curso {p1}": "Edit course {p1}",
    "Editar el curso de la sesión seleccionada; será necesario generar de nuevo": "Edit the selected session's course; a new schedule must be generated",
    "Editar el curso seleccionado en la tabla": "Edit the selected course",
    "Ej: Aula General": "E.g.: General Classroom",
    "Ej: Biología General (opcional)": "E.g.: General Biology (optional)",
    "Ej: HO": "E.g.: HO",
    "Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.": "Run the scheduling algorithm with the loaded courses and classrooms.\nThe result appears in the Generated Schedule tab.",
    "El aula '{p1}' ya existe.": "Classroom '{p1}' already exists.",
    "El curso '{p1}' ya existe en la lista.\n¿Deseas modificarlo en su lugar?": "Course '{p1}' already exists in the list.\nWould you like to edit it instead?",
    "El curso {p1} no se encuentra en la lista de cursos.": "Course {p1} was not found in the course list.",
    "El código del aula es obligatorio.": "A classroom code is required.",
    "El código del curso es obligatorio.": "A course code is required.",
    "Eliminar el curso seleccionado de la lista": "Remove the selected course from the list",
    "Eliminar todas las asignaciones del horario actual": "Remove every assignment from the current schedule",
    "Eliminar todos los cursos de la lista": "Remove every course from the list",
    "En curso": "In progress",
    "Error": "Error",
    "Error al cargar archivo Excel:\n{p1}": "Error loading Excel file:\n{p1}",
    "Error al exportar:\n{p1}": "Error exporting:\n{p1}",
    "Error al generar el horario:\n{p1}": "Error generating schedule:\n{p1}",
    "Espere a que termine la generación antes de cerrar.": "Wait for schedule generation to finish before closing.",
    "Estado": "Status",
    "Estado de guardado": "Save status",
    "Excepción manual LAB": "Manual LAB exception",
    "Excepción manual confirmada: laboratorio en aula regular.": "Confirmed manual exception: laboratory session in a regular classroom.",
    "Exportar completo": "Export all",
    "Exportar completo incluye todas las asignaciones. Exportar filtrado usa Buscar, Aula, Día y Estado; no el aula de la cuadrícula.": "Export all includes every assignment. Export filtered uses Search, Classroom, Day and Status, not the grid's classroom selector.",
    "Exportar filtrado (0)": "Export filtered (0)",
    "Exportar filtrado ({p1})": "Export filtered ({p1})",
    "Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.": "Export {p1} assigned sessions matching Search, Classroom, Day and Status.\nThe active tab and the grid's classroom selector do not change this set.",
    "Faltan las hojas: {missing}. Use esos nombres exactos. Hojas encontradas: {found}": "Missing sheets: {missing}. Use these exact names. Sheets found: {found}",
    "Filtrar por aula": "Filter by classroom",
    "Filtrar por día": "Filter by day",
    "Filtrar por estado": "Filter by status",
    "Fin": "End",
    "Forzar división en varios días": "Force split across days",
    "Generando…": "Generating…",
    "Generar horario": "Generate schedule",
    "Genere un horario para consultar sus sesiones y exportar los resultados.": "Generate a schedule to view its sessions and export the results.",
    "Grupo": "Group",
    "Grupo / sesión": "Group / session",
    "Grupos": "Groups",
    "Grupos asignados:    {p1} / {p3}": "Groups assigned:     {p1} / {p3}",
    "Guardar": "Save",
    "Guardar el horario generado en formato Excel (.xlsx) o CSV.\nEl Excel incluye una grilla visual por aula.": "Save the generated schedule as Excel (.xlsx) or CSV.\nThe Excel file includes a visual grid for each classroom.",
    "Guardar horario {p1} · {p3} sesiones": "Save {p1} schedule · {p3} sessions",
    "Guía rápida": "Quick guide",
    "Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.": "Sheet {sheet}, row 1: duplicate columns: {columns}. Keep only one column of each type.",
    "Hoja {sheet}, fila 1: falta la columna {columns}. Revise el encabezado.": "Sheet {sheet}, row 1: missing column {columns}. Check the header.",
    "Hoja {sheet}: agregue los encabezados en la fila 1.": "Sheet {sheet}: add column headers in row 1.",
    "Hora": "Time",
    "Hora Preferida": "Preferred time",
    "Hora Preferida:": "Preferred time:",
    "Hora de inicio preferida para este curso (ej: 08:00, 13:00)": "Preferred start time for this course (e.g.: 08:00, 13:00)",
    "Horario eliminado.": "Schedule cleared.",
    "Horario no válido": "Invalid schedule",
    "Horario {p1}: {p3} sesiones exportadas a {p5}": "{p1} schedule: {p3} sessions exported to {p5}",
    "Horario {p1}: {p3} sesiones exportadas a:\n{p5}": "{p1} schedule: {p3} sessions exported to:\n{p5}",
    "Idioma de la interfaz": "Interface language",
    "Idioma:": "Language:",
    "Importar con avisos": "Import with warnings",
    "Info": "Information",
    "Inicio": "Start",
    "Jueves": "Thursday",
    "La búsqueda automática no encontró un horario compatible con las asignaciones actuales. Esto no demuestra que sea imposible; revise horarios, restricciones o asigne manualmente.": "The automatic search found no schedule compatible with the current assignments. This does not prove it is impossible; review times and restrictions, or assign manually.",
    "La duración no cabe en el horario permitido sin cruzar el almuerzo.": "The duration does not fit the permitted hours without overlapping lunch.",
    "Las restricciones de cursos excluyen todas las aulas compatibles.": "Course restrictions exclude every compatible classroom.",
    "Libro de Excel (*.xlsx)": "Excel Workbook (*.xlsx)",
    "Limpiar horario": "Clear schedule",
    "Lista detallada": "Detailed list",
    "Lista detallada del horario": "Detailed schedule list",
    "Listo. Cargue un archivo Excel para comenzar.": "Ready. Load an Excel file to get started.",
    "Lunes": "Monday",
    "Marcar todos": "Select all",
    "Martes": "Tuesday",
    "Miércoles": "Wednesday",
    "Mostrando {p1} de {p3} sesiones": "Showing {p1} of {p3} sessions",
    "Mostrando {p1} de {p3} sesión": "Showing {p1} of {p3} session",
    "Motivo y excepciones de la sesión seleccionada": "Reason and exceptions for the selected session",
    "Ningún aula del tipo permitido tiene capacidad suficiente.": "No classroom of the permitted type has sufficient capacity.",
    "No": "No",
    "No dividir (asignar en un solo día)": "Do not split (assign on one day)",
    "No hay aulas con cursos asociados en el Excel.": "No classrooms have associated courses in the Excel file.",
    "No hay horario para exportar.": "There is no schedule to export.",
    "No hay laboratorios configurados. Puede elegir un aula regular manualmente y confirmar la excepción.": "No laboratories are configured. You can manually choose a regular classroom and confirm the exception.",
    "No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.": "No assigned sessions match these filters. Change or reset the filters.",
    "No se cargó el archivo. La sesión anterior se conserva.": "The file was not loaded. The previous session has been preserved.",
    "No se encontró el archivo. Selecciónelo nuevamente.": "The file was not found. Select it again.",
    "No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.": "Unable to open the file. Check its permissions or save an .xlsx copy.",
    "No se pudo generar un horario válido.\n\nPosibles causas:\n  • No hay suficientes aulas disponibles\n  • Restricciones demasiado estrictas\n  • Conflictos de horario entre cursos": "Unable to generate a valid schedule.\n\nPossible causes:\n  • Not enough available classrooms\n  • Overly strict restrictions\n  • Scheduling conflicts between courses",
    "No se pudo guardar la sesión. Si sales, perderás los cambios sin guardar.\nEl último guardado y las copias existentes se conservarán.\n\n{p1}": "Unable to save the session. If you exit, unsaved changes will be lost.\nThe last saved session and existing backups will be kept.\n\n{p1}",
    "No se pudo guardar la sesión: {p1}": "Unable to save the session: {p1}",
    "No se pudo guardar o recuperar la sesión: {p1}": "Unable to save or recover the session: {p1}",
    "No se pudo leer el libro. Ábralo en Excel y guarde una copia .xlsx sin contraseña.": "Unable to read the workbook. Open it in Excel and save an .xlsx copy without a password.",
    "Nombre": "Name",
    "Nombre del curso": "Course name",
    "Nombre:": "Name:",
    "Número de Grupos:": "Number of groups:",
    "Organización de horarios académicos": "Academic schedule organization",
    "Por aula": "By classroom",
    "Por favor agregue al menos un curso.": "Please add at least one course.",
    "Quitar del horario": "Remove from schedule",
    "Quitar sesión del horario": "Remove session from schedule",
    "Recuperación pendiente": "Recovery required",
    "Reducir animaciones": "Reduce animations",
    "Reintentar": "Retry",
    "Restablecer filtros": "Reset filters",
    "Restricciones de aulas": "Classroom restrictions",
    "Restricciones de aulas eliminadas.": "Classroom restrictions removed.",
    "Resultado de validación": "Validation result",
    "Resumen del Horario": "Schedule Summary",
    "Revisar importación": "Review import",
    "SORTH - Sistema de Organización de Horarios": "SORTH - Academic Schedule Organizer",
    "Se encontró una sesión guardada.\n¿Deseas restaurarla?": "A saved session was found.\nWould you like to restore it?",
    "Seleccionar archivo Excel": "Select Excel file",
    "Seleccione el aula, día y hora. Se comprobarán todas las restricciones.": "Select the classroom, day and time. All restrictions will be checked.",
    "Seleccione un aula": "Select a classroom",
    "Seleccione un aula.": "Select a classroom.",
    "Seleccione un curso para editar.": "Select a course to edit.",
    "Seleccione un curso para eliminar.": "Select a course to delete.",
    "Seleccione una fila para editar o quitar.": "Select a row to edit or remove.",
    "Semilla:": "Seed:",
    "Sesiones asignadas": "Assigned sessions",
    "Sesiones por aula": "Sessions by classroom",
    "Sesiones por día": "Sessions by day",
    "Sesiones sin asignar (ver Lista detallada)": "Unassigned sessions (see Detailed list)",
    "Sesión anterior": "Previous session",
    "Sesión no disponible": "Session unavailable",
    "Sin archivo seleccionado": "No file selected",
    "Sin asignar": "Unassigned",
    "Sin cambios pendientes": "All changes saved",
    "Sin coincidencias": "No matches",
    "Sin sesiones para esta aula y estos filtros.": "No sessions for this classroom and these filters.",
    "Sin solución": "No solution",
    "Sábado": "Saturday",
    "Sí": "Yes",
    "Tipo de Sala:": "Room type:",
    "Tipo de sala:": "Room type:",
    "Todas": "All",
    "Todos": "All",
    "Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).": "Use an .xlsx file. In Excel, choose Save As → Excel Workbook (.xlsx).",
    "Valor de semilla fija para resultados reproducibles": "Fixed seed value for reproducible results",
    "Valor: ": "Value: ",
    "Ver resumen": "View summary",
    "Ver, agregar, editar y eliminar los cursos a programar": "View, add, edit and remove courses to schedule",
    "Viernes": "Friday",
    "Visualizar el horario generado en lista, cuadrícula o por aula": "View the generated schedule as a list, grid or by classroom",
    "classroom_count": {
        "one": "{n} classroom",
        "other": "{n} classrooms"
    },
    "completo": "complete",
    "course_count": {
        "one": "{n} course",
        "other": "{n} courses"
    },
    "filtrado": "filtered",
    "placeholder.classroom_code": "E.g.: A-DEMO-1, L-DEMO-1",
    "placeholder.course_code": "E.g.: DEM101, DEM111L",
    "placeholder.preferred_classroom": "E.g.: A-DEMO-1, L-DEMO-1 (optional)",
    "result_count": {
        "one": "Showing {visible} of {n} session",
        "other": "Showing {visible} of {n} sessions"
    },
    "session_count": {
        "one": "{n} session",
        "other": "{n} sessions"
    },
    "{gid}: capacidad insuficiente": "{gid}: insufficient capacity",
    "{gid}: conflicto de aula": "{gid}: classroom conflict",
    "{gid}: duración incorrecta": "{gid}: incorrect duration",
    "{gid}: grupo o aula desconocido": "{gid}: unknown group or classroom",
    "{gid}: horario fuera del intervalo permitido": "{gid}: time outside the permitted interval",
    "{gid}: requiere laboratorio; falta confirmar la excepción manual": "{gid}: laboratory required; confirm the manual exception first",
    "{gid}: restricción de aula": "{gid}: classroom restriction",
    "{gid}: sesiones divididas deben usar días distintos y la misma hora": "{gid}: split sessions must use different days and the same start time",
    "{n} aula": "{n} classroom",
    "{n} aulas": "{n} classrooms",
    "{n} curso": "{n} course",
    "{n} cursos": "{n} courses",
    "{n} sesiones": "{n} sessions",
    "{n} sesión": "{n} session",
    "{p0} cursos  ·  {p2} sesiones  ·  {p4} aulas": "{p0} courses  ·  {p2} sessions  ·  {p4} classrooms",
    "{p0} requiere laboratorio. ¿Asignarlo al aula regular {p2}?\nEsta excepción manual quedará registrada en la sesión.": "{p0} requires a laboratory. Assign it to regular classroom {p2}?\nThis manual exception will be recorded in the session.",
    "{p0} sesiones asignadas · {p2} sin asignar · {p4} aulas utilizadas": "{p0} sessions assigned · {p2} unassigned · {p4} classrooms used",
    "{p0} sesiones{p2}. Horas exactas en cada bloque; detalle completo al señalarlo.": "Sessions: {p0}{p2}. Exact times in each block; hover for full details.",
    "{p0} · {p2} min · {p4} estudiantes": "{p0} · {p2} min · Students: {p4}",
    "¿Eliminar el curso {p1}?": "Delete course {p1}?",
    "¿Eliminar todas las asignaciones del horario actual?\nSe conservarán los cursos y las aulas para generar un horario nuevo.": "Remove every assignment from the current schedule?\nCourses and classrooms will be kept to generate a new schedule.",
    "¿Eliminar todos los cursos de la lista?\nEsta acción no se puede deshacer.": "Remove every course from the list?\nThis action cannot be undone.",
    "¿Quitar {p1} del horario?\nLa sesión quedará sin asignar y no se exportará.": "Remove {p1} from the schedule?\nThe session will be unassigned and will not be exported.",
    "Éxito": "Success",
    "… y {count} errores más.": "… and {count} more errors.",
    "⏳ Generando horario...": "⏳ Generating schedule...",
    "⚠️ No se pudo restaurar la sesión: {p1}": "⚠️ Unable to restore the session: {p1}",
    "✅ Aula '{p1}' agregada ({p3}, cap={p5})": "✅ Classroom '{p1}' added ({p3}, capacity={p5})",
    "✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)": "✅ Excel loaded: {p1}  ({p3} classrooms, {p5} courses)",
    "✅ Horario generado: {p1}/{p3} grupos": "✅ Schedule generated: {p1}/{p3} groups",
    "✅ Sesión restaurada correctamente.": "✅ Session restored successfully.",
    "✅ {p1} aula(s) con restricciones configuradas.": "✅ Classrooms with configured restrictions: {p1}.",
    "✏️ Editar": "✏️ Edit",
    "❌ Error al generar horario": "❌ Error generating schedule",
    "❌ No se pudo generar el horario": "❌ Unable to generate the schedule",
    "➕ Agregar Curso": "➕ Add Course",
    "🏫 REGULAR (detectado automáticamente)": "🏫 REGULAR (automatically detected)",
    "📅 Horario Generado": "📅 Generated Schedule",
    "📚 Gestión de Cursos": "📚 Course Management",
    "🔒 Aulas con Restricciones": "🔒 Classroom restrictions",
    "🔒 Restricciones ({p1})": "🔒 Restrictions ({p1})",
    "🔬 LAB (detectado automáticamente)": "🔬 LAB (automatically detected)",
    "🗑️ Eliminar": "🗑️ Delete",
    "🧹 Limpiar Todo": "🧹 Clear All"
}

QT_MESSAGES = {}

# Explainable schedule quality indicators.
MESSAGES.update({'No aplica': 'Not applicable',
 'Calidad del horario completo': 'Whole-schedule quality',
 'Los filtros no cambian estos indicadores. Son descriptivos: no validan restricciones ni demuestran un óptimo.': 'Filters '
                                                                                                                  'do '
                                                                                                                  'not '
                                                                                                                  'change '
                                                                                                                  'these '
                                                                                                                  'indicators. '
                                                                                                                  'They '
                                                                                                                  'are '
                                                                                                                  'descriptive: '
                                                                                                                  'they '
                                                                                                                  'do '
                                                                                                                  'not '
                                                                                                                  'validate '
                                                                                                                  'constraints '
                                                                                                                  'or '
                                                                                                                  'prove '
                                                                                                                  'optimality.',
 'Grupos originales: {complete} completos, {partial} parciales, {pending} pendientes y {unknown} desconocidos, de {total}. Las preferencias cuentan cada sesión dividida por separado.': 'Original '
                                                                                                                                                                                         'groups: '
                                                                                                                                                                                         '{complete} '
                                                                                                                                                                                         'complete, '
                                                                                                                                                                                         '{partial} '
                                                                                                                                                                                         'partial, '
                                                                                                                                                                                         '{pending} '
                                                                                                                                                                                         'pending '
                                                                                                                                                                                         'and '
                                                                                                                                                                                         '{unknown} '
                                                                                                                                                                                         'unknown, '
                                                                                                                                                                                         'out '
                                                                                                                                                                                         'of '
                                                                                                                                                                                         '{total}. '
                                                                                                                                                                                         'Preferences '
                                                                                                                                                                                         'count '
                                                                                                                                                                                         'each '
                                                                                                                                                                                         'split '
                                                                                                                                                                                         'session '
                                                                                                                                                                                         'separately.',
 'Día preferido': 'Preferred day',
 'Hora preferida': 'Preferred time',
 'Aula preferida': 'Preferred room',
 'Preferencia': 'Preference',
 'Pendientes': 'Pending',
 'Desconocidas': 'Unknown',
 'Sin preferencia': 'No preference',
 'Coincidencia exacta de día, hora de inicio y aula. El denominador incluye sólo preferencias asignadas y conocidas; pendientes, desconocidas y ausentes se muestran aparte. Sin denominador: no aplica.': 'Exact '
                                                                                                                                                                                                           'match '
                                                                                                                                                                                                           'for '
                                                                                                                                                                                                           'day, '
                                                                                                                                                                                                           'start '
                                                                                                                                                                                                           'time '
                                                                                                                                                                                                           'and '
                                                                                                                                                                                                           'room. '
                                                                                                                                                                                                           'The '
                                                                                                                                                                                                           'denominator '
                                                                                                                                                                                                           'includes '
                                                                                                                                                                                                           'only '
                                                                                                                                                                                                           'assigned, '
                                                                                                                                                                                                           'known '
                                                                                                                                                                                                           'preferences; '
                                                                                                                                                                                                           'pending, '
                                                                                                                                                                                                           'unknown '
                                                                                                                                                                                                           'and '
                                                                                                                                                                                                           'absent '
                                                                                                                                                                                                           'preferences '
                                                                                                                                                                                                           'are '
                                                                                                                                                                                                           'shown '
                                                                                                                                                                                                           'separately. '
                                                                                                                                                                                                           'No '
                                                                                                                                                                                                           'denominator: '
                                                                                                                                                                                                           'not '
                                                                                                                                                                                                           'applicable.',
 'Distribución de carga por día': 'Load distribution by day',
 'Minutos de docencia': 'Teaching minutes',
 'Se suman minutos de cada sesión, incluso si son simultáneas. Se incluyen días sin carga; no se presupone que una distribución uniforme sea mejor.': 'Minutes '
                                                                                                                                                      'are '
                                                                                                                                                      'summed '
                                                                                                                                                      'for '
                                                                                                                                                      'every '
                                                                                                                                                      'session, '
                                                                                                                                                      'including '
                                                                                                                                                      'simultaneous '
                                                                                                                                                      'ones. '
                                                                                                                                                      'Days '
                                                                                                                                                      'with '
                                                                                                                                                      'no '
                                                                                                                                                      'load '
                                                                                                                                                      'are '
                                                                                                                                                      'included; '
                                                                                                                                                      'an '
                                                                                                                                                      'even '
                                                                                                                                                      'distribution '
                                                                                                                                                      'is '
                                                                                                                                                      'not '
                                                                                                                                                      'assumed '
                                                                                                                                                      'to '
                                                                                                                                                      'be '
                                                                                                                                                      'better.',
 'Ocupación temporal de aulas': 'Room time occupancy',
 'Minutos ocupados únicos / minutos disponibles, descontando almuerzo y exclusiones. Incluye aulas sin uso; no mide asientos ocupados ni compatibilidad de cursos.': 'Unique '
                                                                                                                                                                     'occupied '
                                                                                                                                                                     'minutes '
                                                                                                                                                                     '/ '
                                                                                                                                                                     'available '
                                                                                                                                                                     'minutes, '
                                                                                                                                                                     'excluding '
                                                                                                                                                                     'lunch '
                                                                                                                                                                     'and '
                                                                                                                                                                     'blocked '
                                                                                                                                                                     'intervals. '
                                                                                                                                                                     'Includes '
                                                                                                                                                                     'unused '
                                                                                                                                                                     'rooms; '
                                                                                                                                                                     'does '
                                                                                                                                                                     'not '
                                                                                                                                                                     'measure '
                                                                                                                                                                     'occupied '
                                                                                                                                                                     'seats '
                                                                                                                                                                     'or '
                                                                                                                                                                     'course '
                                                                                                                                                                     'eligibility.',
 'Minutos ocupados / disponibles': 'Occupied / available minutes',
 'Total': 'Total',
 'Ninguna': 'None',
 'Hay datos desconocidos o incompletos. Los indicadores no sustituyen la revisión de integridad.': 'Some '
                                                                                                   'data '
                                                                                                   'is '
                                                                                                   'unknown '
                                                                                                   'or '
                                                                                                   'incomplete. '
                                                                                                   'These '
                                                                                                   'indicators '
                                                                                                   'do '
                                                                                                   'not '
                                                                                                   'replace '
                                                                                                   'integrity '
                                                                                                   'checks.',
 'Cumplidas': 'Met',
 'Excepciones manuales activas de laboratorio / sesiones asignadas: {ratio}. Confirmadas: {ids}. Sin confirmar: {unconfirmed}. No evaluables: {unknown}. Registros inactivos: {inactive}.': 'Active '
                                                                                                                                                                                            'manual '
                                                                                                                                                                                            'lab '
                                                                                                                                                                                            'exceptions '
                                                                                                                                                                                            '/ '
                                                                                                                                                                                            'assigned '
                                                                                                                                                                                            'sessions: '
                                                                                                                                                                                            '{ratio}. '
                                                                                                                                                                                            'Confirmed: '
                                                                                                                                                                                            '{ids}. '
                                                                                                                                                                                            'Unconfirmed: '
                                                                                                                                                                                            '{unconfirmed}. '
                                                                                                                                                                                            'Not '
                                                                                                                                                                                            'evaluable: '
                                                                                                                                                                                            '{unknown}. '
                                                                                                                                                                                            'Inactive '
                                                                                                                                                                                            'records: '
                                                                                                                                                                                            '{inactive}.'})

# Keyboard and assistive-technology labels.
MESSAGES.update({'Use flechas para recorrer celdas y Tab para salir. En tablas ordenables, Ctrl+Mayús+Arriba o Abajo ordena la columna actual.': 'Use '
                                                                                                                                 'arrow '
                                                                                                                                 'keys '
                                                                                                                                 'to '
                                                                                                                                 'explore '
                                                                                                                                 'cells '
                                                                                                                                 'and '
                                                                                                                                 'Tab '
                                                                                                                                 'to '
                                                                                                                                 'leave. '
                                                                                                                                 'In '
                                                                                                                                 'sortable '
                                                                                                                                 'tables, '
                                                                                                                                 'Ctrl+Shift+Up '
                                                                                                                                 'or '
                                                                                                                                 'Down '
                                                                                                                                 'sorts '
                                                                                                                                 'the '
                                                                                                                                 'current '
                                                                                                                                 'column.',
 'Aulas con restricciones': 'Restricted classrooms',
 'Use flechas para seleccionar y Espacio para marcar o desmarcar.': 'Use arrow keys to select and Space to '
                                                                    'check or uncheck.',
 'Cursos permitidos en el aula seleccionada': 'Allowed courses in the selected classroom',
 'Duración en horas': 'Duration in hours',
 'Duración en minutos': 'Duration in minutes',
 'Hora de inicio preferida': 'Preferred start time',
 'Semilla fija': 'Fixed seed',
 'Progreso de generación': 'Schedule generation progress',
 'Leer estado (F6)': 'Read status (F6)',
 'Estado actual': 'Current status',
 'Use flechas para recorrer la cuadrícula y Tab para salir. La Lista detallada ofrece las mismas sesiones en filas, con estado y acciones.': 'Use '
                                                                                                                                             'arrow '
                                                                                                                                             'keys '
                                                                                                                                             'to '
                                                                                                                                             'explore '
                                                                                                                                             'the '
                                                                                                                                             'grid '
                                                                                                                                             'and '
                                                                                                                                             'Tab '
                                                                                                                                             'to '
                                                                                                                                             'leave. '
                                                                                                                                             'The '
                                                                                                                                             'Detailed '
                                                                                                                                             'list '
                                                                                                                                             'offers '
                                                                                                                                             'the '
                                                                                                                                             'same '
                                                                                                                                             'sessions '
                                                                                                                                             'in '
                                                                                                                                             'rows, '
                                                                                                                                             'with '
                                                                                                                                             'status '
                                                                                                                                             'and '
                                                                                                                                             'actions.'})
