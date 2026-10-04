"""es presentation catalog. Keep keys stable; edit values to revise wording."""

MESSAGES = {
    'Hoja {sheet}, celda {cell}: la fórmula no tiene un resultado guardado. Recalcule y guarde el libro en Excel, o pegue los valores, antes de importarlo.': 'Hoja {sheet}, celda {cell}: la fórmula no tiene un resultado guardado. Recalcule y guarde el libro en Excel, o pegue los valores, antes de importarlo.',
    '{room_type} (guardado en el curso)': '{room_type} (guardado en el curso)',
    'La semilla guardada está fuera del intervalo permitido.': 'La semilla guardada está fuera del intervalo permitido.',
    'Comparación pendiente': 'Comparación pendiente',
    'Comparación actualizada. La sesión sigue guardada.': 'Comparación actualizada. La sesión sigue guardada.',
    'Sesión guardada. No se pudo comparar con la copia del escenario. Reintenta la comparación. {detail}': 'Sesión guardada. No se pudo comparar con la copia del escenario. Reintenta la comparación. {detail}',

    'Confirmar reemplazo': 'Confirmar reemplazo',
    'El archivo ya existe:\n{path}\n\n¿Desea reemplazarlo?': 'El archivo ya existe:\n{path}\n\n¿Desea reemplazarlo?',
    'La generación cambió u omitió grupos solicitados. Se conserva el horario anterior.': 'La generación cambió u omitió grupos solicitados. Se conserva el horario anterior.',
    'Crear un tema con IA…': 'Crear un tema con IA…',
    'Crear un tema con IA': 'Crear un tema con IA',
    'No se pudo preparar la especificación. No se ha aplicado ningún cambio.': 'No se pudo preparar la especificación. No se ha aplicado ningún cambio.',
    'Usa la IA que prefieras fuera de SORTH. Esta guía no abre ni conecta servicios, no envía datos y no realiza llamadas de pago.': 'Usa la IA que prefieras fuera de SORTH. Esta guía no abre ni conecta servicios, no envía datos y no realiza llamadas de pago.',
    '1. Copia la especificación': '1. Copia la especificación',
    'Incluye el contrato y los colores de la vista previa, con nombre y descripción de ejemplo. No incluye cursos, horarios, nombres de archivos ni datos del proyecto.': 'Incluye el contrato y los colores de la vista previa, con nombre y descripción de ejemplo. No incluye cursos, horarios, nombres de archivos ni datos del proyecto.',
    'Copiar especificación': 'Copiar especificación',
    '2. Genera el archivo en tu IA': '2. Genera el archivo en tu IA',
    'Pega la especificación, añade tus preferencias visuales y pide el archivo JSON. Revisa la privacidad y los posibles cargos de ese servicio. Si tu asistente usa habilidades, el repositorio incluye sorth-theme-designer.': 'Pega la especificación, añade tus preferencias visuales y pide el archivo JSON. Revisa la privacidad y los posibles cargos de ese servicio. Si tu asistente usa habilidades, el repositorio incluye sorth-theme-designer.',
    '3. Importa y revisa': '3. Importa y revisa',
    'La IA puede producir un tema inválido. SORTH comprobará el archivo y su contraste. Si es válido, solo cambiará la vista previa; después debes pulsar Aplicar.': 'La IA puede producir un tema inválido. SORTH comprobará el archivo y su contraste. Si es válido, solo cambiará la vista previa; después debes pulsar Aplicar.',
    'Importar resultado…': 'Importar resultado…',
    'Especificación copiada. Pégala en la IA que elijas; el tema sigue sin aplicarse.': 'Especificación copiada. Pégala en la IA que elijas; el tema sigue sin aplicarse.',
    'No se pudo confirmar la copia. Inténtalo de nuevo o selecciona el texto de la especificación y cópialo manualmente.': 'No se pudo confirmar la copia. Inténtalo de nuevo o selecciona el texto de la especificación y cópialo manualmente.',
    'Especificación y plantilla para copiar': 'Especificación y plantilla para copiar',
    'Crea un tema de interfaz SORTH según mis preferencias visuales, que añadiré a este mensaje. Devuelve un único objeto JSON UTF-8 para un archivo .sorth-theme.json, sin Markdown ni texto alrededor. Usa la plantilla completa como punto de partida. Cambia solo los colores y los metadatos del tema; no añadas campos, estilos, código, rutas, fuentes ni recursos externos. No necesitas cursos, horarios, archivos personales, cuentas ni credenciales.\n\nCumple el esquema canónico y todas las parejas de contraste indicadas. Los contrastes usan luminancia relativa sRGB WCAG, sin redondear antes de comparar. No uses claves duplicadas, NaN, Infinity, BOM, marcado ni caracteres Unicode de control o formato. El archivo final debe ocupar como máximo {limit} bytes. Si tienes el repositorio SORTH correspondiente, usa su habilidad sorth-theme-designer y su validador canónico. Si no puedes ejecutar ese validador, dilo por separado y no afirmes que el tema está validado. SORTH comprobará el resultado al importarlo; cumplir el esquema por sí solo no garantiza su aceptación ni certifica accesibilidad.': 'Crea un tema de interfaz SORTH según mis preferencias visuales, que añadiré a este mensaje. Devuelve un único objeto JSON UTF-8 para un archivo .sorth-theme.json, sin Markdown ni texto alrededor. Usa la plantilla completa como punto de partida. Cambia solo los colores y los metadatos del tema; no añadas campos, estilos, código, rutas, fuentes ni recursos externos. No necesitas cursos, horarios, archivos personales, cuentas ni credenciales.\n\nCumple el esquema canónico y todas las parejas de contraste indicadas. Los contrastes usan luminancia relativa sRGB WCAG, sin redondear antes de comparar. No uses claves duplicadas, NaN, Infinity, BOM, marcado ni caracteres Unicode de control o formato. El archivo final debe ocupar como máximo {limit} bytes. Si tienes el repositorio SORTH correspondiente, usa su habilidad sorth-theme-designer y su validador canónico. Si no puedes ejecutar ese validador, dilo por separado y no afirmes que el tema está validado. SORTH comprobará el resultado al importarlo; cumplir el esquema por sí solo no garantiza su aceptación ni certifica accesibilidad.',
    'El tema guardado se muestra en vista previa. El tema activo no cambia hasta pulsar Aplicar.': 'El tema guardado se muestra en vista previa. El tema activo no cambia hasta pulsar Aplicar.',
    'No se pudo preparar la apariencia guardada. Se muestra Original claro sin cambiar el archivo guardado. Abra Configuración → Apariencia para intentarlo de nuevo.': 'No se pudo preparar la apariencia guardada. Se muestra Original claro sin cambiar el archivo guardado. Abra Configuración → Apariencia para intentarlo de nuevo.',
    'No se pudo preparar la vista previa. No se ha aplicado ningún cambio.': 'No se pudo preparar la vista previa. No se ha aplicado ningún cambio.',
    'Sesiones': 'Sesiones',
    'El archivo del tema guardado no es válido y se conserva. Revisa Original claro en la vista previa antes de recuperarlo.': 'El archivo del tema guardado no es válido y se conserva. Revisa Original claro en la vista previa antes de recuperarlo.',
    'Las preferencias de apariencia cambiaron fuera de esta ventana. Revisa el tema guardado en la vista previa y pulsa Aplicar para usarlo.': 'Las preferencias de apariencia cambiaron fuera de esta ventana. Revisa el tema guardado en la vista previa y pulsa Aplicar para usarlo.',
    'El tema se guardó, pero la interfaz no pudo actualizarse por completo. Reinicia SORTH para terminar de aplicarlo.': 'El tema se guardó, pero la interfaz no pudo actualizarse por completo. Reinicia SORTH para terminar de aplicarlo.',
    'Apariencia': 'Apariencia',
    'Apariencia…': 'Apariencia…',
    'Hazlo tuyo': 'Hazlo tuyo',
    'Original claro': 'Original claro',
    'Nocturno': 'Nocturno',
    'Alto contraste claro': 'Alto contraste claro',
    'La identidad original de SORTH: azul marino, verde azulado y violeta.': 'La identidad original de SORTH: azul marino, verde azulado y violeta.',
    'Superficies oscuras y controles nítidos para trabajar con poca luz.': 'Superficies oscuras y controles nítidos para trabajar con poca luz.',
    'Superficies claras con bordes y texto de mayor contraste.': 'Superficies claras con bordes y texto de mayor contraste.',
    'Tu espacio de trabajo': 'Tu espacio de trabajo',
    'Vista previa interactiva · datos de ejemplo': 'Vista previa interactiva · datos de ejemplo',
    'Nombre del horario': 'Nombre del horario',
    'Escribe para probar el tema': 'Escribe para probar el tema',
    'Nombre del horario de ejemplo': 'Nombre del horario de ejemplo',
    'Probar foco': 'Probar foco',
    'Control de ejemplo. Usa Tab para ver el indicador de foco.': 'Control de ejemplo. Usa Tab para ver el indicador de foco.',
    'Probar acción': 'Probar acción',
    'No disponible': 'No disponible',
    'Los controles solo cambian esta muestra.': 'Los controles solo cambian esta muestra.',
    'Filas de ejemplo; la primera está seleccionada': 'Filas de ejemplo; la primera está seleccionada',
    'Fila seleccionada': 'Fila seleccionada',
    'Fila sin seleccionar': 'Fila sin seleccionar',
    'Matemáticas · Aula 101': 'Matemáticas · Aula 101',
    'Bloque de curso de ejemplo': 'Bloque de curso de ejemplo',
    'MAT101 · 08:00–09:00 · Matemáticas · Aula 101': 'MAT101 · 08:00–09:00 · Matemáticas · Aula 101',
    'Tonos adaptados; identidad y patrones estables.': 'Tonos adaptados; identidad y patrones estables.',
    'Aviso de ejemplo: revisa las sesiones pendientes.': 'Aviso de ejemplo: revisa las sesiones pendientes.',
    'Error de ejemplo: hay un cruce de horario.': 'Error de ejemplo: hay un cruce de horario.',
    'Acción de ejemplo completada. Tu horario no ha cambiado.': 'Acción de ejemplo completada. Tu horario no ha cambiado.',
    'Elige un tema y prueba sus controles. Solo Aplicar cambia la aplicación. Cancelar descarta esta vista previa.': 'Elige un tema y prueba sus controles. Solo Aplicar cambia la aplicación. Cancelar descarta esta vista previa.',
    'Tema': 'Tema',
    'Descripción del tema': 'Descripción del tema',
    'Importar tema JSON…': 'Importar tema JSON…',
    'Archivo local .sorth-theme.json · máximo 16 KiB. También admite temas creados con IA usando el contrato de SORTH. Sin código, fuentes ni recursos externos.': 'Archivo local .sorth-theme.json · máximo 16 KiB. También admite temas creados con IA usando el contrato de SORTH. Sin código, fuentes ni recursos externos.',
    'Conservar archivo inválido y reemplazarlo al aplicar': 'Conservar archivo inválido y reemplazarlo al aplicar',
    'Estado del tema': 'Estado del tema',
    'Detalles del error de tema': 'Detalles del error de tema',
    'El tema adapta los tonos de pantalla; PDF y Excel conservan su paleta para papel blanco. No cambia horarios, permisos MCP ni animaciones.': 'El tema adapta los tonos de pantalla; PDF y Excel conservan su paleta para papel blanco. No cambia horarios, permisos MCP ni animaciones.',
    'Restaurar original': 'Restaurar original',
    'Selecciona Original claro en la vista previa. Pulsa Aplicar para guardarlo.': 'Selecciona Original claro en la vista previa. Pulsa Aplicar para guardarlo.',
    'Aplicar': 'Aplicar',
    'Oscuro': 'Oscuro',
    'Claro': 'Claro',
    'Tema activo': 'Tema activo',
    'Vista previa sin aplicar': 'Vista previa sin aplicar',
    'Importar tema JSON': 'Importar tema JSON',
    'Tema de SORTH (*.sorth-theme.json *.json)': 'Tema de SORTH (*.sorth-theme.json *.json)',
    'No se importó el tema. Revisa el archivo; el tema activo no ha cambiado.': 'No se importó el tema. Revisa el archivo; el tema activo no ha cambiado.',
    'Archivo válido. La vista previa está lista; pulsa Aplicar para guardar una copia local.': 'Archivo válido. La vista previa está lista; pulsa Aplicar para guardar una copia local.',
    'Original claro está en vista previa. Pulsa Aplicar para restaurarlo.': 'Original claro está en vista previa. Pulsa Aplicar para restaurarlo.',
    'No se pudo aplicar el tema. El tema anterior sigue activo. Puedes volver a intentarlo.': 'No se pudo aplicar el tema. El tema anterior sigue activo. Puedes volver a intentarlo.',
    'Temas integrados o propios. Aplicar en Apariencia guarda el tema de inmediato; Guardar y Cancelar aquí solo afectan a las herramientas opcionales.': 'Temas integrados o propios. Aplicar en Apariencia guarda el tema de inmediato; Guardar y Cancelar aquí solo afectan a las herramientas opcionales.',
    'No se pudo leer la apariencia guardada. Se muestra Original claro y el archivo original se conserva. Abra Configuración → Apariencia para revisarlo o recuperarlo.': 'No se pudo leer la apariencia guardada. Se muestra Original claro y el archivo original se conserva. Abra Configuración → Apariencia para revisarlo o recuperarlo.',

    'Avanzado': 'Avanzado',
    'MCP': 'MCP',
    'Sin guardar: {count}': 'Sin guardar: {count}',
    'Sin cambios': 'Sin cambios',
    'Al desactivar un recurso, sus registros se conservan. Sus restricciones se retiran después de confirmar y regenerar el horario.': 'Al desactivar un recurso, sus registros se conservan. Sus restricciones se retiran después de confirmar y regenerar el horario.',
    'Al desactivar una herramienta se ocultan sus controles. Los escenarios, las fijaciones y el calendario guardados se conservan.': 'Al desactivar una herramienta se ocultan sus controles. Los escenarios, las fijaciones y el calendario guardados se conservan.',
    'Sin cambios por guardar': 'Sin cambios por guardar',
    'Activa solo las herramientas que necesites. Las funciones opcionales empiezan desactivadas.': 'Activa solo las herramientas que necesites. Las funciones opcionales empiezan desactivadas.',
    'Sección de configuración': 'Sección de configuración',
    'Elige General, Recursos académicos, Herramientas avanzadas o Conexión MCP. Los cambios se conservan al cambiar de sección.': 'Elige General, Recursos académicos, Herramientas avanzadas o Conexión MCP. Los cambios se conservan al cambiar de sección.',
    'General': 'General',
    'Recursos académicos': 'Recursos académicos',
    'Herramientas avanzadas': 'Herramientas avanzadas',
    'Conexión MCP': 'Conexión MCP',
    'Revisa cambios y organiza las sesiones del horario.': 'Revisa cambios y organiza las sesiones del horario.',
    'Define qué recursos deben evitar cruces de horario.': 'Define qué recursos deben evitar cruces de horario.',
    'Organiza escenarios, sesiones y parámetros del calendario.': 'Organiza escenarios, sesiones y parámetros del calendario.',
    'Prepara el complemento, guarda el permiso local y configura tu cliente.': 'Prepara el complemento, guarda el permiso local y configura tu cliente.',
    'Estado de los cambios de configuración': 'Estado de los cambios de configuración',
    'Guardar aplica las preferencias de todas las secciones en este equipo. Cancelar descarta los cambios de preferencias.': 'Guardar aplica las preferencias de todas las secciones en este equipo. Cancelar descarta los cambios de preferencias.',
    'Cambios sin guardar: {count}': 'Cambios sin guardar: {count}',

    'El permiso MCP cambió fuera de este diálogo. Se ha actualizado su casilla; revisa los cambios antes de guardar.': 'El permiso MCP cambió fuera de este diálogo. Se ha actualizado su casilla; revisa los cambios antes de guardar.',
    'Espera a que termine la operación o recupera la sesión antes de guardar la configuración.': 'Espera a que termine la operación o recupera la sesión antes de guardar la configuración.',
    'Guarda los cambios de recursos y el permiso MCP por separado. No se han guardado cambios.': 'Guarda los cambios de recursos y el permiso MCP por separado. No se han guardado cambios.',

    'Permitir servidor MCP local': 'Permitir servidor MCP local',
    'Permitir que un cliente inicie el servidor stdio. No inicia procesos, conecta modelos ni instala componentes.': 'Permitir que un cliente inicie el servidor stdio. No inicia procesos, conecta modelos ni instala componentes.',
    'Disponibilidad MCP sin verificar en este entorno.': 'Disponibilidad MCP sin verificar en este entorno.',
    'Verificar disponibilidad local de MCP': 'Verificar disponibilidad local de MCP',
    'Verificando componentes locales de MCP…': 'Verificando componentes locales de MCP…',
    'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.': 'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.',
    'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.': 'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.',
    'Versión MCP incompatible. Se requiere mcp 1.30.0; no se ha cambiado nada.': 'Versión MCP incompatible. Se requiere mcp 1.30.0; no se ha cambiado nada.',
    'Este EXE no incluye el servidor MCP opcional. Usa el código fuente y un entorno Python separado según MCP_OPTIONAL.md.': 'Este EXE no incluye el servidor MCP opcional. Usa el código fuente y un entorno Python separado según MCP_OPTIONAL.md.',
    'No se pudieron cargar los componentes MCP. Revisa el entorno siguiendo MCP_OPTIONAL.md.': 'No se pudieron cargar los componentes MCP. Revisa el entorno siguiendo MCP_OPTIONAL.md.',
    'La verificación MCP agotó el tiempo. Puedes volver a intentarlo.': 'La verificación MCP agotó el tiempo. Puedes volver a intentarlo.',
    'Verificación MCP cancelada.': 'Verificación MCP cancelada.',
    'Verifica que MCP esté disponible antes de activarlo. No se han guardado cambios.': 'Verifica que MCP esté disponible antes de activarlo. No se han guardado cambios.',
    'Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. La verificación solo comprueba este entorno; el EXE estándar no incluye MCP. Consulta MCP_OPTIONAL.md para un entorno Python separado.': 'Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. La verificación solo comprueba este entorno; el EXE estándar no incluye MCP. Consulta MCP_OPTIONAL.md para un entorno Python separado.',

    'La sesión y sus parámetros de recursos no cambiaron. Algunas preferencias de herramientas se guardaron y no se pudieron restaurar. Recupere la configuración antes de continuar. {detail}': 'La sesión y sus parámetros de recursos no cambiaron. Algunas preferencias de herramientas se guardaron y no se pudieron restaurar. Recupere la configuración antes de continuar. {detail}',
    'Actualizar recursos': 'Actualizar recursos',
    'compact_assigned_count': {'one': '{n} asignada', 'other': '{n} asignadas'},
    'compact_pending_count': {'one': '{n} pendiente', 'other': '{n} pendientes'},
    'Parámetros activos: {count}': 'Parámetros activos: {count}',
    'Calendario personalizado': 'Calendario personalizado',

    'Herramientas del horario (F7)': 'Herramientas del horario (F7)',

    '{name}: {state} ({count})': '{name}: {state} ({count})',
    'La sesión guardada se conserva. La vista requiere recuperación antes de continuar.': 'La sesión guardada se conserva. La vista requiere recuperación antes de continuar.',
    'Sin valor': 'Sin valor',
    'Grupo {number}: aula {room}, día {day}, hora {time}': 'Grupo {number}: aula {room}, día {day}, hora {time}',
    "Cancelando…": 'Cancelando…',
    'Opciones de ubicación': 'Opciones de ubicación',
    'Mostrar ubicaciones válidas para sesiones pendientes sin mover otras sesiones.': 'Mostrar ubicaciones válidas para sesiones pendientes sin mover otras sesiones.',
    'Ver opciones': 'Ver opciones',
    'Opciones para {gid}': 'Opciones para {gid}',
    'Opciones del horario actual, sin mover otras sesiones. Búsqueda cada 30 minutos y en horas guardadas; la asignación manual permite otras horas.': 'Opciones del horario actual, sin mover otras sesiones. Búsqueda cada 30 minutos y en horas guardadas; la asignación manual permite otras horas.',
    'Resultado de opciones': 'Resultado de opciones',
    'Ubicaciones válidas para la sesión pendiente': 'Ubicaciones válidas para la sesión pendiente',
    'Recalcular opciones': 'Recalcular opciones',
    'La sesión o la herramienta ya no está disponible. No se aplicó ningún cambio.': 'La sesión o la herramienta ya no está disponible. No se aplicó ningún cambio.',
    'El horario cambió. Opciones recalculadas; elija de nuevo.': 'El horario cambió. Opciones recalculadas; elija de nuevo.',
    '{count} opciones en el horario actual.': '{count} opciones en el horario actual.',
    'No hay opciones en el horario actual. Esto no demuestra imposibilidad global.': 'No hay opciones en el horario actual. Esto no demuestra imposibilidad global.',
    'Búsqueda limitada: se muestran solo los primeros resultados válidos.': 'Búsqueda limitada: se muestran solo los primeros resultados válidos.',
    'Asignar opción válida': 'Asignar opción válida',

    "Generación cancelada. Se conserva el horario anterior.": 'Generación cancelada. Se conserva el horario anterior.',
    'No se pudo leer la configuración opcional. Abre Configuración para conservarla y recuperarla.': 'No se pudo leer la configuración opcional. Abre Configuración para conservarla y recuperarla.',
    'Herramientas de sesiones fijadas': 'Herramientas de sesiones fijadas',
    'Mostrar controles para fijar o desfijar. Las fijaciones guardadas siempre se respetan.': 'Mostrar controles para fijar o desfijar. Las fijaciones guardadas siempre se respetan.',
    'Herramientas de proyectos y escenarios': 'Herramientas de proyectos y escenarios',
    'Mostrar controles para guardar, abrir y comparar copias independientes.': 'Mostrar controles para guardar, abrir y comparar copias independientes.',
    'La configuración opcional no se puede leer. Puedes conservar el archivo original y restablecer solo estas herramientas.': 'La configuración opcional no se puede leer. Puedes conservar el archivo original y restablecer solo estas herramientas.',
    'Conservar original y restablecer herramientas': 'Conservar original y restablecer herramientas',
    'Se conservará el archivo original y se desactivarán las herramientas opcionales. Los horarios, fijaciones y escenarios no cambian. ¿Continuar?': 'Se conservará el archivo original y se desactivarán las herramientas opcionales. Los horarios, fijaciones y escenarios no cambian. ¿Continuar?',
    'Duración (minutos)': 'Duración (minutos)',
    'Tipo de aula requerido': 'Tipo de aula requerido',
    'Estudiantes': 'Estudiantes',
    'Aula sugerida': 'Aula sugerida',
    'Inicio preferido (minutos)': 'Inicio preferido (minutos)',
    'Preferencias por grupo': 'Preferencias por grupo',
    'División de sesiones': 'División de sesiones',
    'Capacidad': 'Capacidad',
    'Tipo de aula': 'Tipo de aula',
    'Descripción': 'Descripción',
    'Campus': 'Campus',
    '    {field}: {before} → {after}': '    {field}: {before} → {after}',

    'Cancelar importación': 'Cancelar importación',
    'Progreso de importación': 'Progreso de importación',
    'Leyendo y validando Excel… La sesión actual se conserva.': 'Leyendo y validando Excel… La sesión actual se conserva.',
    'Importación cancelada. La sesión anterior se conserva.': 'Importación cancelada. La sesión anterior se conserva.',
    'El archivo cambió. Revise la nueva versión validada antes de importar.': 'El archivo cambió. Revise la nueva versión validada antes de importar.',
    'Comprobando que el archivo no cambió…': 'Comprobando que el archivo no cambió…',
    'Cancelando importación antes de cerrar…': 'Cancelando importación antes de cerrar…',
    'El archivo cambió mientras se leía. Selecciónelo nuevamente.': 'El archivo cambió mientras se leía. Selecciónelo nuevamente.',
    'Revisar cambios del Excel': 'Revisar cambios del Excel',
    'Se reemplazarán los cursos y aulas. Se borrarán las restricciones y las asignaciones no conservadas. Cancelar mantiene la sesión actual.': 'Se reemplazarán los cursos y aulas. Se borrarán las restricciones y las asignaciones no conservadas. Cancelar mantiene la sesión actual.',
    'Cambios de importación': 'Cambios de importación',
    'Reemplazar con este Excel': 'Reemplazar con este Excel',
    'Archivo: {name}': 'Archivo: {name}',
    'Añadidos': 'Añadidos',
    'Modificados': 'Modificados',
    'Eliminados': 'Eliminados',
    '{label}: {count}': '{label}: {count}',
    'Restricciones que se borrarán: {count}': 'Restricciones que se borrarán: {count}',
    'Asignaciones que se borrarán': 'Asignaciones que se borrarán',
    'Sesiones fijadas que se conservarán': 'Sesiones fijadas que se conservarán',
    'Vista previa de cambios del Excel': 'Vista previa de cambios del Excel',
    'Revisar cursos, aulas, restricciones y asignaciones antes de reemplazar la sesión.': 'Revisar cursos, aulas, restricciones y asignaciones antes de reemplazar la sesión.',

    'Cancelar generación': 'Cancelar generación',
    'Cancelando generación; se conservarán el horario y las sesiones fijadas.': 'Cancelando generación; se conservarán el horario y las sesiones fijadas.',

    'La generación cambió sesiones fijadas. Se conserva el horario anterior.': 'La generación cambió sesiones fijadas. Se conserva el horario anterior.',
    'La sesión fijada {gid} requiere confirmar una excepción LAB.': 'La sesión fijada {gid} requiere confirmar una excepción LAB.',
    'Sesión fijada': 'Sesión fijada',
    'Desfije la sesión antes de cambiar su asignación.': 'Desfije la sesión antes de cambiar su asignación.',
    'La estructura dividida de {gid} cambió.': 'La estructura dividida de {gid} cambió.',
    'Sesiones fijadas en conflicto': 'Sesiones fijadas en conflicto',
    'Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.': 'Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.',
    'Fijar sesión': 'Fijar sesión',
    'Conservar solo esta sesión al regenerar; no es una preferencia.': 'Conservar solo esta sesión al regenerar; no es una preferencia.',
    'Desfijar sesión': 'Desfijar sesión',
    'Fijada · {state}': 'Fijada · {state}',
    'Desfije las sesiones antes de limpiar el horario.': 'Desfije las sesiones antes de limpiar el horario.',

    'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.': 'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.',
    'Versión del formato': 'Versión del formato',
    'Aula: preferencias pendientes / desconocidas': 'Aula: preferencias pendientes / desconocidas',
    'Hora: preferencias pendientes / desconocidas': 'Hora: preferencias pendientes / desconocidas',
    'Día: preferencias pendientes / desconocidas': 'Día: preferencias pendientes / desconocidas',
    'Valores diferentes (izquierda / derecha)': 'Valores diferentes (izquierda / derecha)',
    'Nombre (1–120 caracteres)': 'Nombre (1–120 caracteres)',
    'Proyectos y escenarios': 'Proyectos y escenarios',
    'Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.': 'Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.',
    'Proyecto': 'Proyecto',
    'Escenario': 'Escenario',
    'Guardado (UTC)': 'Guardado (UTC)',
    'Escenarios guardados': 'Escenarios guardados',
    'Crear proyecto desde la sesión': 'Crear proyecto desde la sesión',
    'Guardar como escenario': 'Guardar como escenario',
    'Abrir escenario': 'Abrir escenario',
    'Duplicar': 'Duplicar',
    'Renombrar': 'Renombrar',
    'Comparar': 'Comparar',
    'Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.': 'Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.',
    'No se pudo completar la operación. El escenario guardado se conserva. {detail}': 'No se pudo completar la operación. El escenario guardado se conserva. {detail}',
    'Escenario guardado. Las ediciones posteriores no cambian esta copia.': 'Escenario guardado. Las ediciones posteriores no cambian esta copia.',
    'Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?': 'Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?',
    'Comparar escenarios': 'Comparar escenarios',
    'Indicadores descriptivos, sin ganador ni puntuación global.': 'Indicadores descriptivos, sin ganador ni puntuación global.',
    'No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.': 'No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.',
    'Cursos': 'Cursos',
    'Aulas': 'Aulas',
    'Restricciones': 'Restricciones',
    'Sesiones fijas': 'Sesiones fijas',
    'Semilla': 'Semilla',
    'Calendario': 'Calendario',
    'Versión del algoritmo': 'Versión del algoritmo',
    'Versión de métricas': 'Versión de métricas',
    'Recursos': 'Recursos',
    'Diferencias: {details}': 'Diferencias: {details}',
    'Ninguna': 'Ninguna',
    'Indicador': 'Indicador',
    'El calendario guardado no es compatible. No se recalcularon indicadores con reglas diferentes.': 'El calendario guardado no es compatible. No se recalcularon indicadores con reglas diferentes.',
    'Sesiones asignadas / total': 'Sesiones asignadas / total',
    'Sesiones pendientes': 'Sesiones pendientes',
    'Preferencia de día: satisfechas / evaluadas': 'Preferencia de día: satisfechas / evaluadas',
    'Preferencia de hora: satisfechas / evaluadas': 'Preferencia de hora: satisfechas / evaluadas',
    'Preferencia de aula: satisfechas / evaluadas': 'Preferencia de aula: satisfechas / evaluadas',
    'Ocupación: minutos-aula / disponibles': 'Ocupación: minutos-aula / disponibles',
    'Excepciones activas': 'Excepciones activas',
    'No lectivo': 'No lectivo',
    'Docencia, día {day} (min)': 'Docencia, día {day} (min)',
    'No se pudo abrir el catálogo. La sesión actual se conserva. {detail}': 'No se pudo abrir el catálogo. La sesión actual se conserva. {detail}',
    'Cambios posteriores a la copia': 'Cambios posteriores a la copia',
    'Copia guardada': 'Copia guardada',
    '{name} · {state} · {save}': '{name} · {state} · {save}',
    'Ningún archivo seleccionado': 'Ningún archivo seleccionado',
    'El PDF filtrado requiere el total global de asignaciones.': 'El PDF filtrado requiere el total global de asignaciones.',
    'El alcance y el total de asignaciones no coinciden.': 'El alcance y el total de asignaciones no coinciden.',
    'El número de sesiones pendientes no puede ser negativo.': 'El número de sesiones pendientes no puede ser negativo.',
    'El PDF no admite algunos caracteres o escrituras de los datos. Use Excel/CSV para conservarlos.': 'El PDF no admite algunos caracteres o escrituras de los datos. Use Excel/CSV para conservarlos.',
    'Vista filtrada': 'Vista filtrada',
    'Todas las asignaciones': 'Todas las asignaciones',
    'Estado global: pendientes no informados': 'Estado global: pendientes no informados',
    'Horario PARCIAL: {pending} pendientes': 'Horario PARCIAL: {pending} pendientes',
    'Horario completo: 0 pendientes': 'Horario completo: 0 pendientes',
    '{scope} | {count} exportadas de {total} asignadas | {state}': '{scope} | {count} exportadas de {total} asignadas | {state}',
    'SORTH - Horario por aula': 'SORTH - Horario por aula',
    'SORTH {version} | Horario por aula': 'SORTH {version} | Horario por aula',
    'Horas exactas HH:mm | Texto seleccionable | SORTH': 'Horas exactas HH:mm | Texto seleccionable | SORTH',
    'Página {page}': 'Página {page}',
    'Un texto es demasiado largo para la página PDF.': 'Un texto es demasiado largo para la página PDF.',
    'No aplicados (se exportan todas las asignaciones).': 'No aplicados (se exportan todas las asignaciones).',
    'Filtros no informados por el solicitante.': 'Filtros no informados por el solicitante.',
    'Alcance y leyenda': 'Alcance y leyenda',
    'Filtros: {filters}': 'Filtros: {filters}',
    'Un color por curso; los nombres completos aparecen en cada fila. CONFLICTO identifica sesiones simultáneas. EXCEPCIÓN LAB identifica una autorización de aula registrada. Continuación repite día, horas y grupo cuando un nombre ocupa varias páginas. Los pendientes corresponden al horario global, no sólo a esta vista.': 'Un color por curso; los nombres completos aparecen en cada fila. CONFLICTO identifica sesiones simultáneas. EXCEPCIÓN LAB identifica una autorización de aula registrada. Continuación repite día, horas y grupo cuando un nombre ocupa varias páginas. Los pendientes corresponden al horario global, no sólo a esta vista.',
    'Día no válido para {group}.': 'Día no válido para {group}.',
    'Sin sesiones asignadas en este alcance.': 'Sin sesiones asignadas en este alcance.',
    'Aula: {room} | Sesiones: {count}': 'Aula: {room} | Sesiones: {count}',
    'El nombre del aula es demasiado largo para el encabezado PDF.': 'El nombre del aula es demasiado largo para el encabezado PDF.',
    'Inicio - Fin': 'Inicio - Fin',
    'Nombre completo del curso': 'Nombre completo del curso',
    'Avisos': 'Avisos',
    'CONFLICTO': 'CONFLICTO',
    'EXCEPCIÓN LAB': 'EXCEPCIÓN LAB',
    '(Sin nombre de curso)': '(Sin nombre de curso)',
    'Continuación': 'Continuación',
    'Buscar': 'Buscar',
    '(sin búsqueda)': '(sin búsqueda)',
    'Guardar el horario generado en Excel (.xlsx), CSV o PDF.\nEl Excel incluye una grilla visual; el PDF, tablas por aula para imprimir.': 'Guardar el horario generado en Excel (.xlsx), CSV o PDF.\nEl Excel incluye una grilla visual; el PDF, tablas por aula para imprimir.',
    "Archivos Excel (*.xlsx);;Archivos CSV (*.csv);;Documentos PDF (*.pdf)": 'Archivos Excel (*.xlsx);;Archivos CSV (*.csv);;Documentos PDF (*.pdf)',
    'El libro supera el límite de importación. Divídalo en archivos más pequeños.': 'El libro supera el límite de importación. Divídalo en archivos más pequeños.',
    '⚠️ Horario parcial: {p1}/{p3} grupos; {pending} pendientes': '⚠️ Horario parcial: {p1}/{p3} grupos; {pending} pendientes',
    'Sin resultado': 'Sin resultado',
    'No se obtuvo un resultado. Revise los datos y vuelva a generar el horario.': 'No se obtuvo un resultado. Revise los datos y vuelva a generar el horario.',

    '{scope} · horario parcial, {pending} pendientes': '{scope} · horario parcial, {pending} pendientes',
    '{gid}: identificador de grupo duplicado': '{gid}: identificador de grupo duplicado',
    '{gid}: asignación mal formada': '{gid}: asignación mal formada',
    'Exportar todas las asignaciones': 'Exportar todas las asignaciones',
    'todas las asignaciones': 'todas las asignaciones',

    "\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.": "\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.",
    "\n⚠️  {p1} grupo(s) sin asignar.\nRevisa la Lista Detallada (marcados en rojo).": "\n⚠️  {p1} grupo(s) sin asignar.\nRevisa la Lista Detallada (marcados en rojo).",
    "  {p1}  {p3}": "  {p1}  {p3}",
    "  ·  Cargue un Excel para comenzar": "  ·  Cargue un Excel para comenzar",
    "  ·  Listo para generar": "  ·  Listo para generar",
    "  ·  {p1}/{p3} sesiones asignadas": "  ·  {p1}/{p3} sesiones asignadas",
    "  ⚠️  {p1}": "  ⚠️  {p1}",
    "  💾  Sesión anterior encontrada": "  💾  Sesión anterior encontrada",
    " Consulte las sesiones sin asignar en Lista detallada.": " Consulte las sesiones sin asignar en Lista detallada.",
    " · {p1} tramo(s) con conflicto": " · {p1} tramo(s) con conflicto",
    "&Aula:": "&Aula:",
    "&Buscar:": "&Buscar:",
    "&Día:": "&Día:",
    "&Estado:": "&Estado:",
    "(Sin preferencia)": "(Sin preferencia)",
    ". No hay coincidencias; cambie o restablezca los filtros.": ". No hay coincidencias; cambie o restablezca los filtros.",
    "1. Cargue un Excel con las hojas Aulas y Cursos (nombres exactos).\n2. Revise los cursos y configure aulas o restricciones.\n3. Genere el horario, revise los grupos pendientes y exporte.": "1. Cargue un Excel con las hojas Aulas y Cursos (nombres exactos).\n2. Revise los cursos y configure aulas o restricciones.\n3. Genere el horario, revise los grupos pendientes y exporte.",
    "Abrir": "Abrir",
    "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: # DE AULA y CAPACIDAD (entero ≥ 0)\n  • Cursos: Curso; cada fila es un grupo sugerido\nOpcionales: Nombre de Curso, Horas (0800-1055), Aula y Días (L,I,M,J,V,S).\nLos encabezados van en la fila 1; el orden de columnas no importa.": "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: # DE AULA y CAPACIDAD (entero ≥ 0)\n  • Cursos: Curso; cada fila es un grupo sugerido\nOpcionales: Nombre de Curso, Horas (0800-1055), Aula y Días (L,I,M,J,V,S).\nLos encabezados van en la fila 1; el orden de columnas no importa.",
    "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: código, descripción, campus, capacidad\n  • Cursos: cada fila es un grupo sugerido": "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: código, descripción, campus, capacidad\n  • Cursos: cada fila es un grupo sugerido",
    "Aceptar": "Aceptar",
    "Activar hora preferida": "Activar hora preferida",
    "Activar para usar una semilla aleatoria en cada generación": "Activar para usar una semilla aleatoria en cada generación",
    "Active un aula para restringirla. Luego marque los cursos que pueden usarla (los desmarcados quedan libres).": "Active un aula para restringirla. Luego marque los cursos que pueden usarla (los desmarcados quedan libres).",
    "Advertencia": "Advertencia",
    "Agregar Aula": "Agregar Aula",
    "Agregar Curso": "Agregar Curso",
    "Agregar aula": "Agregar aula",
    "Agregar un aula nueva a la sesión actual.\nÚtil para aulas que no están en el Excel pero deben estar disponibles.": "Agregar un aula nueva a la sesión actual.\nÚtil para aulas que no están en el Excel pero deben estar disponibles.",
    "Agregar un nuevo curso manualmente a la lista": "Agregar un nuevo curso manualmente a la lista",
    "Aleatoria": "Aleatoria",
    "Archivo Excel:": "Archivo Excel:",
    "Asignaciones ordenadas por aula": "Asignaciones ordenadas por aula",
    "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual.": "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual.",
    "Asignado": "Asignado",
    "Asignados": "Asignados",
    "Asignar": "Asignar",
    "Asignar manualmente": "Asignar manualmente",
    "Asignar sesión manualmente": "Asignar sesión manualmente",
    "Aula": "Aula",
    "Aula Sugerida": "Aula Sugerida",
    "Aula Sugerida:": "Aula Sugerida:",
    "Aula de la &cuadrícula:": "Aula de la &cuadrícula:",
    "Aula de la cuadrícula": "Aula de la cuadrícula",
    "Aulas con Restricciones": "Aulas con Restricciones",
    "Aulas utilizadas": "Aulas utilizadas",
    "Aulas utilizadas:    {p1}": "Aulas utilizadas:    {p1}",
    "Aulas, fila {row}: '{room}' no tiene capacidad; se usará 0.": "Aulas, fila {row}: '{room}' no tiene capacidad; se usará 0.",
    "Aulas, fila {row}: CAPACIDAD debe ser un entero mayor o igual a 0.": "Aulas, fila {row}: CAPACIDAD debe ser un entero mayor o igual a 0.",
    "Aulas, fila {row}: el aula '{room}' está duplicada.": "Aulas, fila {row}: el aula '{room}' está duplicada.",
    "Aulas, fila {row}: falta # DE AULA.": "Aulas, fila {row}: falta # DE AULA.",
    "Aulas:": "Aulas:",
    "Aulas: agregue al menos un aula con # DE AULA.": "Aulas: agregue al menos un aula con # DE AULA.",
    "Automático (dividir si > 4.5h)": "Automático (dividir si > 4.5h)",
    "Automático: se divide solo si la duración supera 4.5 horas.\nForzar división: siempre se divide en bloques de 2h en días distintos.\nNo dividir: se asigna completo en un solo día sin importar la duración.": "Automático: se divide solo si la duración supera 4.5 horas.\nForzar división: siempre se divide en bloques de 2h en días distintos.\nNo dividir: se asigna completo en un solo día sin importar la duración.",
    "Avisos del archivo: {count}": "Avisos del archivo: {count}",
    "Aún no hay cursos. Cargue un Excel o agregue su primer curso.": "Aún no hay cursos. Cargue un Excel o agregue su primer curso.",
    "Buscar cursos": "Buscar cursos",
    "Buscar en todo el horario": "Buscar en todo el horario",
    "Buscar por código o nombre de curso…": "Buscar por código o nombre de curso…",
    "Cambiar idioma sin modificar los datos ni los formatos de exportación": "Cambiar idioma sin modificar los datos ni los formatos de exportación",
    "Cambios sin guardar": "Cambios sin guardar",
    "Campus:": "Campus:",
    "Cancelar": "Cancelar",
    "Capacidad *:": "Capacidad *:",
    "Cargar Excel": "Cargar Excel",
    "Cargue un Excel o agregue al menos un aula primero.": "Cargue un Excel o agregue al menos un aula primero.",
    "Cargue un Excel o agregue cursos y aulas para comenzar.": "Cargue un Excel o agregue cursos y aulas para comenzar.",
    "Cerrar": "Cerrar",
    "Configurar qué aulas están reservadas exclusivamente para ciertos cursos.\nLos cursos restringidos SOLO pueden asignarse a su aula designada.": "Configurar qué aulas están reservadas exclusivamente para ciertos cursos.\nLos cursos restringidos SOLO pueden asignarse a su aula designada.",
    "Confirmar": "Confirmar",
    "Confirmar eliminación": "Confirmar eliminación",
    "Confirmar excepción de laboratorio": "Confirmar excepción de laboratorio",
    "Conflicto de aula\n": "Conflicto de aula\n",
    "Desempata opciones con la misma prioridad.\nMismos datos y semilla fija → mismo horario.\nSemilla aleatoria → puede ofrecer alternativas, sin garantizar un horario distinto.": "Desempata opciones con la misma prioridad.\nMismos datos y semilla fija → mismo horario.\nSemilla aleatoria → puede ofrecer alternativas, sin garantizar un horario distinto.",
    "Hoja {sheet}, celda {cell}: contiene un error de Excel. Corríjalo y vuelva a cargar el archivo.": "Hoja {sheet}, celda {cell}: contiene un error de Excel. Corríjalo y vuelva a cargar el archivo.",
    "Corrija el archivo y vuelva a cargarlo:": "Corrija el archivo y vuelva a cargarlo:",
    "Cuadrícula por aula": "Cuadrícula por aula",
    "Cuadrícula semanal por aula": "Cuadrícula semanal por aula",
    "Curso ya existe": "Curso ya existe",
    "Cursos a programar": "Cursos a programar",
    "Cursos para {p1}:": "Cursos para {p1}:",
    "Cursos programados": "Cursos programados",
    "Cursos programados:  {p1}": "Cursos programados:  {p1}",
    "Cursos, fila {row}: Días admite L, I, M, J, V, S separados por comas; I=martes y M=miércoles.": "Cursos, fila {row}: Días admite L, I, M, J, V, S separados por comas; I=martes y M=miércoles.",
    "Cursos, fila {row}: Horas debe ser HHMM-HHMM, con fin posterior al inicio (ej. 0800-1055).": "Cursos, fila {row}: Horas debe ser HHMM-HHMM, con fin posterior al inicio (ej. 0800-1055).",
    "Cursos, fila {row}: el aula '{room}' no aparece en Aulas; se importará sin esa preferencia.": "Cursos, fila {row}: el aula '{room}' no aparece en Aulas; se importará sin esa preferencia.",
    "Cursos, fila {row}: falta Curso (código).": "Cursos, fila {row}: falta Curso (código).",
    "Cursos: agregue al menos una fila con Curso (código).": "Cursos: agregue al menos una fila con Curso (código).",
    "Código": "Código",
    "Código *:": "Código *:",
    "Código del Curso:": "Código del Curso:",
    "Código, nombre de curso, grupo o aula": "Código, nombre de curso, grupo o aula",
    "Datos actualizados. Genere un nuevo horario para exportar.": "Datos actualizados. Genere un nuevo horario para exportar.",
    "Dejar la sesión seleccionada sin asignar": "Dejar la sesión seleccionada sin asignar",
    "Desactiva las transiciones y el indicador animado.": "Desactiva las transiciones y el indicador animado.",
    "Descartar": "Descartar",
    "Descripción:": "Descripción:",
    "Desmarcar todos": "Desmarcar todos",
    "Detectado automáticamente por el código (L al inicio → LAB).\nPuedes cambiarlo manualmente si es necesario.": "Detectado automáticamente por el código (L al inicio → LAB).\nPuedes cambiarlo manualmente si es necesario.",
    "División en días:": "División en días:",
    "Domingo": "Domingo",
    "Duplicado": "Duplicado",
    "Duración": "Duración",
    "Duración:": "Duración:",
    "Día": "Día",
    "Día Preferido": "Día Preferido",
    "Día Preferido:": "Día Preferido:",
    "Editar Curso": "Editar Curso",
    "Editar curso": "Editar curso",
    "Editar curso {p1}": "Editar curso {p1}",
    "Editar el curso de la sesión seleccionada; será necesario generar de nuevo": "Editar el curso de la sesión seleccionada; será necesario generar de nuevo",
    "Editar el curso seleccionado en la tabla": "Editar el curso seleccionado en la tabla",
    "Ej: Aula General": "Ej: Aula General",
    "Ej: Biología General (opcional)": "Ej: Biología General (opcional)",
    "Ej: HO": "Ej: HO",
    "Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.": "Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.",
    "El aula '{p1}' ya existe.": "El aula '{p1}' ya existe.",
    "El curso '{p1}' ya existe en la lista.\n¿Deseas modificarlo en su lugar?": "El curso '{p1}' ya existe en la lista.\n¿Deseas modificarlo en su lugar?",
    "El curso {p1} no se encuentra en la lista de cursos.": "El curso {p1} no se encuentra en la lista de cursos.",
    "El código del aula es obligatorio.": "El código del aula es obligatorio.",
    "El código del curso es obligatorio.": "El código del curso es obligatorio.",
    "Eliminar el curso seleccionado de la lista": "Eliminar el curso seleccionado de la lista",
    "Eliminar todas las asignaciones del horario actual": "Eliminar todas las asignaciones del horario actual",
    "Eliminar todos los cursos de la lista": "Eliminar todos los cursos de la lista",
    "En curso": "En curso",
    "Error": "Error",
    "Error al cargar archivo Excel:\n{p1}": "Error al cargar archivo Excel:\n{p1}",
    "Error al exportar:\n{p1}": "Error al exportar:\n{p1}",
    "Error al generar el horario:\n{p1}": "Error al generar el horario:\n{p1}",
    "Espere a que termine la generación antes de cerrar.": "Espere a que termine la generación antes de cerrar.",
    "Estado": "Estado",
    "Estado de guardado": "Estado de guardado",
    "Excepción manual LAB": "Excepción manual LAB",
    "Excepción manual confirmada: laboratorio en aula regular.": "Excepción manual confirmada: laboratorio en aula regular.",
    "Exportar completo": "Exportar completo",
    "Exportar completo incluye todas las asignaciones. Exportar filtrado usa Buscar, Aula, Día y Estado; no el aula de la cuadrícula.": "Los archivos contienen sesiones asignadas. Exportar filtrado usa Buscar, Aula, Día y Estado; no el aula de la cuadrícula.",
    "Exportar filtrado (0)": "Exportar filtrado (0)",
    "Exportar filtrado ({p1})": "Exportar filtrado ({p1})",
    "\nEn Excel también se incluyen todas las sesiones pendientes del horario, aunque no coincidan con los filtros.": "\nEn Excel también se incluyen todas las sesiones pendientes del horario, aunque no coincidan con los filtros.",
    "Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.": "Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.",
    "Faltan las hojas: {missing}. Use esos nombres exactos. Hojas encontradas: {found}": "Faltan las hojas: {missing}. Use esos nombres exactos. Hojas encontradas: {found}",
    "Filtrar por aula": "Filtrar por aula",
    "Filtrar por día": "Filtrar por día",
    "Filtrar por estado": "Filtrar por estado",
    "Fin": "Fin",
    "Forzar división en varios días": "Forzar división en varios días",
    "Generando…": "Generando…",
    "Generar horario": "Generar horario",
    "Genere un horario para consultar sus sesiones y exportar los resultados.": "Genere un horario para consultar sus sesiones y exportar los resultados.",
    "Grupo": "Grupo",
    "Grupo / sesión": "Grupo / sesión",
    "Grupos": "Grupos",
    "Grupos asignados:    {p1} / {p3}": "Grupos asignados:    {p1} / {p3}",
    "Guardar": "Guardar",
    "Guardar el horario generado en formato Excel (.xlsx) o CSV.\nEl Excel incluye una grilla visual por aula.": "Guardar el horario generado en formato Excel (.xlsx) o CSV.\nEl Excel incluye una grilla visual por aula.",
    "Guardar horario {p1} · {p3} sesiones": "Guardar horario {p1} · {p3} sesiones",
    "Guía rápida": "Guía rápida",
    "Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.": "Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.",
    "Hoja {sheet}, fila 1: falta la columna {columns}. Revise el encabezado.": "Hoja {sheet}, fila 1: falta la columna {columns}. Revise el encabezado.",
    "Hoja {sheet}: agregue los encabezados en la fila 1.": "Hoja {sheet}: agregue los encabezados en la fila 1.",
    "Hora": "Hora",
    "Hora Preferida": "Hora Preferida",
    "Hora Preferida:": "Hora Preferida:",
    "Hora de inicio preferida para este curso (ej: 08:00, 13:00)": "Hora de inicio preferida para este curso (ej: 08:00, 13:00)",
    "Horario eliminado.": "Horario eliminado.",
    "Horario no válido": "Horario no válido",
    "Horario {p1}: {p3} sesiones exportadas a {p5}": "Horario {p1}: {p3} sesiones exportadas a {p5}",
    "Horario {p1}: {p3} sesiones exportadas a:\n{p5}": "Horario {p1}: {p3} sesiones exportadas a:\n{p5}",
    "Idioma de la interfaz": "Idioma de la interfaz",
    "Idioma:": "Idioma:",
    "Importar con avisos": "Importar con avisos",
    "Info": "Info",
    "Inicio": "Inicio",
    "Jueves": "Jueves",
    "La búsqueda automática no encontró un horario compatible con las asignaciones actuales. Esto no demuestra que sea imposible; revise horarios, restricciones o asigne manualmente.": "La búsqueda automática no encontró un horario compatible con las asignaciones actuales. Esto no demuestra que sea imposible; revise horarios, restricciones o asigne manualmente.",
    "La duración no cabe en el horario permitido sin cruzar el almuerzo.": "La duración no cabe en el horario permitido sin cruzar el almuerzo.",
    "Las restricciones de cursos excluyen todas las aulas compatibles.": "Las restricciones de cursos excluyen todas las aulas compatibles.",
    "Libro de Excel (*.xlsx)": "Libro de Excel (*.xlsx)",
    "Limpiar horario": "Limpiar horario",
    "Lista detallada": "Lista detallada",
    "Lista detallada del horario": "Lista detallada del horario",
    "Listo. Cargue un archivo Excel para comenzar.": "Listo. Cargue un archivo Excel para comenzar.",
    "Lunes": "Lunes",
    "Marcar todos": "Marcar todos",
    "Martes": "Martes",
    "Miércoles": "Miércoles",
    "Mostrando {p1} de {p3} sesiones": "Mostrando {p1} de {p3} sesiones",
    "Mostrando {p1} de {p3} sesión": "Mostrando {p1} de {p3} sesión",
    "Motivo y excepciones de la sesión seleccionada": "Motivo y excepciones de la sesión seleccionada",
    "Ningún aula del tipo permitido tiene capacidad suficiente.": "Ningún aula del tipo permitido tiene capacidad suficiente.",
    "No": "No",
    "No dividir (asignar en un solo día)": "No dividir (asignar en un solo día)",
    "No hay aulas con cursos asociados en el Excel.": "No hay aulas con cursos asociados en el Excel.",
    "No hay horario para exportar.": "No hay horario para exportar.",
    "No hay laboratorios configurados. Puede elegir un aula regular manualmente y confirmar la excepción.": "No hay laboratorios configurados. Puede elegir un aula regular manualmente y confirmar la excepción.",
    "No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.": "No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.",
    "No se cargó el archivo. La sesión anterior se conserva.": "No se cargó el archivo. La sesión anterior se conserva.",
    "No se encontró el archivo. Selecciónelo nuevamente.": "No se encontró el archivo. Selecciónelo nuevamente.",
    "No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.": "No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.",
    "No se pudo generar un horario válido.\n\nPosibles causas:\n  • No hay suficientes aulas disponibles\n  • Restricciones demasiado estrictas\n  • Conflictos de horario entre cursos": "No se pudo generar un horario válido.\n\nPosibles causas:\n  • No hay suficientes aulas disponibles\n  • Restricciones demasiado estrictas\n  • Conflictos de horario entre cursos",
    "No se pudo guardar la sesión. Si sales, perderás los cambios sin guardar.\nEl último guardado y las copias existentes se conservarán.\n\n{p1}": "No se pudo guardar la sesión. Si sales, perderás los cambios sin guardar.\nEl último guardado y las copias existentes se conservarán.\n\n{p1}",
    "No se pudo guardar la sesión: {p1}": "No se pudo guardar la sesión: {p1}",
    "No se pudo guardar o recuperar la sesión: {p1}": "No se pudo guardar o recuperar la sesión: {p1}",
    "No se pudo leer el libro. Ábralo en Excel y guarde una copia .xlsx sin contraseña.": "No se pudo leer el libro. Ábralo en Excel y guarde una copia .xlsx sin contraseña.",
    "Nombre": "Nombre",
    "Nombre del curso": "Nombre del curso",
    "Nombre:": "Nombre:",
    "Número de Grupos:": "Número de Grupos:",
    "Organización de horarios académicos": "Organización de horarios académicos",
    "Por aula": "Por aula",
    "Por favor agregue al menos un curso.": "Por favor agregue al menos un curso.",
    "Quitar del horario": "Quitar del horario",
    "Quitar sesión del horario": "Quitar sesión del horario",
    "Recuperación pendiente": "Recuperación pendiente",
    "Reducir animaciones": "Reducir animaciones",
    "Reintentar": "Reintentar",
    "Restablecer filtros": "Restablecer filtros",
    "Restricciones de aulas": "Restricciones de aulas",
    "Restricciones de aulas eliminadas.": "Restricciones de aulas eliminadas.",
    "Resultado de validación": "Resultado de validación",
    "Resumen del Horario": "Resumen del Horario",
    "Revisar importación": "Revisar importación",
    "SORTH - Sistema de Organización de Horarios": "SORTH - Sistema de Organización de Horarios",
    "Se encontró una sesión guardada.\n¿Deseas restaurarla?": "Se encontró una sesión guardada.\n¿Deseas restaurarla?",
    "Seleccionar archivo Excel": "Seleccionar archivo Excel",
    "Seleccione el aula, día y hora. Se comprobarán todas las restricciones.": "Seleccione el aula, día y hora. Se comprobarán todas las restricciones.",
    "Seleccione un aula": "Seleccione un aula",
    "Seleccione un aula.": "Seleccione un aula.",
    "Seleccione un curso para editar.": "Seleccione un curso para editar.",
    "Seleccione un curso para eliminar.": "Seleccione un curso para eliminar.",
    "Seleccione una fila para editar o quitar.": "Seleccione una fila para editar o quitar.",
    "Semilla:": "Semilla:",
    "Sesiones asignadas": "Sesiones asignadas",
    "Sesiones por aula": "Sesiones por aula",
    "Sesiones por día": "Sesiones por día",
    "Sesiones sin asignar (ver Lista detallada)": "Sesiones sin asignar (ver Lista detallada)",
    "Sesión anterior": "Sesión anterior",
    "Sesión no disponible": "Sesión no disponible",
    "Sin archivo seleccionado": "Sin archivo seleccionado",
    "Sin asignar": "Sin asignar",
    "Sin cambios pendientes": "Sin cambios pendientes",
    "Sin coincidencias": "Sin coincidencias",
    "Sin sesiones para esta aula y estos filtros.": "Sin sesiones para esta aula y estos filtros.",
    "Sin solución": "Sin solución",
    "Sábado": "Sábado",
    "Sí": "Sí",
    "Tipo de Sala:": "Tipo de Sala:",
    "Tipo de sala:": "Tipo de sala:",
    "Todas": "Todas",
    "Todos": "Todos",
    "Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).": "Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).",
    "Valor de semilla fija para resultados reproducibles": "Valor de semilla fija para resultados reproducibles",
    "Valor: ": "Valor: ",
    "Ver resumen": "Ver resumen",
    "Ver, agregar, editar y eliminar los cursos a programar": "Ver, agregar, editar y eliminar los cursos a programar",
    "Viernes": "Viernes",
    "Visualizar el horario generado en lista, cuadrícula o por aula": "Visualizar el horario generado en lista, cuadrícula o por aula",
    "classroom_count": {
        "one": "{n} aula",
        "other": "{n} aulas"
    },
    "completo": "completo",
    "course_count": {
        "one": "{n} curso",
        "other": "{n} cursos"
    },
    "filtrado": "filtrado",
    "placeholder.classroom_code": "Ej: A-DEMO-1, L-DEMO-1",
    "placeholder.course_code": "Ej: DEM101, DEM111L",
    "placeholder.preferred_classroom": "Ej: A-DEMO-1, L-DEMO-1 (opcional)",
    "result_count": {
        "one": "Mostrando {visible} de {n} sesión",
        "other": "Mostrando {visible} de {n} sesiones"
    },
    "session_count": {
        "one": "{n} sesión",
        "other": "{n} sesiones"
    },
    "{gid}: capacidad insuficiente": "{gid}: capacidad insuficiente",
    "{gid}: conflicto de aula": "{gid}: conflicto de aula",
    "{gid}: duración incorrecta": "{gid}: duración incorrecta",
    "{gid}: grupo o aula desconocido": "{gid}: grupo o aula desconocido",
    "{gid}: horario fuera del intervalo permitido": "{gid}: horario fuera del intervalo permitido",
    "{gid}: requiere laboratorio; falta confirmar la excepción manual": "{gid}: requiere laboratorio; falta confirmar la excepción manual",
    "{gid}: restricción de aula": "{gid}: restricción de aula",
    "{gid}: sesiones divididas deben usar días distintos y la misma hora": "{gid}: sesiones divididas deben usar días distintos y la misma hora",
    "{n} aula": "{n} aula",
    "{n} aulas": "{n} aulas",
    "{n} curso": "{n} curso",
    "{n} cursos": "{n} cursos",
    "{n} sesiones": "{n} sesiones",
    "{n} sesión": "{n} sesión",
    "{p0} cursos  ·  {p2} sesiones  ·  {p4} aulas": "{p0} cursos  ·  {p2} sesiones  ·  {p4} aulas",
    "{p0} requiere laboratorio. ¿Asignarlo al aula regular {p2}?\nEsta excepción manual quedará registrada en la sesión.": "{p0} requiere laboratorio. ¿Asignarlo al aula regular {p2}?\nEsta excepción manual quedará registrada en la sesión.",
    "{p0} sesiones asignadas · {p2} sin asignar · {p4} aulas utilizadas": "{p0} sesiones asignadas · {p2} sin asignar · {p4} aulas utilizadas",
    "{p0} sesiones{p2}. Horas exactas en cada bloque; detalle completo al señalarlo.": "{p0} sesiones{p2}. Horas exactas en cada bloque; detalle completo al señalarlo.",
    "{p0} · {p2} min · {p4} estudiantes": "{p0} · {p2} min · {p4} estudiantes",
    "¿Eliminar el curso {p1}?": "¿Eliminar el curso {p1}?",
    "¿Eliminar todas las asignaciones del horario actual?\nSe conservarán los cursos y las aulas para generar un horario nuevo.": "¿Eliminar todas las asignaciones del horario actual?\nSe conservarán los cursos y las aulas para generar un horario nuevo.",
    "¿Eliminar todos los cursos de la lista?\nEsta acción no se puede deshacer.": "¿Eliminar todos los cursos de la lista?\nEsta acción no se puede deshacer.",
    "¿Quitar {p1} del horario?\nLa sesión quedará sin asignar y no se exportará.": "¿Quitar {p1} del horario?\nLa sesión quedará sin asignar y no se exportará.",
    "Éxito": "Éxito",
    "… y {count} errores más.": "… y {count} errores más.",
    "⏳ Generando horario...": "⏳ Generando horario...",
    "⚠️ No se pudo restaurar la sesión: {p1}": "⚠️ No se pudo restaurar la sesión: {p1}",
    "✅ Aula '{p1}' agregada ({p3}, cap={p5})": "✅ Aula '{p1}' agregada ({p3}, cap={p5})",
    "✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)": "✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)",
    "✅ Horario generado: {p1}/{p3} grupos": "✅ Horario generado: {p1}/{p3} grupos",
    "✅ Sesión restaurada correctamente.": "✅ Sesión restaurada correctamente.",
    "✅ {p1} aula(s) con restricciones configuradas.": "✅ {p1} aula(s) con restricciones configuradas.",
    "✏️ Editar": "✏️ Editar",
    "❌ Error al generar horario": "❌ Error al generar horario",
    "❌ No se pudo generar el horario": "❌ No se pudo generar el horario",
    "➕ Agregar Curso": "➕ Agregar Curso",
    "🏫 REGULAR (detectado automáticamente)": "🏫 REGULAR (detectado automáticamente)",
    "📅 Horario Generado": "📅 Horario Generado",
    "📚 Gestión de Cursos": "📚 Gestión de Cursos",
    "🔒 Aulas con Restricciones": "🔒 Aulas con Restricciones",
    "🔒 Restricciones ({p1})": "🔒 Restricciones ({p1})",
    "🔬 LAB (detectado automáticamente)": "🔬 LAB (detectado automáticamente)",
    "🗑️ Eliminar": "🗑️ Eliminar",
    "🧹 Limpiar Todo": "🧹 Limpiar Todo"
}

