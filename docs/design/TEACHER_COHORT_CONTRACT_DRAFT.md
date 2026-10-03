# Docentes y cohortes: contrato propuesto para revisión (#14)

Estado: **borrador; decisiones de dominio pendientes**. Este documento no activa
restricciones, no acredita aprobación institucional y no completa el issue #14.
Base inspeccionada: árbol `6b901532bc7e86588561aa787362f4a8c19f9c5a`.
Todos los identificadores y ejemplos siguientes son sintéticos.

## 1. Lo que existe

`Course.generate_groups()` crea grupos y partes; `Group` tiene `parent_group_id`
y `subgroup_index`, pero ninguno modela docentes ni cohortes. El validador exige
que las partes usen días distintos y la misma hora de inicio. No se puede deducir
docente, cohorte, exclusividad curricular ni estudiantes compartidos a partir
del código, nombre del curso o sufijo del grupo.

El contrato actual permite extremos adyacentes y expresa intervalos en minutos,
con día entero del `TimeModel`. Esos valores se mantienen en esta propuesta.

## 2. Decisiones confirmadas y pendientes

### Confirmado por el mantenedor (3 de octubre de 2026)

- Docentes y cohortes son **opcionales**. Cuando no se agregan, no participan en
  las restricciones y se conserva el funcionamiento original. Su ausencia no
  bloquea generación, edición, guardado ni exportación y no es un error.
- El caso normal es **un docente durante el curso**. Al activar esta función,
  la interfaz parte de asignar uno y permite que el usuario decida fijarlo o
  asignar varios. No se crea ni se asigna un docente ficticio por defecto cuando
  el usuario no ha agregado ninguno.
- Permitir varios docentes es una necesidad confirmada; su significado exacto
  (simultáneos o repartidos por sesión) todavía no está acordado.

La presentación debe explicar el alcance efectivo («sin restricciones de
docencia/cohortes» cuando no se usan), sin advertencias bloqueantes ni afirmar
que se comprobaron reglas sin datos. No exigir completar una función opcional.

### Pendiente antes de implementar reglas

1. **Varios docentes:** ¿participan juntos en cada clase o se elige el docente
   por sesión? ¿Cómo se asignan en las partes de un grupo dividido? Confirmar
   también si una misma asignación de curso abarca todos sus grupos, o se edita
   por grupo. No deducir esta granularidad del uso coloquial de «curso».
2. **Cruces y disponibilidad:** cuando sí se registra un docente, ¿se prohíbe
   ponerle dos clases al mismo tiempo y clases fuera de su disponibilidad
   declarada? Recomendación pendiente de aprobación: prohibir ambas. La misma
   semántica debe acordarse para cohortes y cualquier excepción/preferencia.
3. **Disponibilidad parcial:** falta concretar qué ocurre cuando se asigna una
   entidad pero no se declara su disponibilidad, y qué significa una lista
   declarada vacía. No confundirlo con la ausencia de docentes/cohortes, que ya
   está resuelta como función no utilizada.

No convertir recomendaciones pendientes en políticas ni relajar una regla dura
aprobada como reintento del generador. La sustitución/asignación automática de
identidades sería otro problema y queda fuera.

## 3. Esquema candidato y decisiones técnicas seguras

- `Teacher {id, label}` y `Cohort {id, label}`: ID opaco estable, independiente
  del nombre. Aceptar alias sintéticos; no pedir correos, matrículas ni listas
  personales. Nombres repetidos no fusionan entidades. Renombrar conserva ID.
- `Membership {group_ref, teacher_ids, cohort_ids}`: referencias explícitas.
  La granularidad curso/grupo/parte sigue pendiente; `group_ref` es sólo una
  forma candidata. Registrar nivel de herencia acordado; no usar simultáneamente
  niveles sin una regla de precedencia aprobada.
- `teacher_ids`/`cohort_ids` ausentes o `null`: información no declarada.
  `[]`: declaración explícita sin entidades, si se acepta esta representación.
  En ambos casos no hay identidades que comprobar y no se bloquea el flujo. La
  distinción de representación puede conservarse para edición/importación; no
  debe convertir una función opcional en obligatoria.
