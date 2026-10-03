# Privacidad y datos locales

Este aviso describe el código de SORTH revisado el 2 de octubre de 2026. No es una certificación de seguridad ni una garantía de cumplimiento legal. Antes de usar datos institucionales, confirma las reglas de tu organización.

## Qué guarda y dónde

SORTH procesa en el equipo el Excel elegido por el usuario. Guarda cursos, aulas, capacidades, sugerencias, restricciones, asignaciones, excepciones manuales LAB, ruta del Excel, semilla y fecha de guardado en una base SQLite local. La ruta puede revelar el nombre del usuario del equipo. No necesita nombres de estudiantes para planificar: usa códigos y cantidades cuando sea posible.

- Windows: `%LOCALAPPDATA%/SORTH/sorth_session.db`.
- macOS: `~/Library/Application Support/SORTH/sorth_session.db`.
- Linux: `$XDG_DATA_HOME/SORTH/sorth_session.db` si la variable contiene una ruta absoluta; en otro caso, `~/.local/share/SORTH/sorth_session.db`.
- Las copias `legacy-session-*.db`, `previous-session-*.db` y `schema-session-*.db` quedan en esa misma carpeta. La migración conserva además la base antigua `data/sorth_session.db` junto al ejecutable o dentro de `project_root`.
- Idioma y movimiento reducido se guardan por separado mediante Qt QSettings, organización/aplicación `SORTH/SORTH`, claves `interface/language` e `interface/reduced_motion`. Su ubicación depende del sistema operativo.
- Las exportaciones Excel/CSV/PDF quedan en la ruta que elijas. El Excel de entrada no se sustituye al exportar salvo que selecciones tú ese mismo destino; usa nombres distintos.

La base SQLite y las exportaciones no tienen cifrado implementado por SORTH. El acceso depende de la cuenta, permisos, disco y copias de seguridad del equipo. Una carpeta sincronizada o unidad de red puede compartir archivos por mecanismos externos a la aplicación.

## Red, diagnósticos y actualizaciones

En el flujo base de la GUI revisado no se encontraron clientes de red, telemetría, analítica, envío automático de errores ni un actualizador automático. El flujo importar/generar/guardar/exportar funciona localmente, sin cuenta SORTH ni servicio de IA remoto. Esta revisión de código no equivale a una captura de tráfico de todos los binarios y dependencias.

La interfaz presenta errores localmente. No se identificó un archivo de registro permanente de la aplicación en el flujo normal. Herramientas de consola pueden imprimir datos o rutas; la prueba optativa de distribución escribe `smoke-result.json` (incluidos errores), una base, exportaciones y capturas en la carpeta de salida indicada. El sistema operativo, antivirus, terminal o servicios de sincronización pueden conservar sus propios registros, fuera del control de SORTH.

Descargar paquetes, instalar dependencias y abrir enlaces del manual/repositorio utiliza servicios externos. Las actualizaciones se obtienen manualmente del origen verificado; conserva una copia de tus datos antes de cambiar de versión.

## Integración MCP voluntaria

El [adaptador MCP opcional](project_root/MCP_OPTIONAL.md) sólo se inicia por decisión explícita desde un cliente local stdio; no abre un servidor de red ni se inicia con la GUI. Recibe exclusivamente cursos/aulas suministrados en la solicitud y devuelve configuración normalizada, propuesta y pendientes. No lee la sesión activa ni permite guardar, aplicar, exportar, elegir rutas o consultar archivos personales. No llama modelos ni pide claves. Los diagnósticos de este adaptador son mínimos por stderr y no repiten datos de solicitudes; stdout se reserva para el protocolo.

El host elegido sí conoce los datos que envía y recibe, y puede compartirlos con un proveedor según sus propias reglas. Sus permisos, retención, telemetría y posibles costes son externos a SORTH. Instalar el SDK y dependencias utiliza servicios de distribución externos. Usa ejemplos sintéticos y revisa autorización institucional antes de proporcionar datos reales a un host. Desactivar o cerrar esta integración no borra lo que un host/proveedor ya haya conservado. El núcleo offline sigue funcionando sin la integración ni sus dependencias.

## Control, respaldo y eliminación

Revisa el indicador de guardado antes de cerrar. Para respaldo o recuperación, sigue [Guardado y recuperación](project_root/SESSION_RECOVERY.md). Con SORTH cerrado, conserva la carpeta de sesión completa, incluidos `-wal` y `-shm` si existen; no copies sólo la base mientras otra instancia la modifica.

Si decides borrar tus datos, cierra todas las instancias y elimina únicamente los archivos de SORTH que identifiques: base actual y archivos auxiliares, copias de sesión y base antigua, entradas originales y exportaciones que ya no necesites. Considera también papelera, respaldos y carpetas sincronizadas. Eliminar la base actual dejando la antigua puede provocar una nueva migración al abrir. No borres una base dañada como método de reparación. Las preferencias se cambian desde la interfaz; borrar la base no las restablece. El borrado normal no garantiza eliminación forense ni borra copias que ya compartiste. Desinstalar o quitar la carpeta de la aplicación tampoco elimina necesariamente los datos del usuario.

## Soporte en GitHub

El soporte general es por [Issues](https://github.com/RodrigoUC/SORTH-AI/issues), sin correo de soporte establecido. Los issues y adjuntos son públicos: utiliza el ejemplo sintético y retira nombres, rutas personales, datos institucionales y secretos de cualquier captura o mensaje. No adjuntes bases SQLite ni planillas reales.

GitHub es un servicio externo: al visitarlo o publicar, GitHub procesa datos de cuenta, contenido y uso según su [declaración de privacidad](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). El funcionamiento local de SORTH no hace privados tus reportes en GitHub. Para vulnerabilidades sigue [SECURITY.md](SECURITY.md); no se afirma que el formulario privado esté habilitado hasta verificarlo.

## Base de esta revisión

Se inspeccionaron `gui_app.py`, `main.py`, `src/`, la configuración de empaquetado y los puntos de escritura de datos: `SessionRepository`, `LanguageManager`, `MotionController`, exportadores y `packaged_smoke.py`. Revisa este aviso si una versión añade red, registros, nuevas preferencias, almacenamiento o integraciones.