# Grid scope and native session details.
MESSAGES.update({
    'Filtros globales · Asignadas exportables: {assigned} · Pendientes: {pending} · Sesiones: {visible}/{total}': 'Filtros globales · Asignadas exportables: {assigned} · Pendientes: {pending} · Sesiones: {visible}/{total}',
    'Sesiones en esta aula: {count}': 'Sesiones en esta aula: {count}',
    'El aula de la cuadrícula no cambia la exportación filtrada.': 'El aula de la cuadrícula no cambia la exportación filtrada.',
    'Ver detalles': 'Ver detalles',
    'Detalles de la sesión': 'Detalles de la sesión',
    'Sesiones del bloque en conflicto': 'Sesiones del bloque en conflicto',
    'Seleccione una sesión para verla en la lista.': 'Seleccione una sesión para verla en la lista.',
    'Ver en lista': 'Ver en lista',
    'Sesión: {gid}\nCurso: {course}\nAula: {room}\nDía: {day}\nHorario: {start}–{end}': 'Sesión: {gid}\nCurso: {course}\nAula: {room}\nDía: {day}\nHorario: {start}–{end}',
    'Seleccione un bloque y pulse Intro o Ver detalles para leer la sesión completa.': 'Seleccione un bloque y pulse Intro o Ver detalles para leer la sesión completa.',
    'Use flechas para recorrer la cuadrícula, Intro para ver detalles y Tab para salir.': 'Use flechas para recorrer la cuadrícula, Intro para ver detalles y Tab para salir.',
})

