# Indicadores explicables del horario

`src/scheduling/quality.py` separa cobertura, preferencias y uso de recursos.
No asigna pesos, no produce una nota global, no cambia el planificador y no
certifica validez ni optimalidad. La validación de restricciones se ejecuta por
separado. Un horario parcial puede tener 100% de preferencias evaluables y seguir
incompleto: las sesiones pendientes siempre se muestran junto a ese porcentaje.

## Contrato v1

1. En el hilo dueño del resultado, llamar a
   `QualitySnapshot.capture(assignments, groups, time_model, classrooms)`.
   Captura únicamente valores inmutables; el diccionario de asignaciones es la
   autoridad. No se leen `Group.assignment`, dominios ni `Classroom.occupancy`.
2. `analyze_quality(snapshot)` es puro, sin Qt, persistencia, reloj ni RNG. Devuelve
   un diccionario independiente serializable como JSON con `schema_version=1`,
   `scope="global"`, `unit="session"` y `validity="not_evaluated"`.
3. Volver a capturar tras generar, restaurar o editar. No capturar objetos que otro
   hilo está modificando simultáneamente. La captura no es un bloqueo transaccional.
   Cambiar filtros o seleccionar un aula en la cuadrícula no cambia el resumen.
4. Los cocientes están en [0, 1]; `None` se serializa como `null` y la interfaz muestra
   **No aplica** cuando no hay denominador. No se inventa 0% o 100% en ese caso.

### Cobertura

- `sessions`: sesiones conocidas, incluidas las partes de un grupo dividido.
- `assigned_sessions / sessions`: asignaciones con identidad de sesión conocida.
  `pending_sessions` incluye las restantes. Asignaciones huérfanas se enumeran en
  `unknown_assignment_ids`, sin inflar esta cobertura.
- `original_groups`: agrupa por `parent_group_id`, o por `group_id` si no se divide.
  `fully_assigned` exige todas las partes; `partially_assigned` exige alguna pero no
  todas; `unassigned` exige ninguna. La ausencia de partes en el catálogo o un
  `total_subgroups` inconsistente produce `unknown`, nunca un grupo completo.

### Preferencias

`day`, `time` y `room` tienen, cada uno, los siguientes contadores de sesiones:

- `requested`: tiene una preferencia declarada, aunque no sea evaluable.
- `absent`: no tiene preferencia; no entra en el denominador.
- `pending`: tiene preferencia y no tiene asignación; no entra en el denominador.
- `unknown`: tiene asignación, pero el objetivo o el valor observado no se conoce
  en el calendario/inventario. No entra en el denominador. Un inventario `None`
  hace desconocidas las preferencias de aula; `{}` representa inventario vacío.
- `evaluated`: asignada y evaluable; `satisfied / evaluated` es el cociente.
- `unsatisfied = evaluated - satisfied`.

Se cumple `requested = pending + unknown + evaluated` y
`requested + absent = sessions`. Pendiente tiene precedencia sobre desconocido:
no puede juzgarse una preferencia hasta que exista una asignación.

Satisfacción significa igualdad exacta de día, hora de inicio o nombre de aula.
La ventana de búsqueda de ±30 minutos del planificador **no** es tolerancia de
satisfacción. Las horas preferidas fuera de la ventana operativa y los días/aulas
inexistentes son desconocidos. No se comparan nombres traducidos de días.
Cada parte de un grupo dividido cuenta por separado y puede compartir la
preferencia heredada. La coincidencia de aula describe la sugerencia aunque una
restricción dura coincida con ella; no sustituye la validación de esa restricción.

### Distribución de carga

`day_load` incluye todos los días configurados, también los de carga cero:

- `assigned_sessions`: intervalos de duración positiva asignados al día.
- `teaching_minutes`: suma de `end-start` de esos intervalos, en minutos de sesión.
  Dos sesiones simultáneas de una hora suman 120 minutos de docencia.
- `teaching_minutes_ratio`: minutos del día / minutos de todos los días conocidos.

Se incluyen intervalos asignados con metadatos de grupo desconocidos porque sí
consumen tiempo; se identifican aparte en cobertura. Días desconocidos e intervalos
no positivos quedan fuera de la distribución y generan un aviso estructurado.
No se afirma que una distribución uniforme sea mejor para la institución.

### Ocupación temporal

Para cada aula y día:

- Denominador: minutos de la ventana operativa menos la unión de exclusiones.
- Numerador: unión de intervalos asignados intersectada con esos minutos disponibles.
- Las aulas sin uso forman parte del denominador. Los totales suman minutos-aula,
  no promedios de porcentajes. Se incluyen detalles por aula y día.
- Se descuenta el almuerzo de `TimeModel`, recortado a la ventana operativa. El
  argumento opcional `room_exclusions={(aula, día): [(inicio, fin), ...]}` permite
  otros cierres, también solapados, sin contarlos dos veces. Intervalos semiabiertos.
- Las restricciones de cursos no cierran un aula en el tiempo; no se descuentan.
- No se infiere disponibilidad desde `occupancy`. Aulas desconocidas se enumeran
  y no reciben un denominador ficticio. Inventario desconocido/vacío o cero minutos
  disponibles producen `None`. La app actual sólo configura el almuerzo; el soporte
  de cierres adicionales es un contrato de análisis, no una nueva pantalla.

Los solapamientos se unen y el tiempo no disponible se excluye, por lo que un
cociente nunca supera 100%. Esto **no** oculta ni resuelve conflictos: sólo el
validador independiente determina integridad. No se mide ocupación de asientos.

### Excepciones manuales

Sólo hay una excepción modelada actualmente: laboratorio en aula que no es LAB.
`recorded_ids` conserva banderas explícitas; `active_ids` exige además asignación
actual y necesidad real de la excepción. `unconfirmed_ids` detecta la necesidad
sin bandera; `inactive_ids` son banderas pendientes o ya innecesarias; `unknown_ids`
son sesiones LAB/banderas asignadas a un aula cuyo tipo no puede consultarse.
No se infiere que una asignación ordinaria fue manual. El cociente es
`len(active_ids) / assigned_sessions`; no representa calidad deseable.

## Integración y comprobación

- El diálogo de resumen existente muestra explicaciones, valores, pendientes y
  excepciones; el botón Cerrar permanece fuera del contenido desplazable.
- `benchmark.py --json` añade `quality` sin incluir el análisis en la región cronometrada.
- `tests/fixtures/quality/partial_schedule.json` es sintético. Sus oráculos de
  aritmética son independientes de las funciones de puntuación del planificador.
- `test_quality.py` cubre resultados parciales/vacíos/completos/divididos,
  restauración SQLite, edición, captura inmutable, preferencias desconocidas,
  cierres solapados y reproducibilidad. Una regresión de preferencias se detecta
  incluso si el número de asignaciones permanece igual.
- `test_quality_summary.py` cubre filtros globales, quitar/reasignar, localización
  ES/EN y cierre del resumen. No cambia el esquema de persistencia.

## Decisiones de producto pendientes

Ninguna impide este contrato descriptivo. Antes de agregar una evaluación global,
la institución tendría que decidir qué objetivos y prioridades significan mejor,
si desea una tolerancia horaria diferente de la igualdad exacta y si las preferencias
se agregan por grupo original en lugar de por sesión. También falta definir cómo
se introducirían cierres de aulas en el producto. No se han supuesto esos cambios.

La revisión nativa Windows y la evidencia del commit/CI final siguen siendo
necesarias antes de cerrar el issue; capturas Qt Linux no prueban soporte Windows.
