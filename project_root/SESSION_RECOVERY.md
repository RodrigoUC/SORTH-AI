# Guardado y recuperación de sesión

SORTH guarda automáticamente al cambiar cursos, aulas, restricciones, semilla o horario. El indicador permanente **Sin cambios pendientes** confirma que no hay cambios pendientes de guardar. **Cambios sin guardar** permanece visible aunque otra operación actualice la barra de estado; su descripción muestra el error. Use **Reintentar** después de liberar espacio o corregir permisos.

Si un guardado falla al cerrar, se ofrecen **Reintentar**, **Descartar** y **Cancelar**. Cancelar es la opción predeterminada. Descartar cierra y pierde únicamente los cambios que no pudieron guardarse. El último guardado válido se conserva mediante una transacción SQLite.

## Ubicación estable

- Windows: `%LOCALAPPDATA%/SORTH/sorth_session.db` (alternativa: `~/AppData/Local/SORTH`)
- macOS: `~/Library/Application Support/SORTH/sorth_session.db`
- Linux: `$XDG_DATA_HOME/SORTH/sorth_session.db`, o `~/.local/share/SORTH/sorth_session.db`

Las rutas explícitas usadas por pruebas siguen aisladas. No se transmite información de diagnóstico.

## Migración sin reemplazos

Si la nueva ubicación no existe, se busca la ubicación anterior: `data/sorth_session.db` junto al ejecutable, o dentro de `project_root` al ejecutar el código fuente. Se crea una copia SQLite consistente, incluyendo datos confirmados en WAL, se verifica su integridad y se publica una segunda copia independiente sin sobrescribir el destino. La fuente original nunca se elimina ni modifica. Una copia `legacy-session-*.db` permanece en la carpeta de datos nueva.

Cualquier archivo existente en el destino tiene prioridad, aunque esté vacío o dañado. No se sustituye automáticamente por una sesión antigua. Si la migración falla por falta de espacio, permisos o corrupción, se muestra el problema y no se crea una sesión vacía como reemplazo. Si dos instancias intentan migrar a la vez, la primera publicación gana y la segunda respeta el destino existente. No abra dos instancias para editar la misma sesión simultáneamente.

Al rechazar la restauración y cerrar sin editar, la sesión anterior se conserva. Antes de guardar una sesión nueva después de rechazarla, SORTH crea una copia `previous-session-*.db`. Si no se puede crear, tampoco reemplaza la sesión anterior.

## Base dañada o inaccesible

El estado **Sesión no disponible** bloquea la edición y mantiene los archivos intactos. **Reintentar** vuelve a comprobar la lectura y ofrece restaurar cuando sea posible. No hay borrado, reparación destructiva ni selección automática de una copia más antigua.

Para una recuperación manual, cierre SORTH y conserve primero una copia de la carpeta completa, incluidos archivos `-wal` y `-shm` si existen. Con ayuda técnica, identifique una copia válida y sustitúyala sólo tras preservar el archivo afectado. No borre una base dañada para intentar que el programa arranque. Las copias contienen datos de la sesión: manténgalas privadas.

## Verificación

Las pruebas cubren migración y prioridad de rutas, WAL, copias independientes, fallo de escritura y lectura, disco lleno simulado, directorios de sólo lectura simulados, bases dañadas, rollback, cierre con cancelar/reintentar/descartar y persistencia del aviso tras otros mensajes. La suite se ejecuta también en Windows mediante el flujo de revisión del PR. Las pruebas Qt offscreen no sustituyen una comprobación interactiva en Windows con usuario estándar.