QT_MESSAGES = {
    'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.': 'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.',
    'Versión del formato': 'Versión del formato',
    'Aula: preferencias pendientes / desconocidas': 'Aula: preferencias pendientes / desconocidas',
    'Hora: preferencias pendientes / desconocidas': 'Hora: preferencias pendientes / desconocidas',
    'Día: preferencias pendientes / desconocidas': 'Día: preferencias pendientes / desconocidas',
    'Valores diferentes (izquierda / derecha)': 'Valores diferentes (izquierda / derecha)',
    "&Cancel": "&Cancelar",
    "&Close": "&Cerrar",
    "&Copy": "&Copiar",
    "&Delete": "&Eliminar",
    "&Discard": "&Descartar",
    "&No": "&No",
    "&OK": "&Aceptar",
    "&Open": "&Abrir",
    "&Paste": "&Pegar",
    "&Redo": "&Rehacer",
    "&Retry": "&Reintentar",
    "&Save": "&Guardar",
    "&Select All": "&Seleccionar todo",
    "&Undo": "&Deshacer",
    "&Yes": "&Sí",
    "Cancel": "Cancelar",
    "Clear": "Limpiar",
    "Clear contents": "Limpiar contenido",
    "Close": "Cerrar",
    "Copy": "Copiar",
    "Cu&t": "Cor&tar",
    "Cut": "Cortar",
    "Delete": "Eliminar",
    "Discard": "Descartar",
    "Hide Details...": "Ocultar detalles...",
    "No": "No",
    "OK": "Aceptar",
    "Open": "Abrir",
    "Paste": "Pegar",
    "Redo": "Rehacer",
    "Retry": "Reintentar",
    "Save": "Guardar",
    "Select All": "Seleccionar todo",
    "Show Details...": "Mostrar detalles...",
    "Undo": "Deshacer",
    "Yes": "Sí"
}

