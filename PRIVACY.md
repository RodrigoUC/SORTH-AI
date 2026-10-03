# Privacidad y datos locales

Este aviso describe el código de SORTH revisado el 3 de octubre de 2026. No es una certificación de seguridad ni una garantía de cumplimiento legal. Antes de usar datos institucionales, confirma las reglas de tu organización.

## Qué guarda y dónde

SORTH procesa en el equipo el Excel elegido por el usuario. La base SQLite local guarda cursos, aulas, capacidades, sugerencias, restricciones, asignaciones, excepciones manuales LAB, sesiones fijadas, calendario del proyecto (días, horas y descansos), ruta del Excel, semilla y fecha de guardado. La ruta puede revelar el nombre del usuario del equipo.

Si utilizas [recursos opcionales](project_root/OPTIONAL_RESOURCES.md), también guarda identificadores y nombres o alias de docentes, grupos de estudiantes y estudiantes individuales, disponibilidad declarada, relaciones explícitas con cada sesión y si sus restricciones están activas. Los grupos son etiquetas: SORTH no deduce qué personas los integran. No necesitas nombres reales, documentos de identidad, edades ni correos para planificar; usa códigos, cantidades y alias mínimos. Los alias y horarios relacionados pueden seguir identificando personas: no equivalen a anonimización.

- Windows: `%LOCALAPPDATA%/SORTH/sorth_session.db`.
- macOS: `~/Library/Application Support/SORTH/sorth_session.db`.
- Linux: `$XDG_DATA_HOME/SORTH/sorth_session.db` si la variable contiene una ruta absoluta; en otro caso, `~/.local/share/SORTH/sorth_session.db`.
- `sorth_projects.db`, en la misma carpeta, conserva nombres e identificadores de proyectos/escenarios, fechas, metadatos de calendario/versiones, ubicación de origen de la sesión recuperada y copias SQLite completas. Incluye los recursos personales, sus relaciones y parámetros, aunque estén desactivados. Las copias de escenario son independientes: editar o borrar datos de la sesión activa no las actualiza.
- Las copias `legacy-session-*.db`, `previous-session-*.db` y `schema-session-*.db` quedan en esa misma carpeta. La migración conserva además la base antigua `data/sorth_session.db` junto al ejecutable o dentro de `project_root`.
- Las herramientas opcionales se guardan aparte en `SORTH/optional-features.json`, bajo la carpeta de configuración que Qt identifica como `QStandardPaths.GenericConfigLocation` (depende del sistema). Contiene versión e interruptores, no el catálogo de personas. La escritura usa `QSaveFile` de forma atómica; recuperar una configuración dañada conserva primero `optional-features.json.preserved-*.bak` junto al original. Si falta el JSON, pueden leerse las antiguas claves `features/` de QSettings, sin borrarlas. Los parámetros efectivos de recursos pertenecen a SQLite; el JSON sólo refleja su presentación.
- Mientras la GUI está abierta, `sorth_session.db.gui.lock` acompaña a la ruta canónica de la base. Qt guarda metadatos para reconocer al proceso/equipo propietario (por ejemplo, PID, aplicación y host; según el sistema, identificadores de máquina/arranque). No es un registro del horario. Normalmente se retira al cerrar; puede quedar tras una caída. No lo borres para forzar otra instancia.
- Idioma y movimiento reducido se guardan por separado mediante Qt QSettings, organización/aplicación `SORTH/SORTH`, claves `interface/language` e `interface/reduced_motion`. Su ubicación depende del sistema operativo.
- Las exportaciones Excel/CSV/PDF quedan en la ruta que elijas. El Excel de entrada no se sustituye al exportar salvo que selecciones tú ese mismo destino; usa nombres distintos.

La sesión, catálogo de escenarios, respaldos, preferencias y exportaciones no tienen cifrado implementado por SORTH. El acceso depende de la cuenta, permisos, disco y copias de seguridad del equipo. Una carpeta sincronizada o unidad de red puede compartir archivos por mecanismos externos a la aplicación.

## Exportaciones e historial

