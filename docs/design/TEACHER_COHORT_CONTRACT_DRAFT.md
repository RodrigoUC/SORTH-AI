# Recursos opcionales: contrato confirmado de #14

Estado: contrato aprobado e implementación local en rama separada, pendiente de
integración/revisión. Este documento no cierra el issue ni acredita políticas
institucionales. Todos los ejemplos y pruebas son sintéticos.

## Decisiones confirmadas (3 de octubre de 2026)

- Tres parámetros generales independientes: **docentes**, **grupos de estudiantes**
  y **estudiantes individuales**. Todos empiezan desactivados. El mantenedor
  prefiere grupos, pero confirmó casos individuales configurables.
- Sin recursos agregados/asignados no se aplica esa restricción, no se inventan
  identidades y el flujo original permanece disponible.
- Habitualmente un curso mantiene un docente. El usuario elige explícitamente
  qué sesiones imparte cada docente y puede usar docentes diferentes en sesiones
  de un mismo curso. La selección de docente por sesión es única; la docencia
  simultánea compartida no se presupone ni se asigna automáticamente.
- Una identidad compartida no puede participar en clases solapadas aunque sean
  cursos o aulas diferentes; sí puede participar en otras clases en otros horarios.
- Grupos y estudiantes individuales se asignan explícitamente por sesión. No se
  deducen matrículas, rosters, cohortes, exclusividad curricular ni pertenencias
  por nombres o códigos. No se implementa una relación persona→grupo; registrar
  sólo el grupo no acredita que se comprobaron identidades individuales.
- Disponibilidad opcional: desconocida no bloquea. Sólo franjas explícitamente
  declaradas limitan. La interfaz avisa antes de guardar una lista declarada vacía
  que impide toda colocación para esa identidad.

Fuentes: [issue #14](https://github.com/RodrigoUC/SORTH-AI/issues/14) y respuestas
explícitas del mantenedor del 3 de octubre sobre selección por sesión, no
solapamiento, opcionalidad y ambos modos de estudiantes configurables.

## Modelo y validación

`SchedulingResources` contiene catálogos inmutables `ResourceCatalog` de tipos
`teacher`, `student_group` y `student`. Cada catálogo conserva `enabled`, recursos
`Resource(id, label, availability)` y relaciones explícitas
`(group_id, resource_ids)`. IDs opacos estables; renombrar no cambia el ID y nombres
repetidos no fusionan identidades. Sólo nombre o alias: sin correos, edades,
cédulas, matrículas ni servicios externos.

La relación apunta al ID exacto de la sesión generada, incluidas partes divididas.
No hay herencia implícita por curso ni cambio de docente para resolver conflictos.
Docentes: cero o uno por sesión. Grupos/personas: cero o varios recursos explícitos.
Ausente, `null` y lista vacía se conservan y no imponen identidades ficticias.

Disponibilidad `null` = desconocida; lista vacía = ninguna ventana permitida;
lista de `(día, inicio, fin)` = unión de intervalos permitidos. Minutos enteros,
días del `TimeModel`, extremos semiabiertos `[inicio, fin)`: ventanas adyacentes
pueden unirse, un hueco real no. No se agregan horarios institucionales nuevos.

Errores estructurados distinguen ID duplicado, referencia desconocida,
pertenencia duplicada, ventanas inválidas, solapamiento por tipo y disponibilidad.
Errores estructurales se rechazan incluso con el parámetro desactivado; la
inactivación no sirve para aceptar corrupción. Reglas temporales de recursos se
aplican sólo cuando su parámetro está activo. Las reglas básicas de aula,
capacidad, laboratorio, jornada y sesiones divididas siempre permanecen activas.

El mismo contrato participa en candidatos/reintentos del generador, validador
final independiente, edición manual, guardado, restauración e importación de
escenarios. Fallo greedy conserva resultados parciales y no demuestra inviabilidad.

## Activación y desactivación

Configuración registra los tres parámetros generales con valor inicial apagado.
La preferencia del equipo sirve de estado inicial; el estado efectivo también se
conserva en cada sesión/escenario. Restaurar una sesión restaura sus parámetros
de recursos y muestra la cobertura efectiva. Una prevalidación de escenario usa
preferencias aisladas y no modifica las del usuario.

Cambiar un parámetro con datos/resultados pide confirmación explícita: el resultado
actual y sus fijaciones se retiran antes de regenerar, el catálogo y sus relaciones
se conservan. Apagar realmente deja de limitar nuevos horarios, y el estado
visible lo dice. No se mantiene un resultado anterior presentado como vigente
bajo un alcance cambiado. Cancelar no cambia datos ni preferencias. Fallo de
persistencia revierte el cambio en memoria y en preferencias.

Editar recursos valida el horario: si se vuelve incompatible, requiere aceptar
retirar el resultado/desfijar antes de aplicar. Eliminar cursos/sesiones con
relaciones pide permiso para quitar esas relaciones; conserva los recursos.

## Persistencia, intercambio y compatibilidad

- Sesión SQLite **schema3**, migración posterior a schema2 (fijaciones), con copia
  SQLite previa y transacción. Tabla singleton `scheduling_resources`, JSON
  interno `version: 1`. Versiones futuras y campos desconocidos fallan cerrados.
- Snapshots de escenarios incluyen el contrato completo. Comparabilidad y huella
  distinguen catálogos, asignaciones y parámetros activos/inactivos.
- Importación Excel existente intacta. No se han inventado nuevas hojas ni un
  formato público de rosters. La importación cubierta aquí es deserialización
  versionada de sesión/escenario, con validación estricta antes de reemplazar.
- CSV/Excel/PDF de horario siguen sin añadir identidades personales. Un futuro
  intercambio enriquecido requiere su propio contrato y confirmación de alcance.
- MCP mantiene su contrato actual sin catálogos de personas; no hay red ni
  proveedores nuevos. No se transmite información de estudiantes a servicios.

## Ejemplos de aceptación

1. Mismo docente, cursos y aulas distintos, lunes 08:00–09:00: conflicto.
2. Mismo docente 08:00–09:00 y 09:00–10:00: permitido.
3. Dos IDs con mismo alias: identidades diferentes, sin fusión.
4. Dos partes divididas con docentes diferentes elegidos: permitido, mantiene
   días distintos/mismo inicio del contrato base.
5. Mismo grupo o persona en dos sesiones solapadas: conflicto cuando está activo.
6. Dos sesiones sin recursos: flujo original, sin error por ausencia.
7. Disponibilidad desconocida: no limita; declarada vacía: sesión pendiente.
8. Desactivar con datos: conserva registros, confirma retirada del resultado,
   nuevo horario bajo reglas básicas; reactivar obliga regeneración.
9. Referencia inexistente aun desactivada: error, sin descartarla silenciosamente.
10. Guardado inválido/importación futura: último estado válido se conserva.

Cierre sólo después de integrar, revisar todas las pruebas y verificar la interfaz
nativa. Capturas Qt offscreen/Linux no sustituyen validación nativa Windows.