# Explainable schedule quality indicators.
MESSAGES.update({'No aplica': 'No aplica',
 'Calidad del horario completo': 'Calidad del horario completo',
 'Los filtros no cambian estos indicadores. Son descriptivos: no validan restricciones ni demuestran un óptimo.': 'Los '
                                                                                                                  'filtros '
                                                                                                                  'no '
                                                                                                                  'cambian '
                                                                                                                  'estos '
                                                                                                                  'indicadores. '
                                                                                                                  'Son '
                                                                                                                  'descriptivos: '
                                                                                                                  'no '
                                                                                                                  'validan '
                                                                                                                  'restricciones '
                                                                                                                  'ni '
                                                                                                                  'demuestran '
                                                                                                                  'un '
                                                                                                                  'óptimo.',
 'Grupos originales: {complete} completos, {partial} parciales, {pending} pendientes y {unknown} desconocidos, de {total}. Las preferencias cuentan cada sesión dividida por separado.': 'Grupos '
                                                                                                                                                                                         'originales: '
                                                                                                                                                                                         '{complete} '
                                                                                                                                                                                         'completos, '
                                                                                                                                                                                         '{partial} '
                                                                                                                                                                                         'parciales, '
                                                                                                                                                                                         '{pending} '
                                                                                                                                                                                         'pendientes '
                                                                                                                                                                                         'y '
                                                                                                                                                                                         '{unknown} '
                                                                                                                                                                                         'desconocidos, '
                                                                                                                                                                                         'de '
                                                                                                                                                                                         '{total}. '
                                                                                                                                                                                         'Las '
                                                                                                                                                                                         'preferencias '
                                                                                                                                                                                         'cuentan '
                                                                                                                                                                                         'cada '
                                                                                                                                                                                         'sesión '
                                                                                                                                                                                         'dividida '
                                                                                                                                                                                         'por '
                                                                                                                                                                                         'separado.',
 'Día preferido': 'Día preferido',
 'Hora preferida': 'Hora preferida',
 'Aula preferida': 'Aula preferida',
 'Preferencia': 'Preferencia',
 'Pendientes': 'Pendientes',
 'Desconocidas': 'Desconocidas',
 'Sin preferencia': 'Sin preferencia',
 'Coincidencia exacta de día, hora de inicio y aula. El denominador incluye sólo preferencias asignadas y conocidas; pendientes, desconocidas y ausentes se muestran aparte. Sin denominador: no aplica.': 'Coincidencia '
                                                                                                                                                                                                           'exacta '
                                                                                                                                                                                                           'de '
                                                                                                                                                                                                           'día, '
                                                                                                                                                                                                           'hora '
                                                                                                                                                                                                           'de '
                                                                                                                                                                                                           'inicio '
                                                                                                                                                                                                           'y '
                                                                                                                                                                                                           'aula. '
                                                                                                                                                                                                           'El '
                                                                                                                                                                                                           'denominador '
                                                                                                                                                                                                           'incluye '
                                                                                                                                                                                                           'sólo '
                                                                                                                                                                                                           'preferencias '
                                                                                                                                                                                                           'asignadas '
                                                                                                                                                                                                           'y '
                                                                                                                                                                                                           'conocidas; '
                                                                                                                                                                                                           'pendientes, '
                                                                                                                                                                                                           'desconocidas '
                                                                                                                                                                                                           'y '
                                                                                                                                                                                                           'ausentes '
                                                                                                                                                                                                           'se '
                                                                                                                                                                                                           'muestran '
                                                                                                                                                                                                           'aparte. '
                                                                                                                                                                                                           'Sin '
                                                                                                                                                                                                           'denominador: '
                                                                                                                                                                                                           'no '
                                                                                                                                                                                                           'aplica.',
 'Distribución de carga por día': 'Distribución de carga por día',
 'Minutos de docencia': 'Minutos de docencia',
 'Se suman minutos de cada sesión, incluso si son simultáneas. Se incluyen días sin carga; no se presupone que una distribución uniforme sea mejor.': 'Se '
                                                                                                                                                      'suman '
                                                                                                                                                      'minutos '
                                                                                                                                                      'de '
                                                                                                                                                      'cada '
                                                                                                                                                      'sesión, '
                                                                                                                                                      'incluso '
                                                                                                                                                      'si '
                                                                                                                                                      'son '
                                                                                                                                                      'simultáneas. '
                                                                                                                                                      'Se '
                                                                                                                                                      'incluyen '
                                                                                                                                                      'días '
                                                                                                                                                      'sin '
                                                                                                                                                      'carga; '
                                                                                                                                                      'no '
                                                                                                                                                      'se '
                                                                                                                                                      'presupone '
                                                                                                                                                      'que '
                                                                                                                                                      'una '
                                                                                                                                                      'distribución '
                                                                                                                                                      'uniforme '
                                                                                                                                                      'sea '
                                                                                                                                                      'mejor.',
 'Ocupación temporal de aulas': 'Ocupación temporal de aulas',
 'Minutos ocupados únicos / minutos disponibles, descontando almuerzo y exclusiones. Incluye aulas sin uso; no mide asientos ocupados ni compatibilidad de cursos.': 'Minutos '
                                                                                                                                                                     'ocupados '
                                                                                                                                                                     'únicos '
                                                                                                                                                                     '/ '
                                                                                                                                                                     'minutos '
                                                                                                                                                                     'disponibles, '
                                                                                                                                                                     'descontando '
                                                                                                                                                                     'almuerzo '
                                                                                                                                                                     'y '
                                                                                                                                                                     'exclusiones. '
                                                                                                                                                                     'Incluye '
                                                                                                                                                                     'aulas '
                                                                                                                                                                     'sin '
                                                                                                                                                                     'uso; '
                                                                                                                                                                     'no '
                                                                                                                                                                     'mide '
                                                                                                                                                                     'asientos '
                                                                                                                                                                     'ocupados '
                                                                                                                                                                     'ni '
                                                                                                                                                                     'compatibilidad '
                                                                                                                                                                     'de '
                                                                                                                                                                     'cursos.',
 'Minutos ocupados / disponibles': 'Minutos ocupados / disponibles',
 'Total': 'Total',
 'Ninguna': 'Ninguna',
 'Hay datos desconocidos o incompletos. Los indicadores no sustituyen la revisión de integridad.': 'Hay '
                                                                                                   'datos '
                                                                                                   'desconocidos '
                                                                                                   'o '
                                                                                                   'incompletos. '
                                                                                                   'Los '
                                                                                                   'indicadores '
                                                                                                   'no '
                                                                                                   'sustituyen '
                                                                                                   'la '
                                                                                                   'revisión '
                                                                                                   'de '
                                                                                                   'integridad.',
 'Cumplidas': 'Cumplidas',
 'Excepciones manuales activas de laboratorio / sesiones asignadas: {ratio}. Confirmadas: {ids}. Sin confirmar: {unconfirmed}. No evaluables: {unknown}. Registros inactivos: {inactive}.': 'Excepciones '
                                                                                                                                                                                            'manuales '
                                                                                                                                                                                            'activas '
                                                                                                                                                                                            'de '
                                                                                                                                                                                            'laboratorio '
                                                                                                                                                                                            '/ '
                                                                                                                                                                                            'sesiones '
                                                                                                                                                                                            'asignadas: '
                                                                                                                                                                                            '{ratio}. '
                                                                                                                                                                                            'Confirmadas: '
                                                                                                                                                                                            '{ids}. '
                                                                                                                                                                                            'Sin '
                                                                                                                                                                                            'confirmar: '
                                                                                                                                                                                            '{unconfirmed}. '
                                                                                                                                                                                            'No '
                                                                                                                                                                                            'evaluables: '
                                                                                                                                                                                            '{unknown}. '
                                                                                                                                                                                            'Registros '
                                                                                                                                                                                            'inactivos: '
                                                                                                                                                                                            '{inactive}.'})

