# Guardado y recuperación de sesión

SORTH guarda automáticamente al cambiar cursos, aulas, restricciones, semilla o horario. El indicador permanente **Sin cambios pendientes** confirma que no hay cambios pendientes de guardar. **Cambios sin guardar** permanece visible aunque otra operación actualice la barra de estado; su descripción muestra el error. Use **Reintentar** después de liberar espacio o corregir permisos.

Si un guardado falla al cerrar, se ofrecen **Reintentar**, **Descartar** y **Cancelar**. Cancelar es la opción predeterminada. Descartar cierra y pierde únicamente los cambios que no pudieron guardarse. El último guardado válido se conserva mediante una transacción SQLite.

## Ubicación estable

- Windows: `%LOCALAPPDATA%/SORTH/sorth_session.db` (alternativa: `~/AppData/Local/SORTH`)
- macOS: `~/Library/Application Support/SORTH/sorth_session.db`
- Linux: `$XDG_DATA_HOME/SORTH/sorth_session.db`, o `~/.local/share/SORTH/sorth_session.db`

Las rutas explícitas usadas por pruebas siguen aisladas. No se transmite información de diagnóstico.

## Una ventana de edición por sesión

El inicio normal de la aplicación obtiene un bloqueo exclusivo antes de abrir o
migrar la base. Una segunda ventana que use la misma ruta canónica se rechaza
con un aviso; no abre la sesión ni puede reemplazar cambios de la primera. El
bloqueo dura hasta finalizar la aplicación, incluidos los guardados al cerrar.
No es una opción configurable. Las carpetas de datos realmente independientes
pueden usarse por separado; no se añade un selector nuevo de carpeta.

El archivo `sorth_session.db.gui.lock` usa `QLockFile` de Qt, sin vencimiento por
antigüedad. Tras un cierre abrupto, Qt puede recuperar el bloqueo de un proceso
local terminado. Un bloqueo desconocido, malformado o de otro equipo se conserva
y el inicio falla de forma segura. Si aparece el aviso, cierre la otra ventana y
reintente; si persiste, revise permisos o solicite ayuda. No elimine bloqueos de
una aplicación abierta. No se ofrece desbloqueo forzado.

Esta protección es cooperativa y se limita al inicio GUI de esta versión, en un
sistema de archivos local. Versiones antiguas, herramientas externas y llamadas
directas al repositorio no respetan necesariamente el bloqueo. No mezcle versiones
abiertas ni use la carpeta de sesión en una unidad de red, sincronizada o compartida
entre contenedores. Las herramientas de recuperación que sólo leen la fuente y
crean un candidato independiente y el smoke-test aislado no toman el bloqueo de
la sesión habitual. La sustitución manual y la vuelta a una versión anterior
siguen exigiendo cerrar todas las instancias y preservar los archivos originales.

## Migración sin reemplazos

Si la nueva ubicación no existe, se busca la ubicación anterior: `data/sorth_session.db` junto al ejecutable, o dentro de `project_root` al ejecutar el código fuente. Se crea una copia SQLite consistente, incluyendo datos confirmados en WAL, se verifica su integridad y se publica una segunda copia independiente sin sobrescribir el destino. La fuente original nunca se elimina ni modifica. Una copia `legacy-session-*.db` permanece en la carpeta de datos nueva.

Cualquier archivo existente en el destino tiene prioridad, aunque esté vacío o dañado. No se sustituye automáticamente por una sesión antigua. Si la migración falla por falta de espacio, permisos o corrupción, se muestra el problema y no se crea una sesión vacía como reemplazo. Si dos instancias intentan migrar a la vez, la primera publicación gana y la segunda respeta el destino existente. No abra dos instancias para editar la misma sesión simultáneamente.

Al rechazar la restauración y cerrar sin editar, la sesión anterior se conserva. Antes de guardar una sesión nueva después de rechazarla, SORTH crea una copia `previous-session-*.db`. Si no se puede crear, tampoco reemplaza la sesión anterior.

## Base dañada o inaccesible

El estado **Sesión no disponible** bloquea la edición y mantiene los archivos intactos. **Reintentar** vuelve a comprobar la lectura y ofrece restaurar cuando sea posible. No hay borrado, reparación destructiva ni selección automática de una copia más antigua.

Para una recuperación manual, cierre SORTH y conserve primero una copia de la carpeta completa, incluidos archivos `-wal` y `-shm` si existen. Con ayuda técnica, identifique una copia válida y sustitúyala sólo tras preservar el archivo afectado. No borre una base dañada para intentar que el programa arranque. Las copias contienen datos de la sesión, incluidos recursos personales cuando existan: manténgalas privadas. Incluya también `sorth_projects.db` para conservar escenarios; editar la sesión no modifica esas copias. Consulte [Privacidad y datos locales](../../PRIVACY.md) para configuración separada y eliminación.

## Verificación

Las pruebas cubren migración y prioridad de rutas, WAL, copias independientes, fallo de escritura y lectura, disco lleno simulado, directorios de sólo lectura simulados, bases dañadas, rollback, cierre con cancelar/reintentar/descartar y persistencia del aviso tras otros mensajes. La suite se ejecuta también en Windows mediante el flujo de revisión del PR. Las pruebas Qt offscreen no sustituyen una comprobación interactiva en Windows con usuario estándar.

