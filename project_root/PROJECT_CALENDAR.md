# Calendario opcional del proyecto

En **Configuración**, activa **Parámetros avanzados del calendario** y usa
**Guardar configuración y editar calendario**. Esta herramienta comienza
apagada. Permite seleccionar días lectivos entre lunes y domingo, apertura,
cierre y varios descansos. No introduce fechas reales, festivos ni disponibilidad
personal. Un cierre 00:00 significa 24:00 al final del mismo día.

El calendario pertenece a la sesión y a sus escenarios, no a la preferencia
visual. Ocultar el editor nunca cambia reglas guardadas. Un aviso permanente
señala calendarios personalizados. El botón Restablecer prepara los valores
originales; solo Revisar y aplicar y la confirmación posterior los guarda.
Cancelar no cambia el calendario.

Los proyectos antiguos mantienen lunes a sábado, 07:00–22:00 y descanso
12:00–13:00. Las horas son minutos enteros, las ventanas son semiabiertas y
los descansos no pueden solaparse ni ocupar toda la jornada. El orden de días
y descansos se normaliza. Una sesión puede no caber aunque quede tiempo para
sesiones más cortas; quedará pendiente, sin inventar una solución.

Antes de aplicar se enumeran las sesiones que quedarán pendientes. Las demás
mantienen su día real y su hora, aunque cambie el índice interno del día. No se
permite afectar sesiones fijadas sin desfijarlas explícitamente. Si una
 disponibilidad declarada hace referencia a un día eliminado, hay que editarla
primero: nunca se elimina o reinterpreta silenciosamente.

El guardado de calendario, asignaciones y recursos usa una única transacción
SQLite y conserva una copia anterior. Los errores dejan intacta la vista activa.
La migración al esquema 4 conserva copia del esquema anterior. Los formatos de
calendario desconocidos se rechazan. Generación, edición manual, reapertura,
indicadores y exportación usan el calendario guardado. Los escenarios comprueban
que sus metadatos coincidan con sus reglas antes de abrir o analizar.

MCP mantiene su contrato explícito de calendario fijo. Rechaza campos de
calendario no soportados en vez de declarar válidas restricciones que no aplica.