# Keyboard and assistive-technology labels.
MESSAGES.update({'Use flechas para recorrer celdas y Tab para salir. En tablas ordenables, Ctrl+Mayús+Arriba o Abajo ordena la columna actual.': 'Use '
                                                                                                                                 'flechas '
                                                                                                                                 'para '
                                                                                                                                 'recorrer '
                                                                                                                                 'celdas '
                                                                                                                                 'y '
                                                                                                                                 'Tab '
                                                                                                                                 'para '
                                                                                                                                 'salir. '
                                                                                                                                 'En '
                                                                                                                                 'tablas '
                                                                                                                                 'ordenables, '
                                                                                                                                 'Ctrl+Mayús+Arriba '
                                                                                                                                 'o '
                                                                                                                                 'Abajo '
                                                                                                                                 'ordena '
                                                                                                                                 'la '
                                                                                                                                 'columna '
                                                                                                                                 'actual.',
 'Aulas con restricciones': 'Aulas con restricciones',
 'Use flechas para seleccionar y Espacio para marcar o desmarcar.': 'Use flechas para seleccionar y Espacio '
                                                                    'para marcar o desmarcar.',
 'Cursos permitidos en el aula seleccionada': 'Cursos permitidos en el aula seleccionada',
 'Duración en horas': 'Duración en horas',
 'Duración en minutos': 'Duración en minutos',
 'Hora de inicio preferida': 'Hora de inicio preferida',
 'Semilla fija': 'Semilla fija',
 'Progreso de generación': 'Progreso de generación',
 'Leer estado (F6)': 'Leer estado (F6)',
 'Estado actual': 'Estado actual',
 'Use flechas para recorrer la cuadrícula y Tab para salir. La Lista detallada ofrece las mismas sesiones en filas, con estado y acciones.': 'Use '
                                                                                                                                             'flechas '
                                                                                                                                             'para '
                                                                                                                                             'recorrer '
                                                                                                                                             'la '
                                                                                                                                             'cuadrícula '
                                                                                                                                             'y '
                                                                                                                                             'Tab '
                                                                                                                                             'para '
                                                                                                                                             'salir. '
                                                                                                                                             'La '
                                                                                                                                             'Lista '
                                                                                                                                             'detallada '
                                                                                                                                             'ofrece '
                                                                                                                                             'las '
                                                                                                                                             'mismas '
                                                                                                                                             'sesiones '
                                                                                                                                             'en '
                                                                                                                                             'filas, '
                                                                                                                                             'con '
                                                                                                                                             'estado '
                                                                                                                                             'y '
                                                                                                                                             'acciones.'})

# Optional feature settings
MESSAGES.update({'Configuración': 'Configuración',
 'Sesiones fijadas': 'Sesiones fijadas',
 'Fijar o desfijar sesiones para conservar su ubicación al regenerar.': 'Fijar o desfijar sesiones para '
                                                                        'conservar su ubicación al '
                                                                        'regenerar.',
 'Guardar copias independientes, abrir escenarios y compararlos.': 'Guardar copias independientes, '
                                                                   'abrir escenarios y compararlos.',
 'Las funciones opcionales empiezan desactivadas. Los cambios se guardan en este equipo.': 'Las '
                                                                                           'funciones '
                                                                                           'opcionales '
                                                                                           'empiezan '
                                                                                           'desactivadas. '
                                                                                           'Los cambios '
                                                                                           'se guardan '
                                                                                           'en este '
                                                                                           'equipo.',
 'Desactivar oculta los controles, sin borrar datos. Las sesiones ya fijadas siguen protegidas. Las validaciones de seguridad siempre están activas.': 'Desactivar '
                                                                                                                                                       'oculta '
                                                                                                                                                       'los '
                                                                                                                                                       'controles, '
                                                                                                                                                       'sin '
                                                                                                                                                       'borrar '
                                                                                                                                                       'datos. '
                                                                                                                                                       'Las '
                                                                                                                                                       'sesiones '
                                                                                                                                                       'ya '
                                                                                                                                                       'fijadas '
                                                                                                                                                       'siguen '
                                                                                                                                                       'protegidas. '
                                                                                                                                                       'Las '
                                                                                                                                                       'validaciones '
                                                                                                                                                       'de '
                                                                                                                                                       'seguridad '
                                                                                                                                                       'siempre '
                                                                                                                                                       'están '
                                                                                                                                                       'activas.',
 'MCP se instala y se inicia por separado; esta configuración no activa servicios externos.': 'MCP se '
                                                                                              'instala '
                                                                                              'y se '
                                                                                              'inicia '
                                                                                              'por '
                                                                                              'separado; '
                                                                                              'esta '
                                                                                              'configuración '
                                                                                              'no '
                                                                                              'activa '
                                                                                              'servicios '
                                                                                              'externos.',
 'Se ocultarán los controles para fijar sesiones. Las sesiones ya fijadas seguirán condicionando la generación. Para cambiarlas, vuelve a activar esta función. ¿Guardar configuración?': 'Se '
                                                                                                                                                                                          'ocultarán '
                                                                                                                                                                                          'los '
                                                                                                                                                                                          'controles '
                                                                                                                                                                                          'para '
                                                                                                                                                                                          'fijar '
                                                                                                                                                                                          'sesiones. '
                                                                                                                                                                                          'Las '
                                                                                                                                                                                          'sesiones '
                                                                                                                                                                                          'ya '
                                                                                                                                                                                          'fijadas '
                                                                                                                                                                                          'seguirán '
                                                                                                                                                                                          'condicionando '
                                                                                                                                                                                          'la '
                                                                                                                                                                                          'generación. '
                                                                                                                                                                                          'Para '
                                                                                                                                                                                          'cambiarlas, '
                                                                                                                                                                                          'vuelve '
                                                                                                                                                                                          'a '
                                                                                                                                                                                          'activar '
                                                                                                                                                                                          'esta '
                                                                                                                                                                                          'función. '
                                                                                                                                                                                          '¿Guardar '
                                                                                                                                                                                          'configuración?',
 'No se pudo guardar la configuración. Revisa los permisos e inténtalo de nuevo.': 'No se pudo guardar '
                                                                                   'la configuración. '
                                                                                   'Revisa los permisos '
                                                                                   'e inténtalo de '
                                                                                   'nuevo.',
 'Datos de funciones desactivadas': 'Datos de funciones desactivadas',
 'Hay sesiones fijadas: siguen protegidas. Activa Sesiones fijadas en Configuración para modificarlas.': 'Hay '
                                                                                                         'sesiones '
                                                                                                         'fijadas: '
                                                                                                         'siguen '
                                                                                                         'protegidas. '
                                                                                                         'Activa '
                                                                                                         'Sesiones '
                                                                                                         'fijadas '
                                                                                                         'en '
                                                                                                         'Configuración '
                                                                                                         'para '
                                                                                                         'modificarlas.',
 'Hay datos de escenarios conservados. Activa Proyectos y escenarios en Configuración para acceder.': 'Hay '
                                                                                                      'datos '
                                                                                                      'de '
                                                                                                      'escenarios '
                                                                                                      'conservados. '
                                                                                                      'Activa '
                                                                                                      'Proyectos '
                                                                                                      'y '
                                                                                                      'escenarios '
                                                                                                      'en '
                                                                                                      'Configuración '
                                                                                                      'para '
                                                                                                      'acceder.'})