## Esquema, recuperación verificable y vuelta a una versión anterior

El esquema se identifica mediante `PRAGMA user_version` (versión actual: 4). Una base existente de esquema anterior se copia a `schema-session-*.db` antes de migrar; la migración y su número de versión se confirman en una sola transacción. La matrícula y las excepciones manuales de laboratorio se conservan cuando existen; en esquemas que no tenían esos campos se inicializan a 0/sin excepción. Abrir nuevamente no repite la migración ni crea copias adicionales. Si falla la copia, no comienza la migración. Una versión de esquema más nueva se rechaza antes de modificarla.

También se ofrece restaurar una sesión que sólo contiene aulas o una sesión vacía guardada intencionalmente. No se interpreta la ausencia de cursos como permiso para reemplazar datos.

Para asistencia técnica con el entorno fuente instalado:

1. Cierre todas las instancias de SORTH. Copie la carpeta de datos completa a una carpeta privada de resguardo; conserve los archivos `-wal` y `-shm` si existen. No use una carpeta sincronizada mientras se recupera.
2. Seleccione una copia conocida `previous-session-*.db`, `legacy-session-*.db` o `schema-session-*.db`. Si sólo queda la base afectada, se puede verificar ésta sin reemplazarla.
3. Cree una carpeta nueva y ejecute desde `project_root`: `python tools/recover_session.py --source "RUTA/copia.db" --output "CARPETA_NUEVA/sorth_session.db"`.
4. La herramienta verifica la integridad SQLite, incluye los datos confirmados de WAL, valida la lectura de los campos y prepara un candidato independiente. Rechaza destinos existentes y esquemas más nuevos. No selecciona una copia automáticamente, ni reemplaza ni borra la fuente. Una copia puede estar sana pero ser antigua: compruebe su contenido y fecha.
5. Sólo después de conservar la carpeta completa original, con SORTH cerrado, aparte la carpeta activa completa (incluidos sus archivos auxiliares), cree una carpeta activa vacía y copie el candidato allí con el nombre `sorth_session.db`. Conserve ambas carpetas. Abra SORTH y acepte restaurar; revise aulas, cursos, restricciones, semilla, asignaciones y excepciones antes de seguir editando. La validez del horario se comprueba por separado de la integridad del archivo.

No hay selector gráfico de copias todavía; la herramienta requiere el entorno Python fuente y asistencia técnica. No abra una base de una versión más nueva con un ejecutable antiguo: los ejecutables anteriores a esta protección no reconocen la incompatibilidad. Para volver atrás, use el ejecutable correspondiente con una copia previa a la actualización, preparada y conservada separadamente. Los cambios posteriores a esa copia no estarán presentes. Nunca sustituya una sesión actual por una copia antigua sin decidir explícitamente qué datos recuperar.

## Límites de importación y evidencia de fallo

Se rechazan libros de más de 25 MiB comprimidos, 100 MiB de contenido ZIP expandido, 1.000 entradas ZIP o 10.000 filas de datos por hoja. Estos límites se comprueban antes de reemplazar la sesión; no se truncan datos. Divida libros mayores y verifique cada importación. Los límites reducen consumo accidental, pero no convierten el lector en un entorno aislado para archivos hostiles.

`test_data_resilience.py` verifica disco lleno real mediante el límite de páginas SQLite, errores tardíos de escritura, terminación de un proceso con una transacción sin confirmar, borrado transaccional, copias completas, migración fallida/idempotente y rechazo de esquemas nuevos. `test_import_state_safety.py` compara datos, restricciones, horario, excepciones, estado de guardado y bytes de la base antes/después de cancelar o fallar una importación. Las pruebas existentes cubren sólo lectura, WAL, prioridad del destino y cierre con reintento/cancelación/descarte. Una caída abrupta del sistema, interrupción real de alimentación y permisos ACL de Windows requieren pruebas manuales sobre datos descartables; no están certificados por estas simulaciones.

## Candidato de recuperación sin instalar Python

La aplicación empaquetada admite un comando de asistencia, sin abrir la sesión
predeterminada ni activar automáticamente una copia. Cierre SORTH y conserve
la carpeta completa original. Con el ejecutable de la versión adecuada, use
rutas explícitas y una carpeta de salida nueva:

```powershell
$p = Start-Process -FilePath 'C:\SORTH\SORTH.exe' -ArgumentList @('--recover-session', '--source', '"D:\Resguardo\copia.db"', '--output', '"D:\Candidato\sorth_session.db"', '--report', '"D:\Candidato\resultado.json"') -PassThru -Wait
$p.ExitCode
Get-Content -LiteralPath 'D:\Candidato\resultado.json'
```

Cree antes `D:\Candidato`; la herramienta exige archivos de salida/informe nuevos.
`ok: true` y código 0 indican un candidato SQLite verificable, no su activación ni
una prueba visual de su contenido. `ok: false` exige investigar el error y mantener
los originales. El EXE de ventana escribe JSON porque no dispone de consola fiable.
Una versión reciente puede migrar el candidato a su esquema: **no** lo use para
producir una copia para un ejecutable anterior. La vuelta atrás utiliza el resguardo
previo y su versión compatible, conservando por separado los cambios recientes.
