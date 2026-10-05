# Actualizaciones oficiales de SORTH

## Consultar una versión

1. Abre **Configuración → General → Buscar actualizaciones**.
2. La ventana muestra la versión instalada y la identidad de compilación cuando
   está empaquetada. Pulsa **Buscar actualizaciones** para consultar GitHub.
3. Revisa las notas o abre **Ver publicación oficial**. Solo se consideran
   versiones estables del repositorio `RodrigoUC/SORTH-AI`; se excluyen borradores,
   prepublicaciones y etiquetas que no tengan una versión válida.

No se consulta la red al abrir Configuración ni por defecto al iniciar SORTH.
**Avisar de actualizaciones al iniciar** es una preferencia explícita: marca la
casilla y guarda Configuración para activarla. El aviso solo consulta y orienta a
esta ventana; nunca descarga ni ejecuta por sí mismo. Cancelar Configuración
conserva el valor guardado anterior. Los fallos de conexión del aviso no interrumpen
el trabajo; una consulta manual permite ver el estado y reintentar.

GitHub recibe datos normales de conexión, incluida la IP; no se envían horarios,
archivos ni datos académicos. Lee [Privacidad](../../PRIVACY.md).

Un repositorio sin publicaciones estables muestra **Todavía no hay publicaciones
estables oficiales**. Esto no demuestra que una compilación de revisión sea la
última. Las compilaciones con distintos commits y la misma versión (por ejemplo,
`2.0.0`) no se ordenan por hash ni se ofrecen como una versión nueva. No se cambia
el número de versión solo para probar el actualizador.

## Descargar y decidir si instalar

La aplicación empaquetada para Windows permite descargar un único instalador x64
compatible cuando la publicación ofrece tamaño y digest SHA-256 válidos. Falta de
hash, activos ambiguos o formato incompatible mantienen la consulta de notas,
pero no habilitan una descarga supuestamente verificada.

- La descarga ocurre en una carpeta temporal privada, separada de los datos y la
  instalación. El cliente limita tamaño, tiempo, destinos HTTPS y redirecciones.
- Se comprueban tamaño y SHA-256 antes de ofrecer la instalación y nuevamente
  antes de ejecutarla. Una descarga parcial o alterada nunca se ejecuta.
- **SHA-256 verifica coincidencia con los metadatos de GitHub; no autentica al
  editor**, no es un análisis antimalware y no sustituye Authenticode. Los
  instaladores revisados actualmente no están firmados.
- **Guardar, cerrar SORTH e instalar…** pide confirmación separada y empieza en
  Cancelar. Cancelar deja la sesión abierta. Cerrar la ventana intenta eliminar
  su descarga temporal; un cierre inesperado puede dejarla para limpieza del SO.
- Después de confirmar, SORTH guarda la sesión y crea/reabre una copia SQLite
  consistente y validada en la carpeta de datos. Si falla, permanece abierto y
  no lanza el instalador. La copia de sesión no incluye automáticamente todos los
  escenarios, preferencias ni archivos externos: conserva además una copia
  independiente de esos datos siguiendo la política manual de recuperación.
- El instalador solo se abre después de cerrar la aplicación y liberar el bloqueo
  de sesión, mediante el manejo de seguridad de adjuntos de Windows. La
  indisponibilidad o rechazo de esa comprobación bloquea el lanzamiento: no hay
  ejecución alternativa que omita las protecciones. Debes completar el asistente
  de Windows; SORTH no acepta avisos, solicita elevación ni usa modo silencioso.
- No omitas SmartScreen o Defender. Cierra las demás instancias y no uses a la vez
  binarios viejos/nuevos sobre la misma base. Los instaladores conservan la carpeta
  de datos, pero un esquema nuevo puede impedir volver a una versión antigua.

El código fuente y otros sistemas pueden consultar publicaciones y abrir la página
oficial; no ofrecen instalar un ejecutable Windows desde esta ventana.

## Contrato de publicación y verificación

Esta función no crea una release. Antes de publicar, el mantenedor debe superar
las [puertas de distribución](../WINDOWS_RELEASE_ACCEPTANCE.md), aprobar el commit
exacto y actualizar `project_root/VERSION`. Las etiquetas aceptadas son `X.Y.Z` o
`vX.Y.Z` (metadatos semánticos `+...` no cambian precedencia), y se compara el número
mayor/menor/parche. El instalador esperado conserva el formato del empaquetado:
`SORTH-X.Y.Z-<12hex>-windows-x64-unsigned-setup.exe`.

Los activos deben estar subidos, tener tamaño dentro del límite y un digest
`sha256:...` en la API oficial. Si GitHub no lo proporciona, la instalación queda
inhabilitada. La consulta no usa autenticación y puede alcanzar los límites de
peticiones; se puede reintentar más tarde. Una colección que supera el límite de
consulta informa error en vez de declarar que no hay actualizaciones.

El smoke fuente/empaquetado usa respuestas sintéticas y nunca contacta GitHub ni
lanza un instalador. Los tests de Windows comprueban la integración de seguridad
sin autorizar una ejecución real. La publicación real, la reputación SmartScreen,
la firma del editor y la aceptación interactiva de una actualización entre dos
versiones siguen siendo puertas independientes.

Fuentes: [activos de releases de GitHub](https://docs.github.com/en/rest/releases/assets)
y [Attachment Execution Services de Windows](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-iattachmentexecute).
