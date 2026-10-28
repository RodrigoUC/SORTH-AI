# Guardado y recuperación de sesión

SORTH guarda automáticamente cursos, aulas, restricciones, semilla, recursos,
calendario y resultado. **Sin cambios pendientes** confirma el guardado; **Cambios
sin guardar** conserva el aviso aunque cambie la barra de estado. Use **Reintentar**
después de corregir espacio o permisos. Al cerrar tras un fallo puede reintentar,
cancelar o descartar únicamente los cambios no guardados.

## Ubicación y acceso

- Windows: `%LOCALAPPDATA%/SORTH/sorth_session.db`.
- macOS: `~/Library/Application Support/SORTH/sorth_session.db`.
- Linux: `$XDG_DATA_HOME/SORTH/sorth_session.db`, o `~/.local/share/SORTH/sorth_session.db`.

La aplicación obtiene un bloqueo exclusivo antes de abrir la sesión y lo conserva
hasta terminar los guardados de cierre. Otra ventana con la misma ruta se rechaza.
No elimine el archivo de bloqueo para forzar el acceso. No use la base en unidades
de red o carpetas sincronizadas. Los respaldos contienen los mismos datos privados
que la sesión; manténgalos fuera de reportes públicos.

## Formato vigente

La versión 3.0.0 utiliza esquema SQLite 5. No importa ubicaciones antiguas ni migra
esquemas anteriores. Un archivo existente incompatible o dañado queda intacto y
bloquea la edición. Para usar datos anteriores, conserve sus archivos y abra un
entorno de sesión independiente con el Excel original. No sobrescriba una base
antigua para intentar convertirla.

El guardado distingue datos todavía sin generar de un horario generado con cero
asignaciones. Al restaurar se utilizan los cursos y sugerencias guardados, aunque
el Excel original haya cambiado o ya no exista. No se reimporta durante la apertura.

Todas las asignaciones se validan antes de guardar y cargar. Las decisiones de
fijación, excepción LAB y presencia de resultado admiten enteros SQLite 0 o 1;
la división de cursos admite además NULL para el modo automático. Los valores
dañados se rechazan; no se interpretan mediante su valor de verdad.

## Copias independientes

Rechazar la restauración y cerrar sin editar conserva la sesión anterior. Antes
de reemplazarla con una sesión nueva se crea `previous-session-*.db`. Un fallo de
respaldo impide el reemplazo. Las copias SQLite incluyen cambios confirmados en WAL.
El catálogo `sorth_projects.db` se respalda por separado para conservar escenarios.

Ante **Sesión no disponible**, conserve la carpeta completa, incluidos `-wal` y
`-shm`, y solicite ayuda técnica. Reintentar sólo habilita la edición si se logra
validar y presentar la sesión. No hay borrado ni reparación destructiva automática.

## Recuperación explícita

Con SORTH cerrado y un respaldo del formato actual, ejecute desde `project_root`:

```powershell
python tools/recover_session.py --source 'D:\Resguardo\session.db' --output 'D:\Candidato\session.db' --report 'D:\Candidato\resultado.json'
```

El ejecutable admite los mismos argumentos precedidos por `--recover-session`.
Los archivos de salida deben ser nuevos. El comando valida una copia independiente,
no abre la sesión habitual ni activa el candidato. Rechaza corrupción, formatos
no vigentes y destinos existentes, conservando la fuente. Un código 0 y `ok: true`
confirman la validación del candidato; revise su contenido antes de adoptarlo.

La recuperación preserva el esquema actual: no convierte bases ni prepara copias
para versiones anteriores. Cada versión incompatible requiere su propio entorno.

## Verificación

Las pruebas comprueban persistencia, presencia del resultado, rechazo sin mutación,
respaldos, WAL, disco lleno, rollback ante errores tardíos, permisos y recuperación.
Las pruebas sin pantalla no sustituyen aceptación interactiva ni fallos reales de
alimentación o permisos ACL en Windows.
