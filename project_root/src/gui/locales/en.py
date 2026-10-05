"""en presentation catalog. Keep keys stable; edit values to revise wording."""

MESSAGES = {
    '{room_type} (guardado en el curso)': '{room_type} (saved in the course)',
    'La semilla guardada está fuera del intervalo permitido.': 'The saved seed is outside the supported range.',
    'Comparación pendiente': 'Comparison pending',
    'Comparación actualizada. La sesión sigue guardada.': 'Comparison updated. The session remains saved.',
    'Sesión guardada. No se pudo comparar con la copia del escenario. Reintenta la comparación. {detail}': 'Session saved. The scenario snapshot could not be compared. Retry the comparison. {detail}',

    'Confirmar reemplazo': 'Confirm replacement',
    'El archivo ya existe:\n{path}\n\n¿Desea reemplazarlo?': 'The file already exists:\n{path}\n\nDo you want to replace it?',
    'La generación cambió u omitió grupos solicitados. Se conserva el horario anterior.': 'Generation changed or omitted requested groups. The previous schedule is preserved.',
    'Crear un tema con IA…': 'Create a theme with AI…',
    'Crear un tema con IA': 'Create a theme with AI',
    'No se pudo preparar la especificación. No se ha aplicado ningún cambio.': 'The specification could not be prepared. No changes have been applied.',
    'Usa la IA que prefieras fuera de SORTH. Esta guía no abre ni conecta servicios, no envía datos y no realiza llamadas de pago.': 'Use your preferred AI outside SORTH. This guide does not open or connect services, send data, or make paid calls.',
    '1. Copia la especificación': '1. Copy the specification',
    'Incluye el contrato y los colores de la vista previa, con nombre y descripción de ejemplo. No incluye cursos, horarios, nombres de archivos ni datos del proyecto.': 'It includes the contract and preview colors, with an example name and description. It excludes courses, timetables, filenames, and project data.',
    'Copiar especificación': 'Copy specification',
    '2. Genera el archivo en tu IA': '2. Generate the file in your AI',
    'Pega la especificación, añade tus preferencias visuales y pide el archivo JSON. Revisa la privacidad y los posibles cargos de ese servicio. Si tu asistente usa habilidades, el repositorio incluye sorth-theme-designer.': 'Paste the specification, add your visual preferences, and ask for the JSON file. Review that service’s privacy and possible charges. If your assistant uses skills, the repository includes sorth-theme-designer.',
    '3. Importa y revisa': '3. Import and review',
    'La IA puede producir un tema inválido. SORTH comprobará el archivo y su contraste. Si es válido, solo cambiará la vista previa; después debes pulsar Aplicar.': 'AI can produce an invalid theme. SORTH will check the file and its contrast. A valid file only changes the preview; you must then choose Apply.',
    'Importar resultado…': 'Import result…',
    'Especificación copiada. Pégala en la IA que elijas; el tema sigue sin aplicarse.': 'Specification copied. Paste it into your chosen AI; the theme is still unapplied.',
    'No se pudo confirmar la copia. Inténtalo de nuevo o selecciona el texto de la especificación y cópialo manualmente.': 'Could not confirm copying. Try again or select the specification text and copy it manually.',
    'Especificación y plantilla para copiar': 'Specification and template to copy',
    'Crea un tema de interfaz SORTH según mis preferencias visuales, que añadiré a este mensaje. Devuelve un único objeto JSON UTF-8 para un archivo .sorth-theme.json, sin Markdown ni texto alrededor. Usa la plantilla completa como punto de partida. Cambia solo los colores y los metadatos del tema; no añadas campos, estilos, código, rutas, fuentes ni recursos externos. No necesitas cursos, horarios, archivos personales, cuentas ni credenciales.\n\nCumple el esquema canónico y todas las parejas de contraste indicadas. Los contrastes usan luminancia relativa sRGB WCAG, sin redondear antes de comparar. No uses claves duplicadas, NaN, Infinity, BOM, marcado ni caracteres Unicode de control o formato. El archivo final debe ocupar como máximo {limit} bytes. Si tienes el repositorio SORTH correspondiente, usa su habilidad sorth-theme-designer y su validador canónico. Si no puedes ejecutar ese validador, dilo por separado y no afirmes que el tema está validado. SORTH comprobará el resultado al importarlo; cumplir el esquema por sí solo no garantiza su aceptación ni certifica accesibilidad.': 'Create a SORTH interface theme using the visual preferences I will add to this message. Return one UTF-8 JSON object for a .sorth-theme.json file, without Markdown or surrounding text. Use the complete template as a starting point. Change only theme colors and metadata; do not add fields, styles, code, paths, fonts, or external resources. You do not need courses, timetables, personal files, accounts, or credentials.\n\nMeet the canonical schema and every listed contrast pair. Contrast uses WCAG sRGB relative luminance, without rounding before comparison. Do not use duplicate keys, NaN, Infinity, a BOM, markup, or Unicode control/format characters. The final file must be at most {limit} bytes. If you have the matching SORTH repository, use its sorth-theme-designer skill and canonical validator. If you cannot run that validator, say so separately and do not claim that the theme is validated. SORTH will check the result on import; meeting the schema alone does not guarantee acceptance or certify accessibility.',
    'El tema guardado se muestra en vista previa. El tema activo no cambia hasta pulsar Aplicar.': 'The saved theme is shown in the preview. The active theme stays unchanged until you choose Apply.',
    'No se pudo preparar la apariencia guardada. Se muestra Original claro sin cambiar el archivo guardado. Abra Configuración → Apariencia para intentarlo de nuevo.': 'The saved appearance could not be prepared. Original light is shown without changing the saved file. Open Settings → Appearance to try again.',
    'No se pudo preparar la vista previa. No se ha aplicado ningún cambio.': 'The preview could not be prepared. No changes have been applied.',
    'Sesiones': 'Sessions',
    'El archivo del tema guardado no es válido y se conserva. Revisa Original claro en la vista previa antes de recuperarlo.': 'The saved theme file is invalid and has been preserved. Review Original light in the preview before recovering it.',
    'Las preferencias de apariencia cambiaron fuera de esta ventana. Revisa el tema guardado en la vista previa y pulsa Aplicar para usarlo.': 'Appearance preferences changed outside this window. Review the saved theme in the preview and choose Apply to use it.',
    'El tema se guardó, pero la interfaz no pudo actualizarse por completo. Reinicia SORTH para terminar de aplicarlo.': 'The theme was saved, but the interface could not update completely. Restart SORTH to finish applying it.',
    'Apariencia': 'Appearance',
    'Apariencia…': 'Appearance…',
    'Hazlo tuyo': 'Make it yours',
    'Original claro': 'Original light',
    'Nocturno': 'Night',
    'Alto contraste claro': 'High contrast light',
    'La identidad original de SORTH: azul marino, verde azulado y violeta.': 'SORTH’s original identity: navy, teal and violet.',
    'Superficies oscuras y controles nítidos para trabajar con poca luz.': 'Dark surfaces and crisp controls for working in low light.',
    'Superficies claras con bordes y texto de mayor contraste.': 'Light surfaces with stronger contrast for text and borders.',
    'Tu espacio de trabajo': 'Your workspace',
    'Vista previa interactiva · datos de ejemplo': 'Interactive preview · sample data',
    'Nombre del horario': 'Timetable name',
    'Escribe para probar el tema': 'Type to try the theme',
    'Nombre del horario de ejemplo': 'Sample timetable name',
    'Probar foco': 'Try focus',
    'Control de ejemplo. Usa Tab para ver el indicador de foco.': 'Sample control. Use Tab to see the focus indicator.',
    'Probar acción': 'Try action',
    'No disponible': 'Unavailable',
    'Los controles solo cambian esta muestra.': 'These controls only change this sample.',
    'Filas de ejemplo; la primera está seleccionada': 'Sample rows; the first is selected',
    'Fila seleccionada': 'Selected row',
    'Fila sin seleccionar': 'Unselected row',
    'Matemáticas · Aula 101': 'Mathematics · Room 101',
    'Bloque de curso de ejemplo': 'Sample course block',
    'MAT101 · 08:00–09:00 · Matemáticas · Aula 101': 'MAT101 · 08:00–09:00 · Mathematics · Room 101',
    'Tonos adaptados; identidad y patrones estables.': 'Adapted tones; stable identity and patterns.',
    'Aviso de ejemplo: revisa las sesiones pendientes.': 'Sample warning: review pending sessions.',
    'Error de ejemplo: hay un cruce de horario.': 'Sample error: there is a timetable conflict.',
    'Acción de ejemplo completada. Tu horario no ha cambiado.': 'Sample action completed. Your timetable has not changed.',
    'Elige un tema y prueba sus controles. Solo Aplicar cambia la aplicación. Cancelar descarta esta vista previa.': 'Choose a theme and try its controls. Only Apply changes the app. Cancel discards this preview.',
    'Tema': 'Theme',
    'Descripción del tema': 'Theme description',
    'Importar tema JSON…': 'Import JSON theme…',
    'Archivo local .sorth-theme.json · máximo 16 KiB. También admite temas creados con IA usando el contrato de SORTH. Sin código, fuentes ni recursos externos.': 'Local .sorth-theme.json file · up to 16 KiB. Also accepts AI-created themes that follow SORTH’s contract. No code, fonts or external resources.',
    'Conservar archivo inválido y reemplazarlo al aplicar': 'Preserve invalid file and replace it when applying',
    'Estado del tema': 'Theme status',
    'Detalles del error de tema': 'Theme error details',
    'El tema adapta los tonos de pantalla; PDF y Excel conservan su paleta para papel blanco. No cambia horarios, permisos MCP ni animaciones.': 'Themes adapt screen colors; PDF and Excel keep their white-paper palette. Timetables, MCP permissions and motion stay unchanged.',
    'Restaurar original': 'Restore original',
    'Selecciona Original claro en la vista previa. Pulsa Aplicar para guardarlo.': 'Selects Original light in the preview. Choose Apply to save it.',
    'Aplicar': 'Apply',
    'Oscuro': 'Dark',
    'Claro': 'Light',
    'Tema activo': 'Active theme',
    'Vista previa sin aplicar': 'Preview, not applied',
    'Importar tema JSON': 'Import JSON theme',
    'Tema de SORTH (*.sorth-theme.json *.json)': 'SORTH theme (*.sorth-theme.json *.json)',
    'No se importó el tema. Revisa el archivo; el tema activo no ha cambiado.': 'Theme was not imported. Check the file; the active theme has not changed.',
    'Archivo válido. La vista previa está lista; pulsa Aplicar para guardar una copia local.': 'Valid file. The preview is ready; choose Apply to save a local copy.',
    'Original claro está en vista previa. Pulsa Aplicar para restaurarlo.': 'Original light is in preview. Choose Apply to restore it.',
    'No se pudo aplicar el tema. El tema anterior sigue activo. Puedes volver a intentarlo.': 'The theme could not be applied. The previous theme is still active. You can try again.',
    'Temas integrados o propios. Aplicar en Apariencia guarda el tema de inmediato; Guardar y Cancelar aquí solo afectan a las herramientas opcionales.': 'Built-in or custom themes. Apply in Appearance saves the theme immediately; Save and Cancel here only affect optional tools.',
    'No se pudo leer la apariencia guardada. Se muestra Original claro y el archivo original se conserva. Abra Configuración → Apariencia para revisarlo o recuperarlo.': 'The saved appearance could not be read. Original light is shown and the original file is preserved. Open Settings → Appearance to review or recover it.',

    'Avanzado': 'Advanced',
    'MCP': 'MCP',
    'Sin guardar: {count}': 'Unsaved: {count}',
    'Sin cambios': 'No changes',
    'Al desactivar un recurso, sus registros se conservan. Sus restricciones se retiran después de confirmar y regenerar el horario.': 'Turning off a resource keeps its records. Its constraints are removed after confirmation and timetable regeneration.',
    'Al desactivar una herramienta se ocultan sus controles. Los escenarios, las fijaciones y el calendario guardados se conservan.': 'Turning off a tool hides its controls. Saved scenarios, pins and calendar settings are kept.',
    'Sin cambios por guardar': 'No unsaved changes',
    'Activa solo las herramientas que necesites. Las funciones opcionales empiezan desactivadas.': 'Enable only the tools you need. Optional features start turned off.',
    'Sección de configuración': 'Settings section',
    'Elige General, Recursos académicos, Herramientas avanzadas o Conexión MCP. Los cambios se conservan al cambiar de sección.': 'Choose General, Academic resources, Advanced tools or MCP connection. Switching sections keeps your unsaved choices.',
    'General': 'General',
    'Recursos académicos': 'Academic resources',
    'Herramientas avanzadas': 'Advanced tools',
    'Conexión MCP': 'MCP connection',
    'Revisa cambios y organiza las sesiones del horario.': 'Review changes and organize timetable sessions.',
    'Define qué recursos deben evitar cruces de horario.': 'Choose which resources must avoid timetable conflicts.',
    'Organiza escenarios, sesiones y parámetros del calendario.': 'Manage scenarios, sessions and calendar settings.',
    'Prepara el complemento, guarda el permiso local y configura tu cliente.': 'Prepare the add-on, save local permission and set up your client.',
    'Estado de los cambios de configuración': 'Settings change status',
    'Guardar aplica las preferencias de todas las secciones en este equipo. Cancelar descarta los cambios de preferencias.': 'Save applies preferences from every section on this device. Cancel discards preference changes.',
    'Cambios sin guardar: {count}': 'Unsaved changes: {count}',

    'El permiso MCP cambió fuera de este diálogo. Se ha actualizado su casilla; revisa los cambios antes de guardar.': 'MCP permission changed outside this dialog. Its checkbox has been refreshed; review the changes before saving.',
    'Espera a que termine la operación o recupera la sesión antes de guardar la configuración.': 'Wait for the operation to finish or recover the session before saving settings.',
    'Guarda los cambios de recursos y el permiso MCP por separado. No se han guardado cambios.': 'Save resource changes and the MCP permission separately. No changes have been saved.',

    'Permitir servidor MCP local': 'Allow local MCP server',
    'Permitir que un cliente inicie el servidor stdio. No inicia procesos, conecta modelos ni instala componentes.': 'Allow a client to start the stdio server. This does not start processes, connect models or install components.',
    'Disponibilidad MCP sin verificar en este entorno.': 'MCP availability has not been checked in this environment.',
    'Verificar disponibilidad local de MCP': 'Check local MCP availability',
    'Verificando componentes locales de MCP…': 'Checking local MCP components…',
    'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.': 'MCP is available in this environment. The client starts the server; Save does not start it.',
    'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.': 'The optional MCP SDK is missing in this environment. Nothing has been installed.',
    'Versión MCP incompatible. Se requiere mcp 1.30.0; no se ha cambiado nada.': 'Incompatible MCP version. mcp 1.30.0 is required; nothing has been changed.',
    'Este EXE no incluye el servidor MCP opcional. Usa el código fuente y un entorno Python separado según MCP_OPTIONAL.md.': 'This EXE does not include the optional MCP server. Use the source code and a separate Python environment as described in MCP_OPTIONAL.md.',
    'No se pudieron cargar los componentes MCP. Revisa el entorno siguiendo MCP_OPTIONAL.md.': 'MCP components could not be loaded. Check the environment using MCP_OPTIONAL.md.',
    'La verificación MCP agotó el tiempo. Puedes volver a intentarlo.': 'The MCP check timed out. You can try again.',
    'Verificación MCP cancelada.': 'MCP check cancelled.',
    'Verifica que MCP esté disponible antes de activarlo. No se han guardado cambios.': 'Check that MCP is available before enabling it. No changes have been saved.',
    'Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. La verificación solo comprueba este entorno; el EXE estándar no incluye MCP. Consulta MCP_OPTIONAL.md para un entorno Python separado.': 'Disabling MCP blocks new starts and requests and discards pending results. The client closes the stdio process; an in-flight task may take up to 10 seconds. The check only tests this environment; the standard EXE does not include MCP. See MCP_OPTIONAL.md for a separate Python environment.',

    'La sesión y sus parámetros de recursos no cambiaron. Algunas preferencias de herramientas se guardaron y no se pudieron restaurar. Recupere la configuración antes de continuar. {detail}': 'The session and its resource parameters did not change. Some tool preferences were saved and could not be restored. Recover settings before continuing. {detail}',
    'Actualizar recursos': 'Update resources',
    'compact_assigned_count': {'one': '{n} assigned', 'other': '{n} assigned'},
    'compact_pending_count': {'one': '{n} pending', 'other': '{n} pending'},
    'Parámetros activos: {count}': 'Active parameters: {count}',
    'Calendario personalizado': 'Custom calendar',

    'Herramientas del horario (F7)': 'Schedule tools (F7)',

    '{name}: {state} ({count})': '{name}: {state} ({count})',
    'La sesión guardada se conserva. La vista requiere recuperación antes de continuar.': 'The saved session is preserved. The view requires recovery before continuing.',
    'Sin valor': 'No value',
    'Grupo {number}: aula {room}, día {day}, hora {time}': 'Group {number}: room {room}, day {day}, time {time}',
    "Cancelando…": 'Cancelling…',
    'Opciones de ubicación': 'Placement options',
    'Mostrar ubicaciones válidas para sesiones pendientes sin mover otras sesiones.': 'Show valid placements for pending sessions without moving other sessions.',
    'Ver opciones': 'View options',
    'Opciones para {gid}': 'Options for {gid}',
    'Opciones del horario actual, sin mover otras sesiones. Búsqueda cada 30 minutos y en horas guardadas; la asignación manual permite otras horas.': 'Options in the current schedule, without moving other sessions. Search uses 30-minute intervals and saved times; manual placement allows other times.',
    'Resultado de opciones': 'Placement options result',
    'Ubicaciones válidas para la sesión pendiente': 'Valid placements for the pending session',
    'Recalcular opciones': 'Recalculate options',
    'La sesión o la herramienta ya no está disponible. No se aplicó ningún cambio.': 'The session or tool is no longer available. No changes were applied.',
    'El horario cambió. Opciones recalculadas; elija de nuevo.': 'The schedule changed. Options recalculated; choose again.',
    '{count} opciones en el horario actual.': '{count} options in the current schedule.',
    'No hay opciones en el horario actual. Esto no demuestra imposibilidad global.': 'There are no options in the current schedule. This does not prove global impossibility.',
    'Búsqueda limitada: se muestran solo los primeros resultados válidos.': 'Limited search: only the first valid results are shown.',
    'Asignar opción válida': 'Assign valid option',

    "Generación cancelada. Se conserva el horario anterior.": 'Generation cancelled. The previous schedule is preserved.',
    'No se pudo leer la configuración opcional. Abre Configuración para conservarla y recuperarla.': 'Optional settings could not be read. Open Settings to preserve and recover them.',
    'Herramientas de sesiones fijadas': 'Pinned session tools',
    'Mostrar controles para fijar o desfijar. Las fijaciones guardadas siempre se respetan.': 'Show pin/unpin controls. Saved pins are always enforced.',
    'Herramientas de proyectos y escenarios': 'Project and scenario tools',
    'Mostrar controles para guardar, abrir y comparar copias independientes.': 'Show controls to save, open and compare independent snapshots.',
    'La configuración opcional no se puede leer. Puedes conservar el archivo original y restablecer solo estas herramientas.': 'Optional settings cannot be read. You can preserve the original file and reset only these tools.',
    'Conservar original y restablecer herramientas': 'Preserve original and reset tools',
    'Se conservará el archivo original y se desactivarán las herramientas opcionales. Los horarios, fijaciones y escenarios no cambian. ¿Continuar?': 'The original file will be preserved and optional tools turned off. Schedules, pins and scenarios will not change. Continue?',
    'Duración (minutos)': 'Duration (minutes)',
    'Tipo de aula requerido': 'Required room type',
    'Estudiantes': 'Students',
    'Aula sugerida': 'Suggested room',
    'Inicio preferido (minutos)': 'Preferred start (minutes)',
    'Preferencias por grupo': 'Per-group preferences',
    'División de sesiones': 'Session splitting',
    'Capacidad': 'Capacity',
    'Tipo de aula': 'Room type',
    'Descripción': 'Description',
    'Campus': 'Campus',
    '    {field}: {before} → {after}': '    {field}: {before} → {after}',

    'Cancelar importación': 'Cancel import',
    'Progreso de importación': 'Import progress',
    'Leyendo y validando Excel… La sesión actual se conserva.': 'Reading and validating Excel… Your current session is preserved.',
    'Importación cancelada. La sesión anterior se conserva.': 'Import cancelled. Your previous session is preserved.',
    'El archivo cambió. Revise la nueva versión validada antes de importar.': 'The file changed. Review the newly validated version before importing.',
    'Comprobando que el archivo no cambió…': 'Checking that the file has not changed…',
    'Cancelando importación antes de cerrar…': 'Cancelling import before closing…',
    'El archivo cambió mientras se leía. Selecciónelo nuevamente.': 'The file changed while it was being read. Select it again.',
    'Revisar cambios del Excel': 'Review Excel changes',
    'Se reemplazarán los cursos y aulas. Se borrarán las restricciones y las asignaciones no conservadas. Cancelar mantiene la sesión actual.': 'Courses and rooms will be replaced. Restrictions and assignments that are not retained will be cleared. Cancel keeps your current session.',
    'Cambios de importación': 'Import changes',
    'Reemplazar con este Excel': 'Replace with this Excel file',
    'Archivo: {name}': 'File: {name}',
    'Añadidos': 'Added',
    'Modificados': 'Changed',
    'Eliminados': 'Deleted',
    '{label}: {count}': '{label}: {count}',
    'Restricciones que se borrarán: {count}': 'Restrictions to be cleared: {count}',
    'Asignaciones que se borrarán': 'Assignments to be cleared',
    'Sesiones fijadas que se conservarán': 'Pinned sessions to be retained',
    'Vista previa de cambios del Excel': 'Excel change preview',
    'Revisar cursos, aulas, restricciones y asignaciones antes de reemplazar la sesión.': 'Review courses, rooms, restrictions and assignments before replacing the session.',

    'Cancelar generación': 'Cancel generation',
    'Cancelando generación; se conservarán el horario y las sesiones fijadas.': 'Cancelling generation; the schedule and pinned sessions will be preserved.',

    'La generación cambió sesiones fijadas. Se conserva el horario anterior.': 'Generation changed pinned sessions. The previous schedule is preserved.',
    'La sesión fijada {gid} requiere confirmar una excepción LAB.': 'Pinned session {gid} requires confirmation of a LAB exception.',
    'Sesión fijada': 'Pinned session',
    'Desfije la sesión antes de cambiar su asignación.': 'Unpin the session before changing its assignment.',
    'La estructura dividida de {gid} cambió.': 'The split structure of {gid} changed.',
    'Sesiones fijadas en conflicto': 'Conflicting pinned sessions',
    'Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.': 'This change invalidates pinned sessions:\n{details}\n\nUnpin all sessions and apply the change? Cancel preserves the data and schedule.',
    'Fijar sesión': 'Pin session',
    'Conservar solo esta sesión al regenerar; no es una preferencia.': 'Keep only this session when regenerating; this is not a preference.',
    'Desfijar sesión': 'Unpin session',
    'Fijada · {state}': 'Pinned · {state}',
    'Desfije las sesiones antes de limpiar el horario.': 'Unpin the sessions before clearing the schedule.',

    'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.': 'The saved format, metrics or calendar are unsupported. Indicators were not recalculated with different rules.',
    'Versión del formato': 'Format version',
    'Aula: preferencias pendientes / desconocidas': 'Room: pending / unknown preferences',
    'Hora: preferencias pendientes / desconocidas': 'Time: pending / unknown preferences',
    'Día: preferencias pendientes / desconocidas': 'Day: pending / unknown preferences',
    'Valores diferentes (izquierda / derecha)': 'Different values (left / right)',
    'Nombre (1–120 caracteres)': 'Name (1–120 characters)',
    'Proyectos y escenarios': 'Projects and scenarios',
    'Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.': 'Each scenario is an independent copy. Save as never overwrites. Select two rows to compare.',
    'Proyecto': 'Project',
    'Escenario': 'Scenario',
    'Guardado (UTC)': 'Saved (UTC)',
    'Escenarios guardados': 'Saved scenarios',
    'Crear proyecto desde la sesión': 'Create project from session',
    'Guardar como escenario': 'Save as scenario',
    'Abrir escenario': 'Open scenario',
    'Duplicar': 'Duplicate',
    'Renombrar': 'Rename',
    'Comparar': 'Compare',
    'Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.': 'That name already exists. Use another name; no scenario was replaced.',
    'No se pudo completar la operación. El escenario guardado se conserva. {detail}': 'The operation could not be completed. The saved scenario is preserved. {detail}',
    'Escenario guardado. Las ediciones posteriores no cambian esta copia.': 'Scenario saved. Further edits do not change this copy.',
    'Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?': 'A recovery copy of the current session will be saved before opening {name}. Continue?',
    'Comparar escenarios': 'Compare scenarios',
    'Indicadores descriptivos, sin ganador ni puntuación global.': 'Descriptive indicators, with no winner or overall score.',
    'No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.': 'Not directly comparable: inputs, rules or versions differ, or the algorithm version is unknown.',
    'Cursos': 'Courses',
    'Aulas': 'Classrooms',
    'Restricciones': 'Restrictions',
    'Sesiones fijas': 'Pinned sessions',
    'Semilla': 'Seed',
    'Calendario': 'Calendar',
    'Versión del algoritmo': 'Algorithm version',
    'Versión de métricas': 'Metrics version',
    'Recursos': 'Resources',
    'Diferencias: {details}': 'Differences: {details}',
    'Ninguna': 'None',
    'Indicador': 'Indicator',
    'El calendario guardado no es compatible. No se recalcularon indicadores con reglas diferentes.': 'The saved calendar is unsupported. Indicators were not recalculated with different rules.',
    'Sesiones asignadas / total': 'Assigned sessions / total',
    'Sesiones pendientes': 'Pending sessions',
    'Preferencia de día: satisfechas / evaluadas': 'Day preference: satisfied / evaluated',
    'Preferencia de hora: satisfechas / evaluadas': 'Time preference: satisfied / evaluated',
    'Preferencia de aula: satisfechas / evaluadas': 'Room preference: satisfied / evaluated',
    'Ocupación: minutos-aula / disponibles': 'Occupancy: room-minutes / available',
    'Excepciones activas': 'Active exceptions',
    'No lectivo': 'Non-teaching day',
    'Docencia, día {day} (min)': 'Teaching, day {day} (min)',
    'No se pudo abrir el catálogo. La sesión actual se conserva. {detail}': 'The catalog could not be opened. The current session is preserved. {detail}',
    'Cambios posteriores a la copia': 'Changes since snapshot',
    'Copia guardada': 'Saved snapshot',
    '{name} · {state} · {save}': '{name} · {state} · {save}',
    'Ningún archivo seleccionado': 'No file selected',
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
    "Desempata opciones con la misma prioridad.\nMismos datos y semilla fija → mismo horario.\nSemilla aleatoria → puede ofrecer alternativas, sin garantizar un horario distinto.": "Breaks ties between equally ranked options.\nSame inputs and fixed seed → same schedule.\nRandom seed → may offer alternatives; a different schedule is not guaranteed.",
    "Hoja {sheet}, celda {cell}: contiene un error de Excel. Corríjalo y vuelva a cargar el archivo.": "Sheet {sheet}, cell {cell}: contains an Excel error. Correct it and load the file again.",
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
    "\nEn Excel también se incluyen todas las sesiones pendientes del horario, aunque no coincidan con los filtros.": "\nExcel also includes all pending sessions in the schedule, even if they do not match the filters.",
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
    "SORTH-AI - Sistema de Organización de Horarios": "SORTH-AI - Academic Schedule Organizer",
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

# Grid scope and native session details.
MESSAGES.update({
    'Filtros globales · Asignadas exportables: {assigned} · Pendientes: {pending} · Sesiones: {visible}/{total}': 'Global filters · Exportable assignments: {assigned} · Pending: {pending} · Sessions: {visible}/{total}',
    'Sesiones en esta aula: {count}': 'Sessions in this classroom: {count}',
    'El aula de la cuadrícula no cambia la exportación filtrada.': 'The grid classroom does not change filtered export.',
    'Ver detalles': 'View details',
    'Detalles de la sesión': 'Session details',
    'Sesiones del bloque en conflicto': 'Sessions in the conflicting block',
    'Seleccione una sesión para verla en la lista.': 'Select a session to view it in the list.',
    'Ver en lista': 'View in list',
    'Sesión: {gid}\nCurso: {course}\nAula: {room}\nDía: {day}\nHorario: {start}–{end}': 'Session: {gid}\nCourse: {course}\nClassroom: {room}\nDay: {day}\nTime: {start}–{end}',
    'Seleccione un bloque y pulse Intro o Ver detalles para leer la sesión completa.': 'Select a block and press Enter or View details to read the complete session.',
    'Use flechas para recorrer la cuadrícula, Intro para ver detalles y Tab para salir.': 'Use arrow keys to navigate the grid, Enter to view details and Tab to leave.',
})

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

# Optional feature settings
MESSAGES.update({'Configuración': 'Settings',
 'Sesiones fijadas': 'Pinned sessions',
 'Fijar o desfijar sesiones para conservar su ubicación al regenerar.': 'Pin or unpin sessions to '
                                                                        'preserve their placement when '
                                                                        'regenerating.',
 'Guardar copias independientes, abrir escenarios y compararlos.': 'Save independent copies, open '
                                                                   'scenarios and compare them.',
 'Las funciones opcionales empiezan desactivadas. Los cambios se guardan en este equipo.': 'Optional '
                                                                                           'features '
                                                                                           'start '
                                                                                           'disabled. '
                                                                                           'Changes are '
                                                                                           'saved on '
                                                                                           'this '
                                                                                           'computer.',
 'Desactivar oculta los controles, sin borrar datos. Las sesiones ya fijadas siguen protegidas. Las validaciones de seguridad siempre están activas.': 'Disabling '
                                                                                                                                                       'hides '
                                                                                                                                                       'controls '
                                                                                                                                                       'without '
                                                                                                                                                       'deleting '
                                                                                                                                                       'data. '
                                                                                                                                                       'Existing '
                                                                                                                                                       'pinned '
                                                                                                                                                       'sessions '
                                                                                                                                                       'stay '
                                                                                                                                                       'protected. '
                                                                                                                                                       'Safety '
                                                                                                                                                       'validations '
                                                                                                                                                       'are '
                                                                                                                                                       'always '
                                                                                                                                                       'active.',
 'MCP se instala y se inicia por separado; esta configuración no activa servicios externos.': 'MCP is '
                                                                                              'installed '
                                                                                              'and '
                                                                                              'started '
                                                                                              'separately; '
                                                                                              'these '
                                                                                              'settings '
                                                                                              'do not '
                                                                                              'activate '
                                                                                              'external '
                                                                                              'services.',
 'Se ocultarán los controles para fijar sesiones. Las sesiones ya fijadas seguirán condicionando la generación. Para cambiarlas, vuelve a activar esta función. ¿Guardar configuración?': 'Pin '
                                                                                                                                                                                          'controls '
                                                                                                                                                                                          'will '
                                                                                                                                                                                          'be '
                                                                                                                                                                                          'hidden. '
                                                                                                                                                                                          'Existing '
                                                                                                                                                                                          'pinned '
                                                                                                                                                                                          'sessions '
                                                                                                                                                                                          'will '
                                                                                                                                                                                          'still '
                                                                                                                                                                                          'constrain '
                                                                                                                                                                                          'generation. '
                                                                                                                                                                                          'Enable '
                                                                                                                                                                                          'this '
                                                                                                                                                                                          'feature '
                                                                                                                                                                                          'again '
                                                                                                                                                                                          'to '
                                                                                                                                                                                          'change '
                                                                                                                                                                                          'them. '
                                                                                                                                                                                          'Save '
                                                                                                                                                                                          'settings?',
 'No se pudo guardar la configuración. Revisa los permisos e inténtalo de nuevo.': 'Settings could not '
                                                                                   'be saved. Check '
                                                                                   'permissions and try '
                                                                                   'again.',
 'Datos de funciones desactivadas': 'Disabled-feature data',
 'Hay sesiones fijadas: siguen protegidas. Activa Sesiones fijadas en Configuración para modificarlas.': 'Pinned '
                                                                                                         'sessions '
                                                                                                         'are '
                                                                                                         'still '
                                                                                                         'protected. '
                                                                                                         'Enable '
                                                                                                         'Pinned '
                                                                                                         'sessions '
                                                                                                         'in '
                                                                                                         'Settings '
                                                                                                         'to '
                                                                                                         'change '
                                                                                                         'them.',
 'Hay datos de escenarios conservados. Activa Proyectos y escenarios en Configuración para acceder.': 'Saved '
                                                                                                      'scenario '
                                                                                                      'data '
                                                                                                      'is '
                                                                                                      'preserved. '
                                                                                                      'Enable '
                                                                                                      'Projects '
                                                                                                      'and '
                                                                                                      'scenarios '
                                                                                                      'in '
                                                                                                      'Settings '
                                                                                                      'to '
                                                                                                      'access '
                                                                                                      'it.'})

MESSAGES.update({'Calendario del proyecto': 'Project calendar', 'Define días lectivos, horas y descansos. El calendario guardado se respeta aunque ocultes el editor.': 'Set teaching days, hours and breaks. Saved calendar rules remain active when the editor is hidden.', 'Hora de apertura': 'Opening time', 'Hora de cierre': 'Closing time', 'Las horas se expresan en HH:mm. Para terminar a medianoche, usa 00:00 como cierre.': 'Times use HH:mm. To finish at midnight, use 00:00 as the closing time.', 'Descansos del proyecto': 'Project breaks', 'Añadir descanso': 'Add break', 'Quitar descanso seleccionado': 'Remove selected break', 'Restablecer calendario predeterminado': 'Reset to default calendar', 'Resultado de la revisión del calendario': 'Calendar review result', 'Revisar y aplicar': 'Review and apply', 'Inicio del descanso': 'Break start', 'Fin del descanso': 'Break end', 'Revisa días, horas y descansos: deben ser válidos, no solaparse y dejar tiempo lectivo. {detail}': 'Check days, hours and breaks: they must be valid, must not overlap and must leave teaching time. {detail}', 'Hay sesiones fijadas afectadas. Desfíjalas explícitamente antes de cambiar el calendario.': 'Pinned sessions would be affected. Explicitly unpin them before changing the calendar.', 'Ninguna': 'None', 'Revisar calendario': 'Review calendar', 'Sesiones que quedarán pendientes: {sessions}. Las demás conservan su día y hora. ¿Aplicar el calendario?': 'Sessions that will become pending: {sessions}. Other sessions keep their day and time. Apply this calendar?', 'No se pudo guardar el calendario. No se aplicaron cambios.': 'Could not save the calendar. No changes were applied.', 'Calendario personalizado activo: se respeta aunque el editor esté oculto. Puedes revisarlo en Configuración.': 'Custom calendar active: its rules apply even while the editor is hidden. Review it in Settings.', 'Parámetros avanzados del calendario': 'Advanced calendar parameters', 'Mostrar el editor de días, horas y descansos del proyecto. El calendario guardado siempre se respeta.': 'Show the editor for project days, hours and breaks. Saved calendar rules always apply.', 'Editar calendario del proyecto': 'Edit project calendar'})

MESSAGES.update({'Guardar configuración y editar calendario': 'Save settings and edit calendar'})
MESSAGES.update({'Docentes': 'Teachers',
 'Grupos de estudiantes': 'Student groups',
 'Estudiantes individuales': 'Individual students',
 'Asignar docentes por sesión y evitar cruces de horario.': 'Choose teachers for each session and prevent '
                                                            'overlapping classes.',
 'Asignar grupos compartidos y evitar cruces de horario.': 'Assign shared student groups and prevent '
                                                           'overlapping classes.',
 'Asignar personas explícitas con alias locales y evitar cruces.': 'Assign individuals using local aliases '
                                                                   'and prevent overlaps.',
 'Editar recurso': 'Edit resource',
 'Nombre o alias': 'Name or alias',
 'Use un alias si lo prefiere. No se necesitan correos, edades ni identificaciones personales.': 'Use an '
                                                                                                 'alias if '
                                                                                                 'you '
                                                                                                 'prefer. No '
                                                                                                 'emails, '
                                                                                                 'ages or '
                                                                                                 'personal '
                                                                                                 'identification '
                                                                                                 'numbers '
                                                                                                 'are '
                                                                                                 'needed.',
 'Limitar a la disponibilidad declarada': 'Restrict to declared availability',
 'Sin declarar: no limita horarios. Declarada sin franjas: ninguna sesión puede asignarse.': 'Undeclared '
                                                                                             'availability '
                                                                                             'does not limit '
                                                                                             'times. '
                                                                                             'Declared '
                                                                                             'availability '
                                                                                             'with no '
                                                                                             'windows '
                                                                                             'prevents all '
                                                                                             'placements.',
 'Disponibilidad declarada': 'Declared availability',
 'Agregar franja': 'Add time window',
 'Quitar franja': 'Remove time window',
 'Revise el nombre y las franjas: el final debe ser posterior al inicio.': 'Check the name and time windows: '
                                                                           'the end must be after the start.',
 'Disponibilidad vacía': 'Empty availability',
 'No se permitirá ninguna sesión para este recurso. ¿Guardar disponibilidad vacía?': 'No sessions will be '
                                                                                     'permitted for this '
                                                                                     'resource. Save empty '
                                                                                     'availability?',
 'Agregue recursos y elija explícitamente sus sesiones. No se asignan personas automáticamente.': 'Add '
                                                                                                  'resources '
                                                                                                  'and '
                                                                                                  'explicitly '
                                                                                                  'choose '
                                                                                                  'their '
                                                                                                  'sessions. '
                                                                                                  'People '
                                                                                                  'are never '
                                                                                                  'allocated '
                                                                                                  'automatically.',
 'Recursos locales': 'Local resources',
 'Agregar recurso': 'Add resource',
 'Quitar recurso': 'Remove resource',
 'Sesión': 'Session',
 'Recursos asignados': 'Assigned resources',
 'Asignaciones de recursos por sesión': 'Resource assignments by session',
 'Elegir recursos de la sesión': 'Choose session resources',
 'Los grupos de estudiantes y las personas se asignan por separado. No se infieren matrículas ni pertenencias entre ellos.': 'Student '
                                                                                                                             'groups '
                                                                                                                             'and '
                                                                                                                             'individuals '
                                                                                                                             'are '
                                                                                                                             'assigned '
                                                                                                                             'separately. '
                                                                                                                             'Enrollment '
                                                                                                                             'and '
                                                                                                                             'group '
                                                                                                                             'membership '
                                                                                                                             'are '
                                                                                                                             'not '
                                                                                                                             'inferred.',
 'Sin disponibilidad declarada': 'Availability not declared',
 'Sin recursos asignados': 'No resources assigned',
 '¿Quitar {name} y sus asignaciones de todas las sesiones? Cancelar conserva todo.': 'Remove {name} and '
                                                                                     'their assignments from '
                                                                                     'all sessions? Cancel '
                                                                                     'preserves everything.',
 'Asignar varios recursos a esta sesión': 'Assign multiple resources to this session',
 'Sin selección no se aplica esta restricción. Cada recurso seleccionado queda ocupado durante toda la sesión.': 'With '
                                                                                                                 'no '
                                                                                                                 'selection, '
                                                                                                                 'this '
                                                                                                                 'constraint '
                                                                                                                 'does '
                                                                                                                 'not '
                                                                                                                 'apply. '
                                                                                                                 'Each '
                                                                                                                 'selected '
                                                                                                                 'resource '
                                                                                                                 'is '
                                                                                                                 'occupied '
                                                                                                                 'for '
                                                                                                                 'the '
                                                                                                                 'whole '
                                                                                                                 'session.',
 'Activo': 'Active',
 'Desactivado: datos conservados, sin restricciones': 'Off: records retained, constraints not applied',
 '{name}: {state}. {count} recursos con sesiones asignadas.': '{name}: {state}. {count} resources with '
                                                              'assigned sessions.',
 'Recursos por revisar': 'Review resources',
 'Este cambio elimina {count} sesiones con relaciones de recursos guardadas. Se quitarán esas relaciones, pero se conservarán los recursos. ¿Continuar?': 'This '
                                                                                                                                                          'change '
                                                                                                                                                          'removes '
                                                                                                                                                          '{count} '
                                                                                                                                                          'sessions '
                                                                                                                                                          'with '
                                                                                                                                                          'saved '
                                                                                                                                                          'resource '
                                                                                                                                                          'relationships. '
                                                                                                                                                          'Those '
                                                                                                                                                          'relationships '
                                                                                                                                                          'will '
                                                                                                                                                          'be '
                                                                                                                                                          'removed, '
                                                                                                                                                          'but '
                                                                                                                                                          'resources '
                                                                                                                                                          'will '
                                                                                                                                                          'be '
                                                                                                                                                          'retained. '
                                                                                                                                                          'Continue?',
 'Los cambios entran en conflicto con el horario. Se retirará el resultado y se desfijarán sus sesiones para regenerarlo. ¿Aplicar cambios?': 'These '
                                                                                                                                              'changes '
                                                                                                                                              'conflict '
                                                                                                                                              'with '
                                                                                                                                              'the '
                                                                                                                                              'timetable. '
                                                                                                                                              'The '
                                                                                                                                              'result '
                                                                                                                                              'and '
                                                                                                                                              'session '
                                                                                                                                              'pins '
                                                                                                                                              'will '
                                                                                                                                              'be '
                                                                                                                                              'cleared '
                                                                                                                                              'so '
                                                                                                                                              'it '
                                                                                                                                              'can '
                                                                                                                                              'be '
                                                                                                                                              'regenerated. '
                                                                                                                                              'Apply '
                                                                                                                                              'changes?',
 'Parámetros actualizados. Genere un nuevo horario; los recursos registrados se conservan.': 'Parameters '
                                                                                             'updated. '
                                                                                             'Generate a new '
                                                                                             'timetable; '
                                                                                             'registered '
                                                                                             'resources have '
                                                                                             'been retained.',
 'Desactivar herramientas oculta sus controles y conserva sus datos. Desactivar recursos retira esas restricciones después de confirmar y regenerar. Las reglas básicas siguen activas.': 'Turning '
                                                                                                                                                                                          'off '
                                                                                                                                                                                          'tools '
                                                                                                                                                                                          'hides '
                                                                                                                                                                                          'controls '
                                                                                                                                                                                          'and '
                                                                                                                                                                                          'preserves '
                                                                                                                                                                                          'data. '
                                                                                                                                                                                          'Turning '
                                                                                                                                                                                          'off '
                                                                                                                                                                                          'resources '
                                                                                                                                                                                          'removes '
                                                                                                                                                                                          'those '
                                                                                                                                                                                          'constraints '
                                                                                                                                                                                          'after '
                                                                                                                                                                                          'confirmation '
                                                                                                                                                                                          'and '
                                                                                                                                                                                          'regeneration. '
                                                                                                                                                                                          'Core '
                                                                                                                                                                                          'rules '
                                                                                                                                                                                          'remain '
                                                                                                                                                                                          'active.',
 'Cambiar parámetros de recursos': 'Change resource parameters',
 'Al desactivar un parámetro, sus recursos dejan de limitar nuevos horarios. Los registros se conservan. Cambiar estos parámetros retira el resultado actual y desfija sus sesiones; deberá regenerarlo. ¿Continuar?': 'Turning '
                                                                                                                                                                                                                       'off '
                                                                                                                                                                                                                       'a '
                                                                                                                                                                                                                       'parameter '
                                                                                                                                                                                                                       'stops '
                                                                                                                                                                                                                       'its '
                                                                                                                                                                                                                       'resources '
                                                                                                                                                                                                                       'from '
                                                                                                                                                                                                                       'constraining '
                                                                                                                                                                                                                       'new '
                                                                                                                                                                                                                       'timetables. '
                                                                                                                                                                                                                       'Records '
                                                                                                                                                                                                                       'are '
                                                                                                                                                                                                                       'retained. '
                                                                                                                                                                                                                       'Changing '
                                                                                                                                                                                                                       'these '
                                                                                                                                                                                                                       'parameters '
                                                                                                                                                                                                                       'clears '
                                                                                                                                                                                                                       'the '
                                                                                                                                                                                                                       'current '
                                                                                                                                                                                                                       'result '
                                                                                                                                                                                                                       'and '
                                                                                                                                                                                                                       'session '
                                                                                                                                                                                                                       'pins; '
                                                                                                                                                                                                                       'you '
                                                                                                                                                                                                                       'must '
                                                                                                                                                                                                                       'regenerate '
                                                                                                                                                                                                                       'it. '
                                                                                                                                                                                                                       'Continue?',
 'Datos de recursos por corregir: {details}': 'Resource data needs correction: {details}',
 'Docente {resource}: las sesiones {session} y {other} se solapan.': 'Teacher {resource}: sessions {session} '
                                                                     'and {other} overlap.',
 'Grupo de estudiantes {resource}: las sesiones {session} y {other} se solapan.': 'Student group {resource}: '
                                                                                  'sessions {session} and '
                                                                                  '{other} overlap.',
 'Estudiante {resource}: las sesiones {session} y {other} se solapan.': 'Student {resource}: sessions '
                                                                        '{session} and {other} overlap.',
 'Recurso {resource}: la sesión {session} queda fuera de su disponibilidad declarada.': 'Resource '
                                                                                        '{resource}: session '
                                                                                        '{session} is '
                                                                                        'outside its '
                                                                                        'declared '
                                                                                        'availability.'})

MESSAGES.update({'Calendar requires unique supported teaching days': 'Calendar requires unique supported teaching days', 'Calendar hours must be increasing integer minutes in 00:00–24:00': 'Calendar hours must be increasing integer minutes in 00:00–24:00', 'Calendar breaks must be intervals': 'Calendar breaks must be intervals', 'Breaks must be within opening hours': 'Breaks must be within opening hours', 'Calendar breaks must not overlap': 'Calendar breaks must not overlap', 'Calendar must leave teaching time available': 'Calendar must leave teaching time available', 'Resource availability references a removed teaching day; edit it explicitly first': 'Resource availability references a removed teaching day; edit it explicitly first', 'La duración no cabe en el horario permitido sin cruzar los descansos.': 'The duration does not fit the permitted hours without overlapping breaks.'})
MESSAGES.update({'Deshacer': 'Undo', 'Rehacer': 'Redo', 'Deshacer y rehacer': 'Undo and redo', 'Revertir cambios locales de esta sesión. Máximo 50 cambios o 16 MiB; importar o restaurar reinicia el historial.': 'Revert local changes in this session. Up to 50 changes or 16 MiB; importing or restoring resets history.', 'Deshacer el último cambio (Ctrl+Z). Historial de esta sesión: máximo 50 cambios o 16 MiB.': 'Undo the last change (Ctrl+Z). Session history: up to 50 changes or 16 MiB.', 'Rehacer el último cambio (Ctrl+Shift+Z).': 'Redo the last change (Ctrl+Shift+Z).', 'Cambio no aplicado': 'Change not applied', 'Se conservan los datos, el horario y el historial. {detail}': 'Data, schedule and history are preserved. {detail}', 'La sesión cambió desde la revisión. Vuelva a revisar el cambio.': 'The session has changed since review. Review the change again.', 'Cambio guardado.': 'Change saved.', 'Cambio deshecho.': 'Change undone.', 'Cambio rehecho.': 'Change redone.', 'Historial reiniciado al importar o restaurar una sesión.': 'History reset after importing or restoring a session.', 'El historial se reinició por cambios fuera del historial.': 'History reset because of changes outside history.', 'No hay cambios disponibles en el historial.': 'No changes are available in history.', 'El cambio supera el límite de memoria del historial. No se aplicó.': 'The change exceeds the history memory limit. It was not applied.', 'Los códigos de curso deben ser únicos y no estar vacíos.': 'Course codes must be unique and nonempty.', 'Datos de curso no válidos: {code}.': 'Invalid course data: {code}.', 'Las sesiones fijadas deben conservar una asignación válida.': 'Pinned sessions must retain a valid assignment.', 'Las excepciones LAB deben corresponder a sesiones asignadas.': 'LAB exceptions must belong to assigned sessions.', 'El cambio no es válido. Revise las asignaciones y las restricciones.': 'The change is invalid. Review assignments and restrictions.', 'Desfije las sesiones afectadas antes de editar los cursos.': 'Unpin affected sessions before editing courses.', '¿Eliminar todos los cursos de la lista?': 'Remove all courses from the list?'})

MESSAGES.update({'Cambiar calendario': 'Change calendar'})

MESSAGES.update({'Domingo': 'Sunday'})
MESSAGES['Se conservará el archivo original y se restablecerán las herramientas opcionales. Los parámetros de recursos de la sesión, horarios, fijaciones y escenarios no cambian. ¿Continuar?'] = 'The original file will be preserved and optional tools will be reset. Session resource parameters, timetables, pins and scenarios will not change. Continue?'

MESSAGES["Curso"] = 'Course'
MESSAGES.update({'Deshacer': 'Undo',
 'Rehacer': 'Redo',
 'Deshacer y rehacer': 'Undo and redo',
 'Revertir cambios locales de esta sesión. Máximo 50 cambios o 16 MiB; importar o restaurar reinicia el historial.': 'Revert '
                                                                                                                     'local '
                                                                                                                     'changes '
                                                                                                                     'in '
                                                                                                                     'this '
                                                                                                                     'session. '
                                                                                                                     'Up '
                                                                                                                     'to '
                                                                                                                     '50 '
                                                                                                                     'changes '
                                                                                                                     'or '
                                                                                                                     '16 '
                                                                                                                     'MiB; '
                                                                                                                     'importing '
                                                                                                                     'or '
                                                                                                                     'restoring '
                                                                                                                     'resets '
                                                                                                                     'history.',
 'Deshacer el último cambio (Ctrl+Z). Historial de esta sesión: máximo 50 cambios o 16 MiB.': 'Undo the last '
                                                                                              'change '
                                                                                              '(Ctrl+Z). '
                                                                                              'Session '
                                                                                              'history: up '
                                                                                              'to 50 changes '
                                                                                              'or 16 MiB.',
 'Rehacer el último cambio (Ctrl+Shift+Z).': 'Redo the last change (Ctrl+Shift+Z).',
 'Cambio no aplicado': 'Change not applied',
 'Se conservan los datos, el horario y el historial. {detail}': 'Data, schedule and history are preserved. '
                                                                '{detail}',
 'La sesión cambió desde la revisión. Vuelva a revisar el cambio.': 'The session has changed since review. '
                                                                    'Review the change again.',
 'Cambio guardado.': 'Change saved.',
 'Cambio deshecho.': 'Change undone.',
 'Cambio rehecho.': 'Change redone.',
 'Historial reiniciado al importar o restaurar una sesión.': 'History reset after importing or restoring a '
                                                             'session.',
 'El historial se reinició por cambios fuera del historial.': 'History reset because of changes outside '
                                                              'history.',
 'No hay cambios disponibles en el historial.': 'No changes are available in history.',
 'El cambio supera el límite de memoria del historial. No se aplicó.': 'The change exceeds the history '
                                                                       'memory limit. It was not applied.',
 'Los códigos de curso deben ser únicos y no estar vacíos.': 'Course codes must be unique and nonempty.',
 'Datos de curso no válidos: {code}.': 'Invalid course data: {code}.',
 'Las sesiones fijadas deben conservar una asignación válida.': 'Pinned sessions must retain a valid '
                                                                'assignment.',
 'Las excepciones LAB deben corresponder a sesiones asignadas.': 'LAB exceptions must belong to assigned '
                                                                 'sessions.',
 'El cambio no es válido. Revise las asignaciones y las restricciones.': 'The change is invalid. Review '
                                                                         'assignments and restrictions.',
 'Desfije las sesiones afectadas antes de editar los cursos.': 'Unpin affected sessions before editing '
                                                               'courses.',
 '¿Eliminar todos los cursos de la lista?': 'Remove all courses from the list?'})

MESSAGES.update({'Edición de cursos en lote': 'Bulk course editing',
 'Cambiar campos seleccionados con revisión previa. Requiere activar Deshacer y rehacer.': 'Change selected '
                                                                                           'fields after '
                                                                                           'preview. '
                                                                                           'Requires Undo '
                                                                                           'and redo to be '
                                                                                           'enabled.',
 'Editar en lote': 'Bulk edit',
 'Editar cursos en lote': 'Edit courses in bulk',
 'Seleccione cursos y active Deshacer y rehacer en Configuración.': 'Select courses and enable Undo and redo '
                                                                    'in Settings.',
 'Seleccione al menos un curso; no repita identificadores.': 'Select at least one course; do not repeat '
                                                             'identifiers.',
 'Marque los campos que desea cambiar. Los códigos no se pueden editar en lote.': 'Select the fields to '
                                                                                  'change. Course codes '
                                                                                  'cannot be edited in bulk.',
 'El tamaño debe ser un entero entre 0 y 100000.': 'Size must be a whole number between 0 and 100000.',
 'Seleccione un tipo de aula válido.': 'Select a valid room type.',
 'Seleccione un día válido o borre la preferencia explícitamente.': 'Select a valid day or explicitly clear '
                                                                    'the preference.',
 'La selección cambió. Cierre y vuelva a seleccionar los cursos.': 'The selection changed. Close and select '
                                                                   'the courses again.',
 'Los valores elegidos no cambian ningún curso.': 'The selected values do not change any course.',
 'Active Deshacer y rehacer en Configuración antes de editar en lote.': 'Enable Undo and redo in Settings '
                                                                        'before editing in bulk.',
 'La sesión o selección cambió desde la revisión. Vuelva a revisar el lote.': 'The session or selection '
                                                                              'changed since review. Review '
                                                                              'the batch again.',
 'Tipo de aula': 'Room type',
 'Tamaño': 'Size',
 'Día preferido': 'Preferred day',
 'Cursos seleccionados: {count}. Identificadores: {codes}': 'Selected courses: {count}. IDs: {codes}',
 'Marque solo los campos que desea cambiar. Sin marcar conserva el valor de cada curso.': 'Check only the '
                                                                                          'fields to change. '
                                                                                          'Unchecked fields '
                                                                                          'keep each '
                                                                                          'course’s current '
                                                                                          'value.',
 'Borrar preferencia': 'Clear preference',
 'Valores mezclados': 'Mixed values',
 'Conservar valor': 'Keep value',
 'Vista previa de cambios por código': 'Changes preview by code',
 'Campo': 'Field',
 'Antes': 'Before',
 'Después': 'After',
 'Revise el lote antes de aplicarlo.': 'Review the batch before applying it.',
 'Impacto en horario y restricciones': 'Impact on schedule and constraints',
 'Error de edición en lote': 'Bulk edit error',
 'Revisar cambios': 'Review changes',
 'Aplicar lote': 'Apply batch',
 'Sin preferencia': 'No preference',
 'Se dejarán pendientes {pending} asignaciones no fijadas. Se conservan {pins} sesiones fijadas y todas las restricciones. Las preferencias por grupo se conservan y pueden prevalecer sobre el día del curso.': '{pending} '
                                                                                                                                                                                                                 'unpinned '
                                                                                                                                                                                                                 'assignments '
                                                                                                                                                                                                                 'will '
                                                                                                                                                                                                                 'become '
                                                                                                                                                                                                                 'pending. '
                                                                                                                                                                                                                 '{pins} '
                                                                                                                                                                                                                 'pinned '
                                                                                                                                                                                                                 'sessions '
                                                                                                                                                                                                                 'and '
                                                                                                                                                                                                                 'all '
                                                                                                                                                                                                                 'constraints '
                                                                                                                                                                                                                 'are '
                                                                                                                                                                                                                 'preserved. '
                                                                                                                                                                                                                 'Per-group '
                                                                                                                                                                                                                 'preferences '
                                                                                                                                                                                                                 'are '
                                                                                                                                                                                                                 'kept '
                                                                                                                                                                                                                 'and '
                                                                                                                                                                                                                 'may '
                                                                                                                                                                                                                 'override '
                                                                                                                                                                                                                 'the '
                                                                                                                                                                                                                 'course '
                                                                                                                                                                                                                 'day.',
 'La herramienta no está disponible. Cierre el diálogo y revise Configuración.': 'This tool is unavailable. '
                                                                                 'Close the dialog and check '
                                                                                 'Settings.',
 'No se pudo guardar el lote. Se conservan todos los datos. {detail}': 'The batch could not be saved. All '
                                                                       'data is preserved. {detail}',
 'Lote guardado. Puede deshacerlo en una sola operación.': 'Batch saved. You can undo it in one operation.'})

MESSAGES['Cursos seleccionados'] = 'Selected courses'

MESSAGES['El historial se reinició por cambios realizados con Deshacer y rehacer desactivado.'] = 'History was reset by changes made while Undo and redo was disabled.'

MESSAGES['No se pudo restaurar la vista. Los datos se conservaron; reintente recuperar la sesión. {detail}'] = 'The view could not be restored. Data was preserved; retry session recovery. {detail}'

MESSAGES['El cambio se guardó, pero no se pudo actualizar la vista. Reintente recuperar la sesión.'] = 'The change was saved, but the view could not be updated. Retry session recovery.'

MESSAGES['No se pudo obtener acceso exclusivo a la sesión. Cierre la otra ventana de SORTH y vuelva a intentarlo. Si el problema continúa, revise los permisos de la carpeta de datos o solicite ayuda. No elimine archivos de bloqueo mientras SORTH esté abierto.'] = 'Exclusive access to the session could not be obtained. Close the other SORTH window and try again. If the problem continues, check the data folder permissions or ask for help. Do not delete lock files while SORTH is open.'

# Offline MCP add-on preparation and client guidance.
MESSAGES.update({
    'Preparar complemento MCP': 'Prepare MCP add-on',
    'Cancelar preparación MCP': 'Cancel MCP preparation',
    'Conectar un cliente MCP': 'Connect an MCP client',
    'Preparar copia el complemento incluido y lo verifica, tras tu confirmación. Se aplica inmediatamente; Cancelar configuración conserva el complemento preparado y no guarda cambios de permiso.': 'Prepare copies and checks the bundled add-on after you confirm. It takes effect immediately; cancelling Settings keeps the prepared add-on and does not save permission changes.',
    'Complemento MCP preparado y verificado. El permiso no ha cambiado. Puedes conectar un cliente y activar MCP por separado con Guardar.': 'MCP add-on prepared and verified. Permission is unchanged. You can connect a client and separately allow MCP with Save.',
    'El complemento MCP no está incluido en esta compilación. Usa una distribución que lo incluya o consulta la ruta de desarrollo en MCP_OPTIONAL.md.': 'The MCP add-on is not included in this build. Use a distribution that includes it or see the development route in MCP_OPTIONAL.md.',
    'El complemento MCP aún no está preparado. Pulsa Preparar complemento MCP y revisa la confirmación.': 'The MCP add-on is not prepared yet. Select Prepare MCP add-on and review the confirmation.',
    'Este complemento MCP requiere Windows de 64 bits. Consulta MCP_OPTIONAL.md para desarrollo desde código fuente.': 'This MCP add-on requires 64-bit Windows. See MCP_OPTIONAL.md for source development.',
    'No se pudo validar el paquete MCP. Obtén una distribución verificada de SORTH; no se instalará este paquete.': 'The MCP package could not be validated. Obtain a verified SORTH distribution; this package will not be installed.',
    'La integridad del complemento MCP no coincide. No se ejecutará. Obtén una distribución verificada de SORTH o consulta soporte antes de reparar archivos.': 'MCP add-on integrity does not match. It will not run. Obtain a verified SORTH distribution or contact support before repairing files.',
    'El complemento MCP no corresponde a esta versión de SORTH. Prepara el complemento incluido en esta compilación.': 'The MCP add-on does not match this SORTH version. Prepare the add-on included in this build.',
    'Otra preparación MCP está en curso. Espera a que termine y vuelve a intentarlo.': 'Another MCP preparation is in progress. Wait for it to finish and try again.',
    'No se pudo preparar el complemento MCP. Revisa el espacio disponible y los permisos de la carpeta de datos e inténtalo de nuevo.': 'The MCP add-on could not be prepared. Check available space and data-folder permissions, then try again.',
    'No se pudieron retirar todos los archivos temporales de la preparación MCP. El permiso no ha cambiado; consulta soporte antes de limpiar archivos manualmente.': 'Some temporary MCP preparation files could not be removed. Permission is unchanged; contact support before manually cleaning up files.',
    'El complemento MCP no superó su verificación. No está listo; revisa MCP_OPTIONAL.md antes de reintentar.': 'The MCP add-on failed verification. It is not ready; review MCP_OPTIONAL.md before retrying.',
    'Operación MCP cancelada. El permiso no ha cambiado.': 'MCP operation cancelled. Permission is unchanged.',
    'Se copiará el complemento MCP {version} incluido con SORTH a:\n{path}\n\nSe comprobará su integridad y se ejecutará una prueba local sin iniciar el servidor. No usa red ni pip y no instala en Python del sistema. Se aplica inmediatamente; Cancelar configuración no elimina el complemento. El permiso MCP y los clientes no cambian. ¿Preparar ahora?': 'The MCP add-on {version} bundled with SORTH will be copied to:\n{path}\n\nIts integrity will be checked and a local test will run without starting the server. No network or pip is used and nothing is installed in system Python. This takes effect immediately; cancelling Settings does not remove the add-on. MCP permission and clients are unchanged. Prepare now?',
    'Comprobando integridad del paquete MCP…': 'Checking MCP package integrity…',
    'Preparando archivos del complemento MCP…': 'Preparing MCP add-on files…',
    'Verificando el complemento MCP preparado…': 'Checking the prepared MCP add-on…',
    'Finalizando la preparación MCP…': 'Finishing MCP preparation…',
    'Cancelando la preparación MCP de forma segura…': 'Safely cancelling MCP preparation…',
    'Terminando la operación MCP de forma segura antes de cerrar…': 'Safely ending the MCP operation before closing…',
    'Elige tu cliente. Esta guía no modifica su configuración. Revisa privacidad, permisos y posibles cargos del proveedor antes de conectar datos. No se han probado estos hosts comerciales.': 'Choose your client. This guide does not change its configuration. Review privacy, permissions and possible provider charges before connecting data. These commercial hosts have not been tested.',
    'Cliente MCP': 'MCP client',
    'Configuración del cliente para copiar': 'Client configuration to copy',
    'Copiar configuración': 'Copy configuration',
    'Añade esta entrada a mcp.servers en opencode.jsonc sin reemplazar otras entradas. Empieza desconectada (disabled: true). Después de guardar el permiso MCP en SORTH, revisa las herramientas y conecta con /mcps. Usa protocol: legacy.': 'Add this entry to mcp.servers in opencode.jsonc without replacing other entries. It starts disconnected (disabled: true). After saving MCP permission in SORTH, review the tools and connect with /mcps. Use protocol: legacy.',
    'Integra esta entrada en mcpServers de la configuración local de Claude Desktop sin reemplazar otros servidores. Al reiniciar el cliente puede iniciar el proceso; primero guarda el permiso MCP en SORTH. Claude admite extensiones MCPB, pero SORTH no genera un paquete MCPB en este flujo.': 'Merge this entry into mcpServers in the local Claude Desktop configuration without replacing other servers. Restarting the client may start the process; first save MCP permission in SORTH. Claude supports MCPB extensions, but SORTH does not generate an MCPB package in this flow.',
    'ChatGPT necesita una conexión HTTPS o Secure MCP Tunnel autorizada por separado; esta ruta local no es una URL. El túnel requiere sus propios permisos y credenciales. SORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT. Consulta las instrucciones oficiales y las reglas de tu organización.': 'ChatGPT needs a separately authorized HTTPS or Secure MCP Tunnel connection; this local path is not a URL. The tunnel requires its own permissions and credentials. SORTH does not create tunnels or keys, open ports or configure ChatGPT. See the official instructions and your organization’s policies.',
    'Prepara y verifica el complemento para obtener su ruta exacta. En desarrollo desde código fuente, consulta MCP_OPTIONAL.md: se usa un entorno Python separado con su directorio de trabajo.': 'Prepare and verify the add-on to get its exact path. For source development, see MCP_OPTIONAL.md: use a separate Python environment with its working directory.',
    '<a href="{url}">Instrucciones oficiales del cliente</a>': '<a href="{url}">Official client instructions</a>',
    '<a href="{url}">Guía oficial de Secure MCP Tunnel</a>': '<a href="{url}">Official Secure MCP Tunnel guide</a>',
    'Configuración copiada. Revisa y combínala con la configuración existente de tu cliente.': 'Configuration copied. Review and merge it with your client’s existing configuration.',
})
MESSAGES['Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. La verificación solo comprueba este entorno; el EXE estándar no incluye MCP. Consulta MCP_OPTIONAL.md para un entorno Python separado.'] = 'Disabling MCP blocks new starts and requests and discards pending results. The client closes the stdio process; a running task can take up to 10 seconds. Preparation does not allow MCP or configure clients or models. See MCP_OPTIONAL.md for details.'
MESSAGES['<a href="{url}">Configuración local de MCP</a>'] = '<a href="{url}">Local MCP configuration</a>'

# Guided MCP setup: preparation, saved permission and client connection stay separate.
MESSAGES.update({
    '1. Preparar MCP': '1. Prepare MCP',
    'Estado del complemento MCP': 'MCP add-on status',
    'Preparar requiere confirmación y conserva el complemento aunque canceles Configuración. No concede permiso ni conecta clientes.': 'Preparation asks for confirmation and keeps the add-on even if you cancel Settings. It does not grant permission or connect clients.',
    '2. Guardar el permiso local': '2. Save local permission',
    '3. Configurar tu cliente': '3. Set up your client',
    'Ver guía de conexión': 'View connection guide',
    'Abre instrucciones para OpenCode, Claude Desktop o ChatGPT. La conexión y sus permisos se gestionan en el cliente.': 'Open instructions for OpenCode, Claude Desktop or ChatGPT. Manage the connection and its permissions in your client.',
    'Otras funciones opcionales': 'Other optional features',
    'Cambio pendiente: pulsa Guardar para permitir MCP. Cancelar conserva el permiso desactivado.': 'Unsaved change: select Save to allow MCP. Cancel keeps permission off.',
    'Cambio pendiente: pulsa Guardar para desactivar MCP. El permiso sigue activo hasta guardar.': 'Unsaved change: select Save to turn off MCP. Permission stays on until then. After saving, new requests are blocked and pending results are discarded. Close the process in your client; an in-flight task may take up to 10 seconds.',
    'Permiso guardado: activado. El cliente inicia el servidor; SORTH no lo inicia al guardar.': 'Saved permission: on. Your client starts the server; saving in SORTH does not start it.',
    'Permiso guardado: desactivado. Prepara y verifica MCP antes de permitirlo y guardar.': 'Saved permission: off. Prepare and check MCP before allowing it and saving.',
    'Cancelar verificación MCP': 'Cancel MCP check',
    'Cancelando la verificación MCP de forma segura…': 'Cancelling the MCP check safely…',
    'Guía de conexión MCP': 'MCP connection guide',
    'Sigue los pasos en tu cliente. Esta guía solo muestra instrucciones y no modifica otras apps.': 'Follow the steps in your client. This guide only shows instructions and does not change other apps.',
    'Hay un cambio de permiso sin guardar. Cierra esta guía, revisa la casilla y pulsa Guardar antes de conectar.': 'There is an unsaved permission change. Close this guide, review the checkbox and select Save before connecting.',
    'Permiso local guardado: activado. Aún debes configurar y autorizar la conexión en el cliente.': 'Saved local permission: on. You still need to set up and authorize the connection in your client.',
    'Antes de conectar, marca Permitir servidor MCP local y pulsa Guardar en Configuración.': 'Before connecting, select Allow local MCP server and Save in Settings.',
    'Antes de compartir datos, revisa la privacidad, los permisos y los posibles cargos del proveedor. Estas conexiones comerciales aún no se han probado.': 'Before sharing data, review the provider’s privacy, permissions and possible charges. These commercial-client connections have not yet been tested.',
    '1. Copia esta configuración y combina sorth-preview en mcp.servers de opencode.jsonc. Conserva las otras entradas.\n2. Empieza desconectada (disabled: true) y usa protocol: legacy.\n3. Tras guardar el permiso en SORTH, revisa las herramientas y conecta con /mcps.': '1. Copy this configuration and merge sorth-preview into mcp.servers in opencode.jsonc. Keep the other entries.\n2. It starts disconnected (disabled: true) and uses protocol: legacy.\n3. After saving permission in SORTH, review the tools and connect with /mcps.',
    '1. Copia esta configuración y combina sorth-preview en mcpServers de la configuración local de Claude Desktop. Conserva los otros servidores.\n2. Guarda primero el permiso MCP en SORTH. Reiniciar Claude puede iniciar el servidor.\n3. Revisa y autoriza las herramientas en Claude. Este flujo no genera extensiones MCPB.': '1. Copy this configuration and merge sorth-preview into mcpServers in Claude Desktop’s local configuration. Keep other servers.\n2. Save MCP permission in SORTH first. Restarting Claude may start the server.\n3. Review and authorize tools in Claude. This flow does not generate MCPB extensions.',
    'ChatGPT no acepta esta ruta local como conexión. Requiere HTTPS o Secure MCP Tunnel con autorización independiente.\n\n1. Consulta las instrucciones oficiales y las reglas de tu organización.\n2. Configura y autoriza esa conexión por separado, incluidos sus permisos y credenciales.\n\nSORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT.': 'ChatGPT cannot use this local path as a connection. It requires HTTPS or Secure MCP Tunnel with separate authorization.\n\n1. Read the official instructions and your organization’s rules.\n2. Set up and authorize that connection separately, including its permissions and credentials.\n\nSORTH does not create tunnels or keys, open ports, or configure ChatGPT.',
    'Permitir que un cliente inicie el servidor stdio. No inicia procesos, conecta modelos ni instala componentes.': 'Allow your client to start the local server. Saving does not start it or connect models.',
    'Disponibilidad MCP sin verificar en este entorno.': 'First check whether MCP is available. If the add-on is missing, you can prepare it separately.',
    'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.': 'MCP checked and available. No need to prepare it again. Review local permission in step 2.',
    'Complemento MCP preparado y verificado. El permiso no ha cambiado. Puedes conectar un cliente y activar MCP por separado con Guardar.': 'MCP add-on prepared and checked. Permission is unchanged. Continue with step 2.',
    'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.': 'The MCP Python component is missing in this environment. See MCP_OPTIONAL.md to prepare it in a separate environment. Nothing has been installed.',
    'MCP ya está disponible. Usa Verificar disponibilidad local de MCP para comprobarlo de nuevo.': 'MCP is already available. Use Check local MCP availability to check it again.',
    'Permiso guardado: desactivado. MCP está listo; marca la casilla y pulsa Guardar si deseas permitirlo.': 'Saved permission: off. MCP is ready; select the checkbox and Save if you want to allow it.',
})

MESSAGES.update({
    'Permiso local guardado: activado.': 'Saved local permission: on.',
    'Permiso local guardado: desactivado.': 'Saved local permission: off.',
    'Espera a que termine la verificación MCP antes de guardar el permiso.': 'Wait for the MCP check to finish before saving permission.',
})

# Import operation identity stays separate from accepted session data.
MESSAGES.update({
    'Archivo de la sesión: {filename}': 'Session file: {filename}',
    'Archivo en importación:': 'File being imported:',
    'Archivo en importación': 'File being imported',
    'Archivo pendiente de aceptar. La sesión actual se conserva. Lea el estado completo con F6.': 'File awaiting acceptance. The current session is preserved. Read the full status with F6.',
    'Esperando para leer {filename}… La sesión actual se conserva.': 'Waiting to read {filename}… The current session is preserved.',
    'Leyendo y validando {filename}… La sesión actual se conserva.': 'Reading and validating {filename}… The current session is preserved.',
    'Comprobando que {filename} no cambió… La sesión actual se conserva.': 'Checking that {filename} has not changed… The current session is preserved.',
    'Revisando {filename}… La sesión actual se conserva.': 'Reviewing {filename}… The current session is preserved.',
    'Guardando {filename}…': 'Saving {filename}…',
    'El archivo {filename} cambió. Revise la nueva versión validada antes de importar.': 'The file {filename} changed. Review the newly validated version before importing.',
    'Importación de {filename} cancelada. La sesión anterior se conserva.': 'Import of {filename} cancelled. The previous session is preserved.',
    'No se pudo importar {filename}. La sesión anterior se conserva. Vuelva a cargar el archivo para reintentar.': 'Could not import {filename}. The previous session is preserved. Load the file again to retry.',
})

# Keep the latest export failure readable after dismissing its dialog.
MESSAGES.update({
    'No se pudo exportar a {filename}. El horario se conserva. Revise el destino y vuelva a intentarlo.': 'Could not export to {filename}. The schedule is preserved. Check the destination and try again.',
})

# Explicit review of changed positional session identities.
MESSAGES.update({
    'Revisar asociaciones del Excel': 'Review Excel associations',
    'Hay cambios en cursos con varios grupos y asociaciones guardadas. G1, G2 y sus partes dependen del orden de las filas. SORTH no puede comprobar que sigan representando al mismo grupo.': 'Courses with multiple groups and saved associations have changed. G1, G2 and their parts depend on row order. SORTH cannot verify that they still represent the same group.',
    'Al continuar, las asociaciones y fijaciones compatibles se conservan por identificador, sin reasignarlas a otras filas. Las eliminaciones y los conflictos se revisan después. Cancelar conserva todos los datos actuales.': 'Continuing keeps compatible associations and pins by identifier, without moving them to other rows. Removals and conflicts are reviewed next. Cancel preserves all current data.',
    'Asociaciones que requieren revisión': 'Associations requiring review',
    'Continuar sin reasignar': 'Continue without remapping',
    'Duración: {minutes} min; tipo: {room_type}; estudiantes: {size}; aula preferida: {room}; día preferido: {day}; inicio preferido: {time}.': 'Duration: {minutes} min; type: {room_type}; students: {size}; preferred room: {room}; preferred day: {day}; preferred start: {time}.',
    'Antes: {details}': 'Before: {details}',
    'Excel propuesto: {details}': 'Proposed Excel: {details}',
    'Este identificador ya no aparece en el Excel propuesto.': 'This identifier is no longer present in the proposed Excel file.',
    '{kind} ({state}): {resources}': '{kind} ({state}): {resources}',
    'Inactivo': 'Inactive',
    'Fijada: {room}, {day}, {start}–{end}': 'Pinned: {room}, {day}, {start}–{end}',
})