El CSV y la hoja Excel **Asignaciones** conservan siete columnas: Código Curso, Nombre Curso, Grupo, Aula, Día, Hora Inicio y Hora Fin. **Por Aula** usa esos mismos campos con Aula primero; Excel añade vistas de horario por aula. El PDF muestra aula, día, horas, grupo/sesión, nombre del curso, avisos de conflicto/excepción LAB, alcance, filtros y recuentos. No se añaden columnas de docentes/estudiantes ni se exportan automáticamente sus catálogos, relaciones o disponibilidad. Esto no anonimiza nombres de curso, aulas o texto de filtros donde hayas escrito información personal: revisa el archivo antes de compartirlo.

[Deshacer y rehacer](project_root/REVERSIBLE_EDITS.md) conserva en memoria copias de los estados editados, incluidos recursos y calendario, con un máximo de 50 cambios y 16 MiB. El historial no se guarda como tal en disco ni sobrevive al cierre; cada edición, deshacer o rehacer aceptados sí guardan el estado resultante en SQLite. Importar/restaurar/cambiar de proyecto y otros cambios fuera del historial lo reinician. Ocultar la herramienta no borra por sí solo los comandos aún válidos. Esto no elimina escenarios o respaldos anteriores, ni garantiza ausencia de copias del sistema operativo.

## Desactivar no es borrar

Ocultar herramientas de fijación, calendario o escenarios conserva sus datos; las fijaciones y el calendario guardados siguen condicionando el horario. Desactivar Docentes, Grupos de estudiantes o Estudiantes individuales conserva sus registros, disponibilidad y relaciones, pero deja de aplicar sus restricciones. Cambiar estos parámetros retira el resultado actual, sus fijaciones y excepciones LAB para regenerarlo; cuando hay horario o relaciones afectadas, la interfaz pide confirmación. Cancelar conserva el estado anterior. Restaurar una sesión o escenario recupera sus parámetros efectivos.

Recuperar el JSON de herramientas conserva los parámetros de recursos de la sesión válida; no es una función de borrado. Consulta [Configuración opcional](project_root/OPTIONAL_FEATURES.md) y [Proyectos y escenarios](project_root/PROJECT_SCENARIOS.md).

## Red, diagnósticos y actualizaciones

En los flujos de la GUI y herramientas opcionales revisados no se encontraron clientes de red, telemetría, analítica, envío automático de errores ni un actualizador automático. El flujo importar/generar/guardar/exportar funciona localmente, sin cuenta SORTH ni servicio de IA remoto. Esta revisión de código no equivale a una captura de tráfico de todos los binarios y dependencias.

La interfaz presenta errores localmente. No se identificó un archivo de registro permanente de la aplicación en el flujo normal. Herramientas de consola pueden imprimir datos o rutas; la prueba optativa de distribución escribe `smoke-result.json` (incluidos errores), una base, exportaciones y capturas en la carpeta de salida indicada. El sistema operativo, antivirus, terminal o servicios de sincronización pueden conservar sus propios registros, fuera del control de SORTH.

Descargar paquetes, instalar dependencias y abrir enlaces del manual/repositorio utiliza servicios externos. Las actualizaciones se obtienen manualmente del origen verificado; conserva una copia de tus datos antes de cambiar de versión.

## Integración MCP voluntaria

La opción MCP de Configuración guarda únicamente un permiso booleano local,
desactivado de origen, en el mismo archivo de preferencias opcionales. La prueba
de disponibilidad carga componentes locales en un proceso temporal limitado;
no envía información a un proveedor ni instala nada. El servidor lee el permiso
al iniciar y en cada solicitud y descarta resultados pendientes cuando está
desactivado. El cliente conserva el control del cierre del proceso; desactivar
no revoca información que ya haya recibido. El EXE estándar no incluye MCP y
muestra esa limitación.