MESSAGES.update({'Calendario del proyecto': 'Calendario del proyecto', 'Define días lectivos, horas y descansos. El calendario guardado se respeta aunque ocultes el editor.': 'Define días lectivos, horas y descansos. El calendario guardado se respeta aunque ocultes el editor.', 'Hora de apertura': 'Hora de apertura', 'Hora de cierre': 'Hora de cierre', 'Las horas se expresan en HH:mm. Para terminar a medianoche, usa 00:00 como cierre.': 'Las horas se expresan en HH:mm. Para terminar a medianoche, usa 00:00 como cierre.', 'Descansos del proyecto': 'Descansos del proyecto', 'Añadir descanso': 'Añadir descanso', 'Quitar descanso seleccionado': 'Quitar descanso seleccionado', 'Restablecer calendario predeterminado': 'Restablecer calendario predeterminado', 'Resultado de la revisión del calendario': 'Resultado de la revisión del calendario', 'Revisar y aplicar': 'Revisar y aplicar', 'Inicio del descanso': 'Inicio del descanso', 'Fin del descanso': 'Fin del descanso', 'Revisa días, horas y descansos: deben ser válidos, no solaparse y dejar tiempo lectivo. {detail}': 'Revisa días, horas y descansos: deben ser válidos, no solaparse y dejar tiempo lectivo. {detail}', 'Hay sesiones fijadas afectadas. Desfíjalas explícitamente antes de cambiar el calendario.': 'Hay sesiones fijadas afectadas. Desfíjalas explícitamente antes de cambiar el calendario.', 'Ninguna': 'Ninguna', 'Revisar calendario': 'Revisar calendario', 'Sesiones que quedarán pendientes: {sessions}. Las demás conservan su día y hora. ¿Aplicar el calendario?': 'Sesiones que quedarán pendientes: {sessions}. Las demás conservan su día y hora. ¿Aplicar el calendario?', 'No se pudo guardar el calendario. No se aplicaron cambios.': 'No se pudo guardar el calendario. No se aplicaron cambios.', 'Calendario personalizado activo: se respeta aunque el editor esté oculto. Puedes revisarlo en Configuración.': 'Calendario personalizado activo: se respeta aunque el editor esté oculto. Puedes revisarlo en Configuración.', 'Parámetros avanzados del calendario': 'Parámetros avanzados del calendario', 'Mostrar el editor de días, horas y descansos del proyecto. El calendario guardado siempre se respeta.': 'Mostrar el editor de días, horas y descansos del proyecto. El calendario guardado siempre se respeta.', 'Editar calendario del proyecto': 'Editar calendario del proyecto'})

MESSAGES.update({'Guardar configuración y editar calendario': 'Guardar configuración y editar calendario'})
MESSAGES.update({'Docentes': 'Docentes',
 'Grupos de estudiantes': 'Grupos de estudiantes',
 'Estudiantes individuales': 'Estudiantes individuales',
 'Asignar docentes por sesión y evitar cruces de horario.': 'Asignar docentes por sesión y evitar cruces de '
                                                            'horario.',
 'Asignar grupos compartidos y evitar cruces de horario.': 'Asignar grupos compartidos y evitar cruces de '
                                                           'horario.',
 'Asignar personas explícitas con alias locales y evitar cruces.': 'Asignar personas explícitas con alias '
                                                                   'locales y evitar cruces.',
 'Editar recurso': 'Editar recurso',
 'Nombre o alias': 'Nombre o alias',
 'Use un alias si lo prefiere. No se necesitan correos, edades ni identificaciones personales.': 'Use un '
                                                                                                 'alias si '
                                                                                                 'lo '
                                                                                                 'prefiere. '
                                                                                                 'No se '
                                                                                                 'necesitan '
                                                                                                 'correos, '
                                                                                                 'edades ni '
                                                                                                 'identificaciones '
                                                                                                 'personales.',
 'Limitar a la disponibilidad declarada': 'Limitar a la disponibilidad declarada',
 'Sin declarar: no limita horarios. Declarada sin franjas: ninguna sesión puede asignarse.': 'Sin declarar: '
                                                                                             'no limita '
                                                                                             'horarios. '
                                                                                             'Declarada sin '
                                                                                             'franjas: '
                                                                                             'ninguna sesión '
                                                                                             'puede '
                                                                                             'asignarse.',
 'Disponibilidad declarada': 'Disponibilidad declarada',
 'Agregar franja': 'Agregar franja',
 'Quitar franja': 'Quitar franja',
 'Revise el nombre y las franjas: el final debe ser posterior al inicio.': 'Revise el nombre y las franjas: '
                                                                           'el final debe ser posterior al '
                                                                           'inicio.',
 'Disponibilidad vacía': 'Disponibilidad vacía',
 'No se permitirá ninguna sesión para este recurso. ¿Guardar disponibilidad vacía?': 'No se permitirá '
                                                                                     'ninguna sesión para '
                                                                                     'este recurso. ¿Guardar '
                                                                                     'disponibilidad vacía?',
 'Agregue recursos y elija explícitamente sus sesiones. No se asignan personas automáticamente.': 'Agregue '
                                                                                                  'recursos '
                                                                                                  'y elija '
                                                                                                  'explícitamente '
                                                                                                  'sus '
                                                                                                  'sesiones. '
                                                                                                  'No se '
                                                                                                  'asignan '
                                                                                                  'personas '
                                                                                                  'automáticamente.',
 'Recursos locales': 'Recursos locales',
 'Agregar recurso': 'Agregar recurso',
 'Quitar recurso': 'Quitar recurso',
 'Sesión': 'Sesión',
 'Recursos asignados': 'Recursos asignados',
 'Asignaciones de recursos por sesión': 'Asignaciones de recursos por sesión',
 'Elegir recursos de la sesión': 'Elegir recursos de la sesión',
 'Los grupos de estudiantes y las personas se asignan por separado. No se infieren matrículas ni pertenencias entre ellos.': 'Los '
                                                                                                                             'grupos '
                                                                                                                             'de '
                                                                                                                             'estudiantes '
                                                                                                                             'y '
                                                                                                                             'las '
                                                                                                                             'personas '
                                                                                                                             'se '
                                                                                                                             'asignan '
                                                                                                                             'por '
                                                                                                                             'separado. '
                                                                                                                             'No '
                                                                                                                             'se '
                                                                                                                             'infieren '
                                                                                                                             'matrículas '
                                                                                                                             'ni '
                                                                                                                             'pertenencias '
                                                                                                                             'entre '
                                                                                                                             'ellos.',
 'Sin disponibilidad declarada': 'Sin disponibilidad declarada',
 'Sin recursos asignados': 'Sin recursos asignados',
 '¿Quitar {name} y sus asignaciones de todas las sesiones? Cancelar conserva todo.': '¿Quitar {name} y sus '
                                                                                     'asignaciones de todas '
                                                                                     'las sesiones? Cancelar '
                                                                                     'conserva todo.',
 'Asignar varios recursos a esta sesión': 'Asignar varios recursos a esta sesión',
 'Sin selección no se aplica esta restricción. Cada recurso seleccionado queda ocupado durante toda la sesión.': 'Sin '
                                                                                                                 'selección '
                                                                                                                 'no '
                                                                                                                 'se '
                                                                                                                 'aplica '
                                                                                                                 'esta '
                                                                                                                 'restricción. '
                                                                                                                 'Cada '
                                                                                                                 'recurso '
                                                                                                                 'seleccionado '
                                                                                                                 'queda '
                                                                                                                 'ocupado '
                                                                                                                 'durante '
                                                                                                                 'toda '
                                                                                                                 'la '
                                                                                                                 'sesión.',
 'Activo': 'Activo',
 'Desactivado: datos conservados, sin restricciones': 'Desactivado: datos conservados, sin restricciones',
 '{name}: {state}. {count} recursos con sesiones asignadas.': '{name}: {state}. {count} recursos con '
                                                              'sesiones asignadas.',
 'Recursos por revisar': 'Recursos por revisar',
 'Este cambio elimina {count} sesiones con relaciones de recursos guardadas. Se quitarán esas relaciones, pero se conservarán los recursos. ¿Continuar?': 'Este '
                                                                                                                                                          'cambio '
                                                                                                                                                          'elimina '
                                                                                                                                                          '{count} '
                                                                                                                                                          'sesiones '
                                                                                                                                                          'con '
                                                                                                                                                          'relaciones '
                                                                                                                                                          'de '
                                                                                                                                                          'recursos '
                                                                                                                                                          'guardadas. '
                                                                                                                                                          'Se '
                                                                                                                                                          'quitarán '
                                                                                                                                                          'esas '
                                                                                                                                                          'relaciones, '
                                                                                                                                                          'pero '
                                                                                                                                                          'se '
                                                                                                                                                          'conservarán '
                                                                                                                                                          'los '
                                                                                                                                                          'recursos. '
                                                                                                                                                          '¿Continuar?',
 'Los cambios entran en conflicto con el horario. Se retirará el resultado y se desfijarán sus sesiones para regenerarlo. ¿Aplicar cambios?': 'Los '
                                                                                                                                              'cambios '
                                                                                                                                              'entran '
                                                                                                                                              'en '
                                                                                                                                              'conflicto '
                                                                                                                                              'con '
                                                                                                                                              'el '
                                                                                                                                              'horario. '
                                                                                                                                              'Se '
                                                                                                                                              'retirará '
                                                                                                                                              'el '
                                                                                                                                              'resultado '
                                                                                                                                              'y '
                                                                                                                                              'se '
                                                                                                                                              'desfijarán '
                                                                                                                                              'sus '
                                                                                                                                              'sesiones '
                                                                                                                                              'para '
                                                                                                                                              'regenerarlo. '
                                                                                                                                              '¿Aplicar '
                                                                                                                                              'cambios?',
 'Parámetros actualizados. Genere un nuevo horario; los recursos registrados se conservan.': 'Parámetros '
                                                                                             'actualizados. '
                                                                                             'Genere un '
                                                                                             'nuevo horario; '
                                                                                             'los recursos '
                                                                                             'registrados se '
                                                                                             'conservan.',
 'Desactivar herramientas oculta sus controles y conserva sus datos. Desactivar recursos retira esas restricciones después de confirmar y regenerar. Las reglas básicas siguen activas.': 'Desactivar '
                                                                                                                                                                                          'herramientas '
                                                                                                                                                                                          'oculta '
                                                                                                                                                                                          'sus '
                                                                                                                                                                                          'controles '
                                                                                                                                                                                          'y '
                                                                                                                                                                                          'conserva '
                                                                                                                                                                                          'sus '
                                                                                                                                                                                          'datos. '
                                                                                                                                                                                          'Desactivar '
                                                                                                                                                                                          'recursos '
                                                                                                                                                                                          'retira '
                                                                                                                                                                                          'esas '
                                                                                                                                                                                          'restricciones '
                                                                                                                                                                                          'después '
                                                                                                                                                                                          'de '
                                                                                                                                                                                          'confirmar '
                                                                                                                                                                                          'y '
                                                                                                                                                                                          'regenerar. '
                                                                                                                                                                                          'Las '
                                                                                                                                                                                          'reglas '
                                                                                                                                                                                          'básicas '
                                                                                                                                                                                          'siguen '
                                                                                                                                                                                          'activas.',
 'Cambiar parámetros de recursos': 'Cambiar parámetros de recursos',
 'Al desactivar un parámetro, sus recursos dejan de limitar nuevos horarios. Los registros se conservan. Cambiar estos parámetros retira el resultado actual y desfija sus sesiones; deberá regenerarlo. ¿Continuar?': 'Al '
                                                                                                                                                                                                                       'desactivar '
                                                                                                                                                                                                                       'un '
                                                                                                                                                                                                                       'parámetro, '
                                                                                                                                                                                                                       'sus '
                                                                                                                                                                                                                       'recursos '
                                                                                                                                                                                                                       'dejan '
                                                                                                                                                                                                                       'de '
                                                                                                                                                                                                                       'limitar '
                                                                                                                                                                                                                       'nuevos '
                                                                                                                                                                                                                       'horarios. '
                                                                                                                                                                                                                       'Los '
                                                                                                                                                                                                                       'registros '
                                                                                                                                                                                                                       'se '
                                                                                                                                                                                                                       'conservan. '
                                                                                                                                                                                                                       'Cambiar '
                                                                                                                                                                                                                       'estos '
                                                                                                                                                                                                                       'parámetros '
                                                                                                                                                                                                                       'retira '
                                                                                                                                                                                                                       'el '
                                                                                                                                                                                                                       'resultado '
                                                                                                                                                                                                                       'actual '
                                                                                                                                                                                                                       'y '
                                                                                                                                                                                                                       'desfija '
                                                                                                                                                                                                                       'sus '
                                                                                                                                                                                                                       'sesiones; '
                                                                                                                                                                                                                       'deberá '
                                                                                                                                                                                                                       'regenerarlo. '
                                                                                                                                                                                                                       '¿Continuar?',
 'Datos de recursos por corregir: {details}': 'Datos de recursos por corregir: {details}',
 'Docente {resource}: las sesiones {session} y {other} se solapan.': 'Docente {resource}: las sesiones '
                                                                     '{session} y {other} se solapan.',
 'Grupo de estudiantes {resource}: las sesiones {session} y {other} se solapan.': 'Grupo de estudiantes '
                                                                                  '{resource}: las sesiones '
                                                                                  '{session} y {other} se '
                                                                                  'solapan.',
 'Estudiante {resource}: las sesiones {session} y {other} se solapan.': 'Estudiante {resource}: las sesiones '
                                                                        '{session} y {other} se solapan.',
 'Recurso {resource}: la sesión {session} queda fuera de su disponibilidad declarada.': 'Recurso {resource}: '
                                                                                        'la sesión {session} '
                                                                                        'queda fuera de su '
                                                                                        'disponibilidad '
                                                                                        'declarada.'})