- `Availability {entity_kind, entity_id, status, windows}`: `status` distingue
  `unknown` de `declared`; cada ventana contiene `day`, `start_min`, `end_min`.
  Propuesta para aprobación: ventanas declaradas son ventanas permitidas, no
  excepciones; lista declarada vacía implica ninguna franja permitida. La UI
  debe hacer explícito ese efecto antes de guardarlo.
- Si se aprueban preferencias, guardarlas separadas de disponibilidad dura,
  con tipo explícito. No introducir pesos, penalizaciones ni excepciones
  institucionales sin especificación aprobada.
- Referencia inexistente, ID duplicado, valor no entero, intervalo invertido o
  día fuera del modelo: error estructurado y corrección requerida. Nunca
  descartar silenciosamente la referencia ni crear una entidad por su nombre.
- Los intervalos son semiabiertos `[inicio, fin)`: dos sesiones que se tocan en
  un extremo no se solapan. Validar identidad mediante IDs, nunca etiquetas.

Ejemplo de forma, **no archivo importable en la versión actual**:

```json
{
  "resource_contract_version": 1,
  "teachers": [{"id": "teacher-demo-01", "label": "Docente de ejemplo A"}],
  "cohorts": [{"id": "cohort-demo-01", "label": "Cohorte de ejemplo A"}],
  "memberships": [{
    "group_ref": "DEMO-G1",
    "teacher_ids": ["teacher-demo-01"],
    "cohort_ids": ["cohort-demo-01"]
  }],
  "availability": [{
    "entity_kind": "teacher",
    "entity_id": "teacher-demo-01",
    "status": "declared",
    "windows": [{"day": 1, "start_min": 480, "end_min": 720}]
  }]
}
```

## 4. Comprobación y mensajes

Sólo si se aprueban recursos simultáneos y reglas duras de conflicto y
disponibilidad, el intervalo de una sesión deberá estar permitido para todos sus
docentes/cohortes declarados, y cada identidad compartida prohibirá un
solapamiento aunque el aula sea distinta. Estas reglas aún son propuestas. La regla se aplica a cada
parte siguiendo la pertenencia que se acuerde; se conserva además la regla
actual de partes en días distintos a la misma hora.

El resultado debe separar:

- errores estructurales o violaciones probadas del horario;
- alcance no utilizado cuando no se agregan docentes/cohortes (sin error);
- disponibilidad no declarada para entidades asignadas (política pendiente);
- preferencias incumplidas, sólo si se acuerdan;
- sesiones pendientes porque la búsqueda no encontró colocación.

Un horario puede ser válido para las restricciones activas sin incluir la
función opcional; describir ese alcance y no afirmar validación de docencia o
cohortes no registradas. Un fallo greedy no demuestra inviabilidad matemática.

Errores estructurados sugeridos: `UNKNOWN_TEACHER_REFERENCE`,
`UNKNOWN_COHORT_REFERENCE`, `TEACHER_OVERLAP`, `COHORT_OVERLAP`,
`OUTSIDE_DECLARED_AVAILABILITY`, `RESOURCE_DATA_UNVERIFIED`. Incluir entidades,
grupos y franja implicados, más origen/hoja/fila cuando proceda; la capa GUI
traduce el mensaje sin introducir textos de presentación en el dominio.

## 5. Integración y compatibilidad propuestas

1. Acordar y registrar decisiones con ejemplos antes de modificar el motor.
2. Añadir modelos y un validador independiente. Un único contrato sirve a
   generación, edición manual, restauración y exportación, incluyendo MCP si
   está disponible. Extender el sobre de validación sin alterar el significado
   de las tuplas de asignación existentes.
3. Integrar filtrado duro de candidatos en el generador. Nunca relajar identidad,
   colisiones o disponibilidad aprobada como dura en el camino de reintentos.
4. Edición local de catálogos y pertenencias; seleccionar por etiqueta mostrando
   el ID si hay ambigüedad. No inferir cohortes de cursos. Cambios relevantes
   invalidan/revalidan el horario antes de guardarlo como vigente.
