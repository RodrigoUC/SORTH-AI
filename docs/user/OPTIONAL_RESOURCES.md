# Docentes y estudiantes opcionales

En **Configuración**, active de forma independiente **Docentes**, **Grupos de
estudiantes** o **Estudiantes individuales**. Todos vienen apagados. Sin añadir
recursos, SORTH sigue funcionando como antes.

1. Abra el botón del recurso activado y agregue un nombre o alias local.
2. Seleccione una sesión y pulse **Elegir recursos de la sesión**. Puede dejarla
   sin selección. Cada parte dividida se elige por separado.
3. Un docente por sesión es el valor normal. Para distintos docentes en un curso,
   elija el docente de cada sesión. No se asignan docentes automáticamente.
4. Los grupos de estudiantes y las personas permiten varias selecciones. Una
   identidad compartida evita cruces; los nombres iguales no se fusionan.
5. Opcionalmente declare franjas de disponibilidad. Sin declarar no limita;
   declarada sin franjas impide asignar sesiones y pide confirmación.
6. Guarde. Si el cambio entra en conflicto con el horario, debe confirmar retirarlo
   y desfijar sus sesiones para regenerar. Cancelar conserva el estado previo.

Los grupos son etiquetas compartidas; SORTH no deduce qué personas los integran.
Si necesita comprobar a una persona concreta, asígnela explícitamente a sus
sesiones. No hace falta introducir documentos de identidad, edades o correos.
Todo queda en la sesión local, sin nuevos servicios de red.

## Qué significa desactivar

Desactivar conserva catálogo y relaciones, pero deja de aplicar ese parámetro a
nuevos horarios. Con datos/resultados, aparece una confirmación y se retira el
resultado previo antes de regenerar. El aviso superior identifica los parámetros
inactivos con datos conservados. Las reglas básicas de aulas y horarios siguen
activas. Activar de nuevo también regenera bajo el nuevo alcance.

Las sesiones/escenarios guardan sus parámetros efectivos. Al restaurarlos se
restaura ese alcance, indicado en la ventana. Los CSV/Excel/PDF actuales no añaden
identidades de docentes o estudiantes; mantenga las copias de la base local en
un lugar privado. Se crea un respaldo antes de migrar la sesión de schema2 a 3.

## Alcance técnico

El contrato interno JSON version1 se valida estrictamente en restauración de
sesiones y escenarios. El importador Excel antiguo no cambia; no se admite aún
un nuevo formato de hojas de docentes, matrículas o rosters. La disponibilidad
usa minutos exactos HH:mm y el calendario existente, sin reglas institucionales
inferidas. La búsqueda puede devolver pendientes; eso no prueba que el problema
sea matemáticamente imposible.

Si las preferencias opcionales están dañadas, una sesión válida conserva sus
parámetros de recursos y permite recuperarlas desde Configuración. Restablecer
las herramientas no borra ni desactiva los recursos de esa sesión.

## Límite técnico pendiente de medir

La versión actual valida esquema, tipos, referencias, identificadores y etiquetas
(hasta 120 caracteres), pero no impone un máximo total de recursos, ventanas de
disponibilidad, relaciones o bytes de JSON dentro de una sesión SQLite local.
Un catálogo local excepcionalmente grande puede consumir memoria o bloquear la
interfaz durante su carga; las pruebas actuales no certifican capacidad a esa
escala. No se truncan registros silenciosamente. No se añadió un límite
institucional arbitrario sin mediciones representativas. MCP rechaza estos campos
y no ofrece una ruta externa para cargar catálogos de recursos.

## Integridad de parámetros y preferencias

Las activaciones de docentes/grupos/personas pertenecen únicamente a la sesión
SQLite aceptada; los valores correspondientes en el JSON de herramientas son
una copia de presentación, nunca activan un proyecto nuevo. Restaurar una sesión
recupera siempre sus reglas efectivas. Ediciones de recursos y calendario usan la
misma transacción con reversión de presentación e historial.

El JSON de herramientas y SQLite son archivos separados: no se afirma una
transacción ACID entre ambos. Si falla guardar la sesión y también restaurar el
JSON previo, se conservan la sesión, sus entidades y activaciones; se informa que
algunas preferencias de herramientas ya se guardaron, se bloquea la edición y se
pide recuperar la configuración. Un fallo visual después de confirmar ambos
guardados se identifica como cambio guardado pendiente de recuperar la vista.

Consulta [Privacidad y datos locales](../../PRIVACY.md) para ubicaciones, datos
conservados, exportaciones, respaldos y diferencia entre desactivar y borrar.