MESSAGES.update({'Calendar requires unique supported teaching days': 'Selecciona al menos un día lectivo válido, sin duplicados.', 'Calendar hours must be increasing integer minutes in 00:00–24:00': 'La apertura debe ser anterior al cierre, entre 00:00 y 24:00.', 'Calendar breaks must be intervals': 'Los descansos deben tener inicio y fin.', 'Breaks must be within opening hours': 'Los descansos deben estar dentro de la jornada y tener inicio anterior al fin.', 'Calendar breaks must not overlap': 'Los descansos no pueden solaparse.', 'Calendar must leave teaching time available': 'Los descansos deben dejar tiempo lectivo disponible.', 'Resource availability references a removed teaching day; edit it explicitly first': 'Hay disponibilidad de recursos en un día eliminado; edítala explícitamente primero.', 'La duración no cabe en el horario permitido sin cruzar los descansos.': 'La duración no cabe en el horario permitido sin cruzar los descansos.'})
MESSAGES.update({'Deshacer': 'Deshacer', 'Rehacer': 'Rehacer', 'Deshacer y rehacer': 'Deshacer y rehacer', 'Revertir cambios locales de esta sesión. Máximo 50 cambios o 16 MiB; importar o restaurar reinicia el historial.': 'Revertir cambios locales de esta sesión. Máximo 50 cambios o 16 MiB; importar o restaurar reinicia el historial.', 'Deshacer el último cambio (Ctrl+Z). Historial de esta sesión: máximo 50 cambios o 16 MiB.': 'Deshacer el último cambio (Ctrl+Z). Historial de esta sesión: máximo 50 cambios o 16 MiB.', 'Rehacer el último cambio (Ctrl+Shift+Z).': 'Rehacer el último cambio (Ctrl+Shift+Z).', 'Cambio no aplicado': 'Cambio no aplicado', 'Se conservan los datos, el horario y el historial. {detail}': 'Se conservan los datos, el horario y el historial. {detail}', 'La sesión cambió desde la revisión. Vuelva a revisar el cambio.': 'La sesión cambió desde la revisión. Vuelva a revisar el cambio.', 'Cambio guardado.': 'Cambio guardado.', 'Cambio deshecho.': 'Cambio deshecho.', 'Cambio rehecho.': 'Cambio rehecho.', 'Historial reiniciado al importar o restaurar una sesión.': 'Historial reiniciado al importar o restaurar una sesión.', 'El historial se reinició por cambios fuera del historial.': 'El historial se reinició por cambios fuera del historial.', 'No hay cambios disponibles en el historial.': 'No hay cambios disponibles en el historial.', 'El cambio supera el límite de memoria del historial. No se aplicó.': 'El cambio supera el límite de memoria del historial. No se aplicó.', 'Los códigos de curso deben ser únicos y no estar vacíos.': 'Los códigos de curso deben ser únicos y no estar vacíos.', 'Datos de curso no válidos: {code}.': 'Datos de curso no válidos: {code}.', 'Las sesiones fijadas deben conservar una asignación válida.': 'Las sesiones fijadas deben conservar una asignación válida.', 'Las excepciones LAB deben corresponder a sesiones asignadas.': 'Las excepciones LAB deben corresponder a sesiones asignadas.', 'El cambio no es válido. Revise las asignaciones y las restricciones.': 'El cambio no es válido. Revise las asignaciones y las restricciones.', 'Desfije las sesiones afectadas antes de editar los cursos.': 'Desfije las sesiones afectadas antes de editar los cursos.', '¿Eliminar todos los cursos de la lista?': '¿Eliminar todos los cursos de la lista?'})

MESSAGES.update({'Cambiar calendario': 'Cambiar calendario'})

MESSAGES.update({'Domingo': 'Domingo'})
MESSAGES['Se conservará el archivo original y se restablecerán las herramientas opcionales. Los parámetros de recursos de la sesión, horarios, fijaciones y escenarios no cambian. ¿Continuar?'] = 'Se conservará el archivo original y se restablecerán las herramientas opcionales. Los parámetros de recursos de la sesión, horarios, fijaciones y escenarios no cambian. ¿Continuar?'

MESSAGES["Curso"] = 'Curso'
MESSAGES.update({'Deshacer': 'Deshacer',
 'Rehacer': 'Rehacer',
 'Deshacer y rehacer': 'Deshacer y rehacer',
 'Revertir cambios locales de esta sesión. Máximo 50 cambios o 16 MiB; importar o restaurar reinicia el historial.': 'Revertir '
                                                                                                                     'cambios '
                                                                                                                     'locales '
                                                                                                                     'de '
                                                                                                                     'esta '
                                                                                                                     'sesión. '
                                                                                                                     'Máximo '
                                                                                                                     '50 '
                                                                                                                     'cambios '
                                                                                                                     'o '
                                                                                                                     '16 '
                                                                                                                     'MiB; '
                                                                                                                     'importar '
                                                                                                                     'o '
                                                                                                                     'restaurar '
                                                                                                                     'reinicia '
                                                                                                                     'el '
                                                                                                                     'historial.',
 'Deshacer el último cambio (Ctrl+Z). Historial de esta sesión: máximo 50 cambios o 16 MiB.': 'Deshacer el '
                                                                                              'último cambio '
                                                                                              '(Ctrl+Z). '
                                                                                              'Historial de '
                                                                                              'esta sesión: '
                                                                                              'máximo 50 '
                                                                                              'cambios o 16 '
                                                                                              'MiB.',
 'Rehacer el último cambio (Ctrl+Shift+Z).': 'Rehacer el último cambio (Ctrl+Shift+Z).',
 'Cambio no aplicado': 'Cambio no aplicado',
 'Se conservan los datos, el horario y el historial. {detail}': 'Se conservan los datos, el horario y el '
                                                                'historial. {detail}',
 'La sesión cambió desde la revisión. Vuelva a revisar el cambio.': 'La sesión cambió desde la revisión. '
                                                                    'Vuelva a revisar el cambio.',
 'Cambio guardado.': 'Cambio guardado.',
 'Cambio deshecho.': 'Cambio deshecho.',
 'Cambio rehecho.': 'Cambio rehecho.',
 'Historial reiniciado al importar o restaurar una sesión.': 'Historial reiniciado al importar o restaurar '
                                                             'una sesión.',
 'El historial se reinició por cambios fuera del historial.': 'El historial se reinició por cambios fuera '
                                                              'del historial.',
 'No hay cambios disponibles en el historial.': 'No hay cambios disponibles en el historial.',
 'El cambio supera el límite de memoria del historial. No se aplicó.': 'El cambio supera el límite de '
                                                                       'memoria del historial. No se aplicó.',
 'Los códigos de curso deben ser únicos y no estar vacíos.': 'Los códigos de curso deben ser únicos y no '
                                                             'estar vacíos.',
 'Datos de curso no válidos: {code}.': 'Datos de curso no válidos: {code}.',
 'Las sesiones fijadas deben conservar una asignación válida.': 'Las sesiones fijadas deben conservar una '
                                                                'asignación válida.',
 'Las excepciones LAB deben corresponder a sesiones asignadas.': 'Las excepciones LAB deben corresponder a '
                                                                 'sesiones asignadas.',
 'El cambio no es válido. Revise las asignaciones y las restricciones.': 'El cambio no es válido. Revise las '
                                                                         'asignaciones y las restricciones.',
 'Desfije las sesiones afectadas antes de editar los cursos.': 'Desfije las sesiones afectadas antes de '
                                                               'editar los cursos.',
 '¿Eliminar todos los cursos de la lista?': '¿Eliminar todos los cursos de la lista?'})

MESSAGES.update({'Edición de cursos en lote': 'Edición de cursos en lote',
 'Cambiar campos seleccionados con revisión previa. Requiere activar Deshacer y rehacer.': 'Cambiar campos '
                                                                                           'seleccionados '
                                                                                           'con revisión '
                                                                                           'previa. Requiere '
                                                                                           'activar Deshacer '
                                                                                           'y rehacer.',
 'Editar en lote': 'Editar en lote',
 'Editar cursos en lote': 'Editar cursos en lote',
 'Seleccione cursos y active Deshacer y rehacer en Configuración.': 'Seleccione cursos y active Deshacer y '
                                                                    'rehacer en Configuración.',
 'Seleccione al menos un curso; no repita identificadores.': 'Seleccione al menos un curso; no repita '
                                                             'identificadores.',
 'Marque los campos que desea cambiar. Los códigos no se pueden editar en lote.': 'Marque los campos que '
                                                                                  'desea cambiar. Los '
                                                                                  'códigos no se pueden '
                                                                                  'editar en lote.',
 'El tamaño debe ser un entero entre 0 y 100000.': 'El tamaño debe ser un entero entre 0 y 100000.',
 'Seleccione un tipo de aula válido.': 'Seleccione un tipo de aula válido.',
 'Seleccione un día válido o borre la preferencia explícitamente.': 'Seleccione un día válido o borre la '
                                                                    'preferencia explícitamente.',
 'La selección cambió. Cierre y vuelva a seleccionar los cursos.': 'La selección cambió. Cierre y vuelva a '
                                                                   'seleccionar los cursos.',
 'Los valores elegidos no cambian ningún curso.': 'Los valores elegidos no cambian ningún curso.',
 'Active Deshacer y rehacer en Configuración antes de editar en lote.': 'Active Deshacer y rehacer en '
                                                                        'Configuración antes de editar en '
                                                                        'lote.',
 'La sesión o selección cambió desde la revisión. Vuelva a revisar el lote.': 'La sesión o selección cambió '
                                                                              'desde la revisión. Vuelva a '
                                                                              'revisar el lote.',
 'Tipo de aula': 'Tipo de aula',
 'Tamaño': 'Tamaño',
 'Día preferido': 'Día preferido',
 'Cursos seleccionados: {count}. Identificadores: {codes}': 'Cursos seleccionados: {count}. Identificadores: '
                                                            '{codes}',
 'Marque solo los campos que desea cambiar. Sin marcar conserva el valor de cada curso.': 'Marque solo los '
                                                                                          'campos que desea '
                                                                                          'cambiar. Sin '
                                                                                          'marcar conserva '
                                                                                          'el valor de cada '
                                                                                          'curso.',
 'Borrar preferencia': 'Borrar preferencia',
 'Valores mezclados': 'Valores mezclados',
 'Conservar valor': 'Conservar valor',
 'Vista previa de cambios por código': 'Vista previa de cambios por código',
 'Campo': 'Campo',
 'Antes': 'Antes',
 'Después': 'Después',
 'Revise el lote antes de aplicarlo.': 'Revise el lote antes de aplicarlo.',
 'Impacto en horario y restricciones': 'Impacto en horario y restricciones',
 'Error de edición en lote': 'Error de edición en lote',
 'Revisar cambios': 'Revisar cambios',
 'Aplicar lote': 'Aplicar lote',
 'Sin preferencia': 'Sin preferencia',
 'Se dejarán pendientes {pending} asignaciones no fijadas. Se conservan {pins} sesiones fijadas y todas las restricciones. Las preferencias por grupo se conservan y pueden prevalecer sobre el día del curso.': 'Se '
                                                                                                                                                                                                                 'dejarán '
                                                                                                                                                                                                                 'pendientes '
                                                                                                                                                                                                                 '{pending} '
                                                                                                                                                                                                                 'asignaciones '
                                                                                                                                                                                                                 'no '
                                                                                                                                                                                                                 'fijadas. '
                                                                                                                                                                                                                 'Se '
                                                                                                                                                                                                                 'conservan '
                                                                                                                                                                                                                 '{pins} '
                                                                                                                                                                                                                 'sesiones '
                                                                                                                                                                                                                 'fijadas '
                                                                                                                                                                                                                 'y '
                                                                                                                                                                                                                 'todas '
                                                                                                                                                                                                                 'las '
                                                                                                                                                                                                                 'restricciones. '
                                                                                                                                                                                                                 'Las '
                                                                                                                                                                                                                 'preferencias '
                                                                                                                                                                                                                 'por '
                                                                                                                                                                                                                 'grupo '
                                                                                                                                                                                                                 'se '
                                                                                                                                                                                                                 'conservan '
                                                                                                                                                                                                                 'y '
                                                                                                                                                                                                                 'pueden '
                                                                                                                                                                                                                 'prevalecer '
                                                                                                                                                                                                                 'sobre '
                                                                                                                                                                                                                 'el '
                                                                                                                                                                                                                 'día '
                                                                                                                                                                                                                 'del '
                                                                                                                                                                                                                 'curso.',
 'La herramienta no está disponible. Cierre el diálogo y revise Configuración.': 'La herramienta no está '
                                                                                 'disponible. Cierre el '
                                                                                 'diálogo y revise '
                                                                                 'Configuración.',
 'No se pudo guardar el lote. Se conservan todos los datos. {detail}': 'No se pudo guardar el lote. Se '
                                                                       'conservan todos los datos. {detail}',
 'Lote guardado. Puede deshacerlo en una sola operación.': 'Lote guardado. Puede deshacerlo en una sola '
                                                           'operación.'})

MESSAGES['Cursos seleccionados'] = 'Cursos seleccionados'

MESSAGES['El historial se reinició por cambios realizados con Deshacer y rehacer desactivado.'] = 'El historial se reinició por cambios realizados con Deshacer y rehacer desactivado.'

MESSAGES['No se pudo restaurar la vista. Los datos se conservaron; reintente recuperar la sesión. {detail}'] = 'No se pudo restaurar la vista. Los datos se conservaron; reintente recuperar la sesión. {detail}'

MESSAGES['El cambio se guardó, pero no se pudo actualizar la vista. Reintente recuperar la sesión.'] = 'El cambio se guardó, pero no se pudo actualizar la vista. Reintente recuperar la sesión.'

MESSAGES['No se pudo obtener acceso exclusivo a la sesión. Cierre la otra ventana de SORTH y vuelva a intentarlo. Si el problema continúa, revise los permisos de la carpeta de datos o solicite ayuda. No elimine archivos de bloqueo mientras SORTH esté abierto.'] = 'No se pudo obtener acceso exclusivo a la sesión. Cierre la otra ventana de SORTH y vuelva a intentarlo. Si el problema continúa, revise los permisos de la carpeta de datos o solicite ayuda. No elimine archivos de bloqueo mientras SORTH esté abierto.'