5. Proponer importación versionada mediante hojas adicionales `Docentes`,
   `Cohortes`, `Pertenencias` y `Disponibilidad`, con una fila por relación o
   ventana. Revisar encabezados exactos con el mantenedor antes de implementarlos.
   Evitar listas separadas por comas que resulten ambiguas con nombres.
6. Mantener importación antigua; campos nuevos ausentes no activan restricciones
   de docentes/cohortes ni bloquean el flujo. Presentar el alcance de validación
   original sin afirmar comprobaciones de recursos que no se agregaron. Rechazar versiones futuras no soportadas sin mutación.
7. Migración SQLite transaccional con respaldo previo y lectura antigua cubierta
   por pruebas. No fijar aquí un número de esquema: coordinar con la migración
   de escenarios y otras ramas para evitar colisiones de versión.
8. Mantener CSV/Excel de siete columnas actuales. Un intercambio enriquecido
   debe tener versión/acción distinta y permiso explícito de exportar identidades.

No añadir sincronización, cuentas, correos, analítica remota, matrículas reales,
viajes entre sedes, vacaciones o selección automática de docentes a este alcance.

## 6. Ejemplos que deben aprobarse y luego probarse

- A: DEMO-G1 y DEMO-G2, aulas distintas, mismo docente, lunes 08:00–09:00:
  conflicto bajo la propuesta de recursos simultáneos.
- B: mismo docente, sesiones 08:00–09:00 y 09:00–10:00: sin solapamiento.
- C: mismo nombre visible, IDs distintos: no fusionar ni inventar conflicto.
- D: docentes `[teacher-demo-01, teacher-demo-02]`: ambos ocupados si se aprueba
  docencia compartida; jamás escoger uno automáticamente.
- E: grupo dividido con pertenencia por grupo: ambas partes heredan los mismos
  recursos. Si varía por parte, exigir referencias explícitas acordadas.
- F: `teacher_ids` ausente: función de docentes no utilizada; generación y
  demás flujos mantienen el comportamiento original, sin docente ficticio.
- G: docente conocido con `status=unknown`: disponibilidad desconocida, aunque
  técnicamente se pueden comprobar colisiones de identidad; su obligatoriedad
  y la política de disponibilidad parcial siguen pendientes.
- H: referencia `teacher-missing`: error de importación, no preferencia descartable.
- I: disponibilidad declarada 08:00–10:00, sesión 09:30–10:30: fuera de ventana;
  probar por separado ventanas adyacentes y normalización de su unión.
- J: múltiples cohortes: cualquier identidad compartida colisiona bajo la
  propuesta, sin inferir estudiantes individuales ni compatibilidad curricular.

## 7. Criterio de aceptación y cierre

La fase de especificación termina con respuestas registradas y aprobación de
los ejemplos anteriores, formato de importación y decisiones aún pendientes.
La opcionalidad y el caso habitual de un docente ya están confirmados; no
volver a presentarlos como preguntas abiertas.
El issue completo sigue abierto hasta integrar dominio, generación, validador,
GUI y persistencia; pasar pruebas de compatibilidad, desconocidos, multirrecursos,
partes, edición manual, restauración y exportación; y revisar interfaz nativa.
Reportar pruebas aprobadas, fallidas y no ejecutadas, con commit final. Todos los
fixtures públicos serán sintéticos. No cerrar por añadir sólo este documento.

## Fuentes

- [Issue #14](https://github.com/RodrigoUC/SORTH-AI/issues/14).
- `project_root/src/scheduling/course.py`, `group.py`, `validation.py`.
- `project_root/SCHEDULING_VALIDATION.md`.
- `project_root/src/infrastructure/session_repository.py`, `excel_reader.py`.

Decisiones confirmadas: respuesta directa del mantenedor del 3 de octubre de
2026, puntos 1 y 3. El punto 2 requirió reformular la pregunta; no equivale a
aprobación de reglas de conflicto o disponibilidad.
