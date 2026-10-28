# Proyectos y escenarios locales

El botón **Proyectos y escenarios** conserva alternativas sin cambiar el flujo
habitual de sesión única con guardado automático. Un proyecto tiene identificador
opaco y nombre visible; contiene escenarios, cada uno con su propio identificador.

- **Crear proyecto desde la sesión** conserva los datos actuales como escenario `1`.
- **Guardar como escenario** guarda la sesión actual en el proyecto de la fila
  seleccionada. Siempre requiere un nombre nuevo, nunca reemplaza otra copia.
- **Duplicar** copia exactamente el escenario seleccionado, no los cambios actuales.
- **Renombrar** cambia solamente el nombre del escenario y conserva su identificador.
- **Abrir escenario** valida primero sus datos/formato/calendario, pide confirmar,
  guarda el trabajo actual y crea una copia de recuperación antes de cargarlo.
- Selecciona exactamente dos filas (Ctrl/clic o selección de teclado) para comparar.

La barra de estado distingue el guardado de la sesión de los cambios posteriores
a la copia nombrada. El estado compara valores persistidos, incluidas excepciones
y sesiones fijas; guardar sin cambios no marca el escenario como modificado.
La sesión activa continúa en la base habitual: al reiniciar se ofrece su
restauración habitual. Las copias nombradas se abren desde el catálogo.

## Persistencia y recuperación

`ProjectRepository` mantiene `sorth_projects.db` junto a la base de sesión. Los
nombres admiten 1–120 caracteres visibles, normalización NFC y comparación Unicode
sin distinción de mayúsculas; nunca forman rutas o consultas SQL. Los identificadores
UUID son independientes del nombre. La unicidad se aplica en SQLite (proyecto en
el catálogo; escenario dentro del proyecto), también ante llamadas concurrentes.

El catálogo guarda la copia SQLite completa como BLOB, no una selección parcial de
columnas. Incluye cursos, aulas, restricciones, semilla, asignaciones, excepciones,
marcas fijas, calendario y recursos con el contrato de sesión actual.
`SessionRepository` valida exclusivamente el esquema 5. El catálogo usa esquema 2.
La API de backup incluye WAL; los snapshots se validan en archivos temporales sin
modificar el BLOB original. No hay importación automática de sesiones anteriores.
Los proyectos se crean explícitamente a partir de la sesión actual. Los nombres
duplicados, fallos de inserción y formatos incompatibles no reemplazan originales.

## Comparación

La comparación utiliza exclusivamente `QualitySnapshot` / `analyze_quality`, contrato
v1 de `QUALITY_METRICS.md`. Muestra cobertura, pendientes, preferencias satisfechas
frente a evaluables, pendientes/desconocidas, minutos de docencia por día,
minutos-aula ocupados/disponibles y excepciones activas. Cero denominador se muestra
como **No aplica**. No se calcula puntuación global ni se declara ganador.

También compara entradas completas, restricciones, sesiones fijas con su aula,
día, intervalo y excepción LAB registrada, semilla, calendario y versiones.
Los valores diferentes se muestran en orden izquierda/derecha. Las asignaciones
no fijadas siguen siendo resultados y no se tratan como restricciones nuevas.
Cualquier diferencia o versión de algoritmo desconocida advierte que no hay
comparabilidad directa. La semilla diferente se informa, sin suponer que invalida
la aritmética descriptiva. Los calendarios no soportados no se recalculan usando
las reglas actuales y tampoco pueden abrirse sobre la sesión activa.

Las nuevas generaciones identifican el contrato `sorth-scheduler-v2`: la semilla
desempata candidatos con la misma puntuación sin modificar las prioridades. Con
las mismas entradas, orden, versión y semilla fija, el resultado es reproducible;
semillas diferentes pueden producir el mismo horario. Una semilla no garantiza
el mismo resultado entre v1 y v2. Los horarios guardados no se regeneran al abrir.
Los escenarios sin generación conservan una versión de algoritmo desconocida.
Las revisiones que cambien la semántica del algoritmo deben actualizar ese marcador.
La semilla `None` conserva el modo aleatorio, sin inventar una semilla concreta.
El formato de metadatos es v2 y el contrato de métricas es v1; se serializa un único formato de calendario. Las versiones futuras,
metadatos inválidos o calendario incompatible se rechazan antes de escribir.

## Verificación

Pruebas sintéticas: `test_project_repository.py` y `test_projects.py` cubren
reabrir/duplicar/renombrar, nombres repetidos y Unicode, nombres que parecen rutas,
cancelación, fallos de escritura y rollback compuesto, rechazo de formatos retirados sin mutación,
esquema futuro, conservación de campos extendidos, métricas y advertencias,
localización ES/EN e incompatibilidad previa a cualquier escritura.

La revisión Qt offscreen en Linux no sustituye pruebas nativas de Windows ni una
validación con lector de pantalla. No cerrar el issue solamente por este documento;
registrar el resultado de tests/CI del commit final y los controles no ejecutados.

Consulta [Privacidad y datos locales](../../PRIVACY.md) para ubicaciones, datos
conservados, exportaciones, respaldos y diferencia entre desactivar y borrar.