# Offline MCP add-on preparation and client guidance.
MESSAGES.update({
    'Preparar complemento MCP': 'Preparar complemento MCP',
    'Cancelar preparación MCP': 'Cancelar preparación MCP',
    'Conectar un cliente MCP': 'Conectar un cliente MCP',
    'Preparar copia el complemento incluido y lo verifica, tras tu confirmación. Se aplica inmediatamente; Cancelar configuración conserva el complemento preparado y no guarda cambios de permiso.': 'Preparar copia el complemento incluido y lo verifica, tras tu confirmación. Se aplica inmediatamente; Cancelar configuración conserva el complemento preparado y no guarda cambios de permiso.',
    'Complemento MCP preparado y verificado. El permiso no ha cambiado. Puedes conectar un cliente y activar MCP por separado con Guardar.': 'Complemento MCP preparado y verificado. El permiso no ha cambiado. Puedes conectar un cliente y activar MCP por separado con Guardar.',
    'El complemento MCP no está incluido en esta compilación. Usa una distribución que lo incluya o consulta la ruta de desarrollo en MCP_OPTIONAL.md.': 'El complemento MCP no está incluido en esta compilación. Usa una distribución que lo incluya o consulta la ruta de desarrollo en MCP_OPTIONAL.md.',
    'El complemento MCP aún no está preparado. Pulsa Preparar complemento MCP y revisa la confirmación.': 'El complemento MCP aún no está preparado. Pulsa Preparar complemento MCP y revisa la confirmación.',
    'Este complemento MCP requiere Windows de 64 bits. Consulta MCP_OPTIONAL.md para desarrollo desde código fuente.': 'Este complemento MCP requiere Windows de 64 bits. Consulta MCP_OPTIONAL.md para desarrollo desde código fuente.',
    'No se pudo validar el paquete MCP. Obtén una distribución verificada de SORTH; no se instalará este paquete.': 'No se pudo validar el paquete MCP. Obtén una distribución verificada de SORTH; no se instalará este paquete.',
    'La integridad del complemento MCP no coincide. No se ejecutará. Obtén una distribución verificada de SORTH o consulta soporte antes de reparar archivos.': 'La integridad del complemento MCP no coincide. No se ejecutará. Obtén una distribución verificada de SORTH o consulta soporte antes de reparar archivos.',
    'El complemento MCP no corresponde a esta versión de SORTH. Prepara el complemento incluido en esta compilación.': 'El complemento MCP no corresponde a esta versión de SORTH. Prepara el complemento incluido en esta compilación.',
    'Otra preparación MCP está en curso. Espera a que termine y vuelve a intentarlo.': 'Otra preparación MCP está en curso. Espera a que termine y vuelve a intentarlo.',
    'No se pudo preparar el complemento MCP. Revisa el espacio disponible y los permisos de la carpeta de datos e inténtalo de nuevo.': 'No se pudo preparar el complemento MCP. Revisa el espacio disponible y los permisos de la carpeta de datos e inténtalo de nuevo.',
    'No se pudieron retirar todos los archivos temporales de la preparación MCP. El permiso no ha cambiado; consulta soporte antes de limpiar archivos manualmente.': 'No se pudieron retirar todos los archivos temporales de la preparación MCP. El permiso no ha cambiado; consulta soporte antes de limpiar archivos manualmente.',
    'El complemento MCP no superó su verificación. No está listo; revisa MCP_OPTIONAL.md antes de reintentar.': 'El complemento MCP no superó su verificación. No está listo; revisa MCP_OPTIONAL.md antes de reintentar.',
    'Operación MCP cancelada. El permiso no ha cambiado.': 'Operación MCP cancelada. El permiso no ha cambiado.',
    'Se copiará el complemento MCP {version} incluido con SORTH a:\n{path}\n\nSe comprobará su integridad y se ejecutará una prueba local sin iniciar el servidor. No usa red ni pip y no instala en Python del sistema. Se aplica inmediatamente; Cancelar configuración no elimina el complemento. El permiso MCP y los clientes no cambian. ¿Preparar ahora?': 'Se copiará el complemento MCP {version} incluido con SORTH a:\n{path}\n\nSe comprobará su integridad y se ejecutará una prueba local sin iniciar el servidor. No usa red ni pip y no instala en Python del sistema. Se aplica inmediatamente; Cancelar configuración no elimina el complemento. El permiso MCP y los clientes no cambian. ¿Preparar ahora?',
    'Comprobando integridad del paquete MCP…': 'Comprobando integridad del paquete MCP…',
    'Preparando archivos del complemento MCP…': 'Preparando archivos del complemento MCP…',
    'Verificando el complemento MCP preparado…': 'Verificando el complemento MCP preparado…',
    'Finalizando la preparación MCP…': 'Finalizando la preparación MCP…',
    'Cancelando la preparación MCP de forma segura…': 'Cancelando la preparación MCP de forma segura…',
    'Terminando la operación MCP de forma segura antes de cerrar…': 'Terminando la operación MCP de forma segura antes de cerrar…',
    'Elige tu cliente. Esta guía no modifica su configuración. Revisa privacidad, permisos y posibles cargos del proveedor antes de conectar datos. No se han probado estos hosts comerciales.': 'Elige tu cliente. Esta guía no modifica su configuración. Revisa privacidad, permisos y posibles cargos del proveedor antes de conectar datos. No se han probado estos hosts comerciales.',
    'Cliente MCP': 'Cliente MCP',
    'Configuración del cliente para copiar': 'Configuración del cliente para copiar',
    'Copiar configuración': 'Copiar configuración',
    'Añade esta entrada a mcp.servers en opencode.jsonc sin reemplazar otras entradas. Empieza desconectada (disabled: true). Después de guardar el permiso MCP en SORTH, revisa las herramientas y conecta con /mcps. Usa protocol: legacy.': 'Añade esta entrada a mcp.servers en opencode.jsonc sin reemplazar otras entradas. Empieza desconectada (disabled: true). Después de guardar el permiso MCP en SORTH, revisa las herramientas y conecta con /mcps. Usa protocol: legacy.',
    'Integra esta entrada en mcpServers de la configuración local de Claude Desktop sin reemplazar otros servidores. Al reiniciar el cliente puede iniciar el proceso; primero guarda el permiso MCP en SORTH. Claude admite extensiones MCPB, pero SORTH no genera un paquete MCPB en este flujo.': 'Integra esta entrada en mcpServers de la configuración local de Claude Desktop sin reemplazar otros servidores. Al reiniciar el cliente puede iniciar el proceso; primero guarda el permiso MCP en SORTH. Claude admite extensiones MCPB, pero SORTH no genera un paquete MCPB en este flujo.',
    'ChatGPT necesita una conexión HTTPS o Secure MCP Tunnel autorizada por separado; esta ruta local no es una URL. El túnel requiere sus propios permisos y credenciales. SORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT. Consulta las instrucciones oficiales y las reglas de tu organización.': 'ChatGPT necesita una conexión HTTPS o Secure MCP Tunnel autorizada por separado; esta ruta local no es una URL. El túnel requiere sus propios permisos y credenciales. SORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT. Consulta las instrucciones oficiales y las reglas de tu organización.',
    'Prepara y verifica el complemento para obtener su ruta exacta. En desarrollo desde código fuente, consulta MCP_OPTIONAL.md: se usa un entorno Python separado con su directorio de trabajo.': 'Prepara y verifica el complemento para obtener su ruta exacta. En desarrollo desde código fuente, consulta MCP_OPTIONAL.md: se usa un entorno Python separado con su directorio de trabajo.',
    '<a href="{url}">Instrucciones oficiales del cliente</a>': '<a href="{url}">Instrucciones oficiales del cliente</a>',
    '<a href="{url}">Guía oficial de Secure MCP Tunnel</a>': '<a href="{url}">Guía oficial de Secure MCP Tunnel</a>',
    'Configuración copiada. Revisa y combínala con la configuración existente de tu cliente.': 'Configuración copiada. Revisa y combínala con la configuración existente de tu cliente.',
})
MESSAGES['Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. La verificación solo comprueba este entorno; el EXE estándar no incluye MCP. Consulta MCP_OPTIONAL.md para un entorno Python separado.'] = 'Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. Preparar no activa MCP ni configura clientes o modelos. Consulta MCP_OPTIONAL.md para más información.'
MESSAGES['<a href="{url}">Configuración local de MCP</a>'] = '<a href="{url}">Configuración local de MCP</a>'

# Guided MCP setup: preparation, saved permission and client connection stay separate.
MESSAGES.update({
    '1. Preparar MCP': '1. Preparar MCP',
    'Estado del complemento MCP': 'Estado del complemento MCP',
    'Preparar requiere confirmación y conserva el complemento aunque canceles Configuración. No concede permiso ni conecta clientes.': 'Preparar requiere confirmación y conserva el complemento aunque canceles Configuración. No concede permiso ni conecta clientes.',
    '2. Guardar el permiso local': '2. Guardar el permiso local',
    '3. Configurar tu cliente': '3. Configurar tu cliente',
    'Ver guía de conexión': 'Ver guía de conexión',
    'Abre instrucciones para OpenCode, Claude Desktop o ChatGPT. La conexión y sus permisos se gestionan en el cliente.': 'Abre instrucciones para OpenCode, Claude Desktop o ChatGPT. La conexión y sus permisos se gestionan en el cliente.',
    'Otras funciones opcionales': 'Otras funciones opcionales',
    'Cambio pendiente: pulsa Guardar para permitir MCP. Cancelar conserva el permiso desactivado.': 'Cambio pendiente: pulsa Guardar para permitir MCP. Cancelar conserva el permiso desactivado.',
    'Cambio pendiente: pulsa Guardar para desactivar MCP. El permiso sigue activo hasta guardar.': 'Cambio pendiente: pulsa Guardar para desactivar MCP. Hasta entonces, el permiso sigue activo. Después se bloquean nuevas solicitudes y se descartan resultados pendientes. Cierra el proceso desde tu cliente; una tarea en curso puede tardar hasta 10 segundos.',
    'Permiso guardado: activado. El cliente inicia el servidor; SORTH no lo inicia al guardar.': 'Permiso guardado: activado. El cliente inicia el servidor; SORTH no lo inicia al guardar.',
    'Permiso guardado: desactivado. Prepara y verifica MCP antes de permitirlo y guardar.': 'Permiso guardado: desactivado. Prepara y verifica MCP antes de permitirlo y guardar.',
    'Cancelar verificación MCP': 'Cancelar verificación MCP',
    'Cancelando la verificación MCP de forma segura…': 'Cancelando la verificación MCP de forma segura…',
    'Guía de conexión MCP': 'Guía de conexión MCP',
    'Sigue los pasos en tu cliente. Esta guía solo muestra instrucciones y no modifica otras apps.': 'Sigue los pasos en tu cliente. Esta guía solo muestra instrucciones y no modifica otras apps.',
    'Hay un cambio de permiso sin guardar. Cierra esta guía, revisa la casilla y pulsa Guardar antes de conectar.': 'Hay un cambio de permiso sin guardar. Cierra esta guía, revisa la casilla y pulsa Guardar antes de conectar.',
    'Permiso local guardado: activado. Aún debes configurar y autorizar la conexión en el cliente.': 'Permiso local guardado: activado. Aún debes configurar y autorizar la conexión en el cliente.',
    'Antes de conectar, marca Permitir servidor MCP local y pulsa Guardar en Configuración.': 'Antes de conectar, marca Permitir servidor MCP local y pulsa Guardar en Configuración.',
    'Antes de compartir datos, revisa la privacidad, los permisos y los posibles cargos del proveedor. Estas conexiones comerciales aún no se han probado.': 'Antes de compartir datos, revisa la privacidad, los permisos y los posibles cargos del proveedor. Estas conexiones comerciales aún no se han probado.',
    '1. Copia esta configuración y combina sorth-preview en mcp.servers de opencode.jsonc. Conserva las otras entradas.\n2. Empieza desconectada (disabled: true) y usa protocol: legacy.\n3. Tras guardar el permiso en SORTH, revisa las herramientas y conecta con /mcps.': '1. Copia esta configuración y combina sorth-preview en mcp.servers de opencode.jsonc. Conserva las otras entradas.\n2. Empieza desconectada (disabled: true) y usa protocol: legacy.\n3. Tras guardar el permiso en SORTH, revisa las herramientas y conecta con /mcps.',
    '1. Copia esta configuración y combina sorth-preview en mcpServers de la configuración local de Claude Desktop. Conserva los otros servidores.\n2. Guarda primero el permiso MCP en SORTH. Reiniciar Claude puede iniciar el servidor.\n3. Revisa y autoriza las herramientas en Claude. Este flujo no genera extensiones MCPB.': '1. Copia esta configuración y combina sorth-preview en mcpServers de la configuración local de Claude Desktop. Conserva los otros servidores.\n2. Guarda primero el permiso MCP en SORTH. Reiniciar Claude puede iniciar el servidor.\n3. Revisa y autoriza las herramientas en Claude. Este flujo no genera extensiones MCPB.',
    'ChatGPT no acepta esta ruta local como conexión. Requiere HTTPS o Secure MCP Tunnel con autorización independiente.\n\n1. Consulta las instrucciones oficiales y las reglas de tu organización.\n2. Configura y autoriza esa conexión por separado, incluidos sus permisos y credenciales.\n\nSORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT.': 'ChatGPT no acepta esta ruta local como conexión. Requiere HTTPS o Secure MCP Tunnel con autorización independiente.\n\n1. Consulta las instrucciones oficiales y las reglas de tu organización.\n2. Configura y autoriza esa conexión por separado, incluidos sus permisos y credenciales.\n\nSORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT.',
    'Permitir que un cliente inicie el servidor stdio. No inicia procesos, conecta modelos ni instala componentes.': 'Permite que tu cliente inicie el servidor local. Guardar no lo inicia ni conecta modelos.',
    'Disponibilidad MCP sin verificar en este entorno.': 'Primero verifica si MCP está disponible. Si falta el complemento, podrás prepararlo por separado.',
    'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.': 'MCP verificado y disponible. No necesita prepararse de nuevo. Revisa el permiso local en el paso 2.',
    'Complemento MCP preparado y verificado. El permiso no ha cambiado. Puedes conectar un cliente y activar MCP por separado con Guardar.': 'Complemento MCP preparado y verificado. El permiso no ha cambiado. Continúa con el paso 2.',
    'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.': 'Falta el componente MCP de Python en este entorno. Consulta MCP_OPTIONAL.md para prepararlo en un entorno separado. No se ha instalado nada.',
    'MCP ya está disponible. Usa Verificar disponibilidad local de MCP para comprobarlo de nuevo.': 'MCP ya está disponible. Usa Verificar disponibilidad local de MCP para comprobarlo de nuevo.',
    'Permiso guardado: desactivado. MCP está listo; marca la casilla y pulsa Guardar si deseas permitirlo.': 'Permiso guardado: desactivado. MCP está listo; marca la casilla y pulsa Guardar si deseas permitirlo.',
})

MESSAGES.update({
    'Permiso local guardado: activado.': 'Permiso local guardado: activado.',
    'Permiso local guardado: desactivado.': 'Permiso local guardado: desactivado.',
    'Espera a que termine la verificación MCP antes de guardar el permiso.': 'Espera a que termine la verificación MCP antes de guardar el permiso.',
})

# Import operation identity stays separate from accepted session data.
MESSAGES.update({
    'Archivo de la sesión: {filename}': 'Archivo de la sesión: {filename}',
    'Archivo en importación:': 'Archivo en importación:',
    'Archivo en importación': 'Archivo en importación',
    'Archivo pendiente de aceptar. La sesión actual se conserva. Lea el estado completo con F6.': 'Archivo pendiente de aceptar. La sesión actual se conserva. Lea el estado completo con F6.',
    'Esperando para leer {filename}… La sesión actual se conserva.': 'Esperando para leer {filename}… La sesión actual se conserva.',
    'Leyendo y validando {filename}… La sesión actual se conserva.': 'Leyendo y validando {filename}… La sesión actual se conserva.',
    'Comprobando que {filename} no cambió… La sesión actual se conserva.': 'Comprobando que {filename} no cambió… La sesión actual se conserva.',
    'Revisando {filename}… La sesión actual se conserva.': 'Revisando {filename}… La sesión actual se conserva.',
    'Guardando {filename}…': 'Guardando {filename}…',
    'El archivo {filename} cambió. Revise la nueva versión validada antes de importar.': 'El archivo {filename} cambió. Revise la nueva versión validada antes de importar.',
    'Importación de {filename} cancelada. La sesión anterior se conserva.': 'Importación de {filename} cancelada. La sesión anterior se conserva.',
    'No se pudo importar {filename}. La sesión anterior se conserva. Vuelva a cargar el archivo para reintentar.': 'No se pudo importar {filename}. La sesión anterior se conserva. Vuelva a cargar el archivo para reintentar.',
})

# Keep the latest export failure readable after dismissing its dialog.
MESSAGES.update({
    'No se pudo exportar a {filename}. El horario se conserva. Revise el destino y vuelva a intentarlo.': 'No se pudo exportar a {filename}. El horario se conserva. Revise el destino y vuelva a intentarlo.',
})
