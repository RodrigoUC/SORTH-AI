# Próximas mejoras propuestas

Revisión del árbol `6b901532bc7e86588561aa787362f4a8c19f9c5a`.
Propuestas para priorizar; **no son funciones implementadas**. Se mantienen la
identidad PyQt6 y las decisiones de `DESIGN.md`. No hace falta reescribir la app.
Se excluyen PDF, métricas existentes, MCP, idiomas, accesibilidad, fijación de
sesiones y escenarios, que ya tienen trabajo específico.

## Prioridad 1: control y prevención

### 1. Cancelar generación con seguridad

La integración de sesiones fijadas ya añade Cancelar y estado «Cancelando»:
descarta el resultado y espera a que el trabajador termine, conservando el horario
anterior. La mejora pendiente es interrumpir el cálculo de forma cooperativa
mediante comprobaciones en bucles de dominios/grupos y un resultado cancelado
diferente de error.
El horario anterior no cambia hasta aceptar un resultado completo y validado.
No usar terminación forzada del hilo.

Aceptación: cancelar antes/durante/después de un lote no persiste un resultado
intermedio ni sobrescribe el horario anterior; no quedan hilos activos al cerrar.
Pruebas deterministas con señal de cancelación inyectada. Objetivo de respuesta
medido en el equipo de referencia; no prometer latencia antes de medirla.