El [adaptador MCP opcional](project_root/MCP_OPTIONAL.md) sólo se inicia por decisión explícita desde un cliente local stdio; no abre un servidor de red ni se inicia con la GUI. Recibe exclusivamente cursos/aulas suministrados en la solicitud y devuelve configuración normalizada, propuesta y pendientes. No lee la sesión activa ni el catálogo de escenarios, ni permite guardar, aplicar, exportar, elegir rutas o consultar archivos personales. Rechaza campos de docentes, estudiantes, membresías, disponibilidad y calendario personalizado; activar recursos en la GUI no amplía este contrato. No llama modelos ni pide claves. Los diagnósticos de este adaptador son mínimos por stderr y no repiten datos de solicitudes; stdout se reserva para el protocolo.

El host elegido sí conoce los datos que envía y recibe, y puede compartirlos con un proveedor según sus propias reglas. Sus permisos, retención, telemetría y posibles costes son externos a SORTH. Instalar el SDK y dependencias utiliza servicios de distribución externos. Usa ejemplos sintéticos y revisa autorización institucional antes de proporcionar datos reales a un host. Desactivar o cerrar esta integración no borra lo que un host/proveedor ya haya conservado. El núcleo offline sigue funcionando sin la integración ni sus dependencias.

## Control, respaldo y eliminación

Revisa el indicador de guardado antes de cerrar. Para respaldo o recuperación, sigue [Guardado y recuperación](project_root/SESSION_RECOVERY.md). Con todas las instancias cerradas, conserva la carpeta de sesión completa, incluido `sorth_projects.db` y los auxiliares SQLite (`-wal`, `-shm` o `-journal` si existen); no copies sólo la base mientras otra instancia la modifica. Para conservar también herramientas e idioma/movimiento, respalda por separado su configuración. El catálogo crea copias temporales locales de los escenarios al guardarlos/abrirlos, que se limpian normalmente al terminar la operación; una caída puede dejar restos en la carpeta temporal del sistema.

Si decides borrar tus datos, cierra todas las instancias y elimina únicamente los archivos de SORTH que identifiques: base actual y archivos auxiliares, catálogo de escenarios, copias de sesión y base antigua, JSON de herramientas y sus respaldos, entradas originales y exportaciones que ya no necesites. La interfaz no ofrece eliminación de escenarios individuales; quitar una persona de la sesión no la quita de escenarios, respaldos o exportaciones anteriores. Considera también papelera, respaldos y carpetas sincronizadas. Eliminar la base actual dejando la antigua puede provocar una nueva migración al abrir. No borres una base dañada como método de reparación. Las preferencias se cambian desde la interfaz; borrar la base no restablece QSettings ni el JSON opcional. Para retirarlas también, identifica sus ubicaciones por separado, incluidas las antiguas claves `features/` de QSettings si existen. El borrado normal no garantiza eliminación forense ni borra copias que ya compartiste. Desinstalar o quitar la carpeta de la aplicación tampoco elimina necesariamente los datos del usuario.

## Soporte en GitHub

El soporte general es por [Issues](https://github.com/RodrigoUC/SORTH-AI/issues), sin correo de soporte establecido. Los issues y adjuntos son públicos: utiliza el ejemplo sintético y retira nombres, rutas personales, datos institucionales y secretos de cualquier captura o mensaje. No adjuntes bases SQLite ni planillas reales.

GitHub es un servicio externo: al visitarlo o publicar, GitHub procesa datos de cuenta, contenido y uso según su [declaración de privacidad](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). El funcionamiento local de SORTH no hace privados tus reportes en GitHub. Para vulnerabilidades sigue [SECURITY.md](SECURITY.md); no se afirma que el formulario privado esté habilitado hasta verificarlo.

## Base de esta revisión

Se inspeccionaron `gui_app.py`, `main.py`, `src/`, la configuración de empaquetado y los puntos de escritura de datos: `SessionRepository`, `ProjectRepository`, `SchedulingResources`, `FeaturePreferences`, `SettingsDialog`, `EditHistory`, `gui_session_lock.py`, `LanguageManager`, `MotionController`, exportadores y `packaged_smoke.py`. Las rutas y los datos descritos corresponden al inicio normal; pruebas y herramientas técnicas pueden usar rutas explícitas distintas. Revisa este aviso si una versión añade red, registros, nuevas preferencias, almacenamiento o integraciones.