Evidencia: `src/gui/scheduler_worker.py:6–28`,
`src/gui/main_window.py:383–412`, `src/scheduling/scheduler.py:26–84`.
Qt documenta que `requestInterruption()` es una petición y el código debe
comprobarla: [QThread](https://doc.qt.io/qt-6/qthread.html#requestInterruption).

### 2. Revisar los cambios antes de importar

La importación valida y preserva la sesión si se cancela, pero la revisión se
centra en avisos; al aceptar reemplaza cursos/aulas y reinicia restricciones.
Añadir resumen «nuevos / modificados / eliminados», número de restricciones y
asignaciones afectadas y vista de errores por hoja/fila. Empezar con reemplazo
explícito; una futura fusión necesita reglas de conflicto propias.

Aceptación: la previsualización nunca modifica la sesión; confirma exactamente
los cambios indicados; archivo cambiado desde la revisión obliga a revalidar;
errores y cancelación conservan el estado anterior.

Evidencia: `src/gui/main_window.py:279–338`,
`src/infrastructure/excel_reader.py:143` y siguientes.

### 3. Deshacer/rehacer modificaciones locales

Hoy eliminar cursos/asignaciones requiere confirmación y modifica inmediatamente
el estado. Añadir un historial acotado de comandos para edición, eliminación y
colocación manual. No confundirlo con escenarios: el objetivo es revertir un
error inmediato en el mismo trabajo, manteniendo validación y persistencia.

Aceptación: una secuencia editar→eliminar→deshacer→rehacer restaura exactamente
curso, horario y excepciones; una edición nueva descarta sólo la rama de rehacer;
el historial se reinicia de forma explícita al importar/restaurar otra sesión.

Evidencia: `src/gui/course_manager_widget.py:407–443`,
`src/gui/schedule_viewer_widget.py:574–603`.

## Prioridad 2: rapidez demostrable y menos trabajo repetido

### 4. Importar sin congelar la ventana

La generación ya usa un hilo, pero `_load_excel()` lee/valida pandas/openpyxl en
el manejador GUI. Llevar lectura/validación a un trabajador con datos aislados;
mostrar etapa y permitir seguir consultando el horario anterior. Confirmar el
reemplazo únicamente en el hilo GUI y rechazar resultados de cargas obsoletas.

Aceptación: durante una carga grande un temporizador de UI sigue respondiendo;
segunda importación/cancelación no deja que un resultado antiguo reemplace al
nuevo; ningún trabajador accede a widgets; errores no alteran datos.

Evidencia: `src/gui/main_window.py:291–296`,
`src/infrastructure/excel_reader.py:92–128`.
Es una hipótesis fundada de bloqueo con archivos grandes, no un atasco cronometrado.

### 5. Medir y acelerar la búsqueda del horario

Cada cambio de texto recorre dos tablas, normaliza consulta/datos repetidamente y
reconstruye la cuadrícula. Primero medir 100, 1.000 y 5.000 grupos sintéticos en
Linux y Windows; guardar tiempos por etapa y memoria, no sólo tiempo del motor.
Después precalcular claves de búsqueda, calcular coincidencias una sola vez y
no regenerar una cuadrícula oculta. Migrar sólo esta tabla a Model/View si las
mediciones justifican el coste; no sustituir toda la aplicación.

Aceptación: resultados, selección por ID, filtros y exportación idénticos antes
y después; informe repetible con medianas y p95, hardware/versiones y muestras;
sin regresión de tiempos en tamaños pequeños. Acordar presupuesto tras baseline.

Evidencia: `src/gui/schedule_viewer_widget.py:434–472`; el benchmark actual declara
que excluye GUI/importación/exportación (`project_root/benchmark.py:1–8`). No hay
medición nueva en esta revisión. [Model/View de Qt](https://doc.qt.io/qt-6/model-view-programming.html)
respalda una evolución localizada si se necesita.

### 6. Editar cursos en lote con previsualización

La edición actual abre un curso cada vez. Permitir seleccionar varios cursos y
cambiar sólo campos marcados, por ejemplo tipo de aula, tamaño o preferencia de
día. Mostrar recuento y diferencias; validar el conjunto antes de aplicar una
transacción única. No alterar códigos/identidades en la primera versión.

Aceptación: campos no marcados conservan exactamente su valor; cualquier error
impide cambios parciales; el usuario puede deshacer el lote en una operación;
revalidación o invalidación explícita del horario afectado.

Evidencia: `src/gui/course_manager_widget.py:400–420`, `CourseDialog.get_course()`.

## Prioridad 3: nuevas funciones del planificador

### 7. Sugerir alternativas concretas para una sesión pendiente

Ya existen causas estáticas y colocación manual. Añadir «Ver opciones» que
enumere franjas/aulas válidas contra el estado actual y explique por qué las
alternativas descartadas chocan. En la primera versión no mover otras sesiones
ni relajar reglas para producir una sugerencia.

Aceptación: cada opción propuesta pasa el mismo validador al aplicarse; si el
estado cambia, recalcular antes de aceptar; cero candidatos se expresa como
«no hay opciones en el horario actual», no como prueba global de inviabilidad.

Evidencia: `src/scheduling/validation.py:unassigned_reason`,
`src/gui/manual_assignment_dialog.py`; `SCHEDULING_VALIDATION.md`.

### 8. Calendario operativo configurable por proyecto

Permitir editar días lectivos, apertura/cierre y descansos; hoy se usan defaults
07:00–22:00, almuerzo 12:00–13:00 y lunes–sábado. Mantener esos valores para
proyectos antiguos y previsualizar qué sesiones quedarían fuera. No adivinar
festivos ni normas institucionales; un calendario fechado sería otra fase.

Aceptación: generación, edición, validación, guardado/restauración y exportación
usan el mismo calendario versionado; rechazar intervalos inválidos; cambio con
horario existente requiere revisión; pruebas de bordes y descansos múltiples.

Evidencia: `src/scheduling/time_model.py:3–25`, llamadas a
`TimeModel.default()` en `main_window.py` y servicio de generación.

## Límites de esta revisión

Hallazgos estáticos comprobados; no se realizaron sesiones de usuario ni se
cronometró una UI en esta tarea. El Python por defecto no dispone de PyQt6, por
lo que no se ejecutaron nuevos ensayos gráficos. No interpretar los objetivos
de rendimiento anteriores como resultados. Ninguna propuesta cambia reglas de
docentes/cohortes mientras #14 siga pendiente de decisiones.
