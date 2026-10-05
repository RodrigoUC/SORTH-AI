# Importación de Excel en segundo plano

La carga validada es una mejora de seguridad y rendimiento siempre activa. No
requiere activar una función opcional. En Configuración, **Vista previa de cambios
del Excel** está desactivada inicialmente. Activarla añade una revisión explícita
antes del reemplazo; desactivarla mantiene la validación, los avisos existentes y
la confirmación de conflictos con sesiones fijadas.

## Flujo y garantías

1. El selector devuelve inmediatamente a la interfaz. Un único lector captura
   bytes del archivo y valida todas las hojas, encabezados, filas y límites
   existentes. No accede a widgets, a la sesión ni a la base de datos.
2. El usuario puede cancelar, seguir leyendo la interfaz o elegir otro archivo.
   Solo se conserva la última petición pendiente: las lecturas obsoletas nunca
   sustituyen los datos. La edición y la generación quedan bloqueadas hasta
   terminar o cancelar la carga.
3. Los avisos y conflictos de fijaciones conservan su confirmación. Una respuesta
   afirmativa al desfijado todavía no cambia las fijaciones: se aplicará únicamente
   con el reemplazo aceptado y guardado.
4. La vista previa opcional muestra cursos y aulas añadidos, modificados (campos
   anteriores/nuevos) y eliminados; restricciones que se borrarán; asignaciones
   que se borrarán; y sesiones fijadas válidas que se conservarán. No mezcla
   silenciosamente dos sesiones ni ofrece una estrategia de fusión implícita.
5. Antes de guardar se vuelven a leer los bytes. Un archivo cambiado se valida de
   nuevo y vuelve a pasar por las revisiones necesarias. Una modificación durante
   la lectura se rechaza y requiere seleccionar el archivo otra vez. La importación
   representa la última instantánea de bytes validada, no una vinculación viva:
   editar el archivo después de la comprobación final no altera esa instantánea.
6. Se comprueba primero la presentación en controles separados. Después, la
   sesión aceptada y su presentación forman una unidad de trabajo: SQLite no
   confirma hasta que termina la sustitución visible, sin diálogos ni bombeo de
   eventos durante la transacción. Un error de presentación o escritura revierte
   los datos y restaura el estado previo. Si también falla el renderizado de
   recuperación, los datos originales y el archivo se conservan, pero se bloquea
   la edición con una indicación explícita de recuperación pendiente. Cancelar o
   recibir un resultado obsoleto no escribe la sesión. Un historial de cambios,
   si otra extensión lo añade, se reinicia solo tras `_commit_import` exitoso.

Cerrar durante la lectura solicita cancelación y espera mediante el bucle de
eventos; no destruye un QThread en ejecución ni bloquea con `wait()` la interfaz.
La cancelación es cooperativa en lecturas de bytes, límites de hoja y bucles de
filas. pandas/openpyxl no ofrece interrupción dentro de una lectura de hoja: esa
llamada debe terminar antes de liberar el lector o finalizar el cierre. No se
utiliza terminación forzada de hilos. Al cancelar se descarta el resultado aunque
la llamada de terceros todavía continúe.

## Revisión obligatoria de asociaciones por posición

Los identificadores G1, G2 y sus partes divididas dependen del orden de las filas
con el mismo código. Si un curso tiene varios grupos en la versión actual o la
nueva, cambia su cantidad, sus preferencias ordenadas o sus propiedades de sesión,
y tiene recursos asociados o fijaciones, SORTH pide una confirmación adicional.
Esta protección funciona aunque **Vista previa de cambios del Excel** esté
desactivada. También incluye recursos guardados cuyo parámetro esté inactivo.

**Revisar asociaciones del Excel** muestra las propiedades anteriores y propuestas,
los recursos con sus alias e identificadores, su estado activo/inactivo y las
fijaciones afectadas. **Continuar sin reasignar** acepta conservar las asociaciones
compatibles por el mismo identificador; no identifica filas ni traslada personas,
grupos de estudiantes o fijaciones. Después siguen las revisiones habituales de
relaciones eliminadas y fijaciones incompatibles. Cancelar, Escape o Intro con el
detalle enfocado conservan todos los datos. La aceptación no se guarda hasta que
termina la verificación del archivo y la transacción; si cambian los bytes, se
revisa de nuevo el candidato nuevo.

Un cambio intencional de preferencias también puede requerir esta revisión: el
Excel no contiene una identidad estable por fila que permita distinguirlo de un
reordenamiento. Las filas normalizadas idénticas siguen siendo indistinguibles;
intercambiarlas no puede detectarse y no provoca este aviso. Revise manualmente las
asociaciones cuando reorganice grupos idénticos. No se adivinan reasignaciones ni
se cambia el formato del Excel.

## Accesibilidad y localización

Controles nativos y nombres accesibles en ES/EN; Escape y Cancelar conservan la
sesión. Cancelar es la opción predeterminada del resumen, también al pulsar Intro
con el detalle enfocado. Para aceptar, active explícitamente **Reemplazar con este
Excel** mediante clic o llevando el foco a ese botón con Tab y pulsando Intro
o Espacio. El contenido es texto
seleccionable y desplazable; nunca depende solo de colores. La preferencia
Reducir animaciones mantiene un indicador estático. F6 permite leer el estado
completo si la barra de estado es demasiado estrecha. Durante la operación,
**Archivo en importación** muestra por separado el nombre del candidato en un
campo de solo lectura: Tab permite enfocarlo, recorrer un nombre largo y copiarlo.
**Archivo Excel** sigue identificando la sesión aceptada hasta confirmar la
transacción. El estado identifica el archivo y la fase real (espera, lectura y
validación, revisión, comprobación o guardado), sin porcentajes inventados.
Cancelar, rechazar o fallar retira el candidato activo; el último resultado queda
en la barra y en F6. Un fallo nunca conserva un mensaje anterior de éxito. Los diálogos de avisos y
revisión de recursos también identifican el archivo por su nombre. Tab permite
abrir **Mostrar detalles**, entrar al texto completo para seleccionarlo y volver
a los botones; no necesita usar F6 detrás de un diálogo modal. Las capturas Qt offscreen
no prueban anuncios de lectores de pantalla ni apariencia nativa de Windows.

## Medición reproducible y limitación conocida

Desde `project_root`, con dependencias de desarrollo:

```
QT_QPA_PLATFORM=offscreen python tools/benchmark_excel_import.py --output /tmp/import-qa
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

El script genera exclusivamente cursos sintéticos y registra versiones, tiempos,
frecuencia del bucle de eventos y capturas ES/EN. No modifica archivos del usuario.
Los números de referencia están en el informe de evidencia de esta revisión.
Son observaciones de una ejecución Linux/Fusion, no una garantía ni prueba de
rendimiento Windows. No se afirma que QThread acelere el análisis total.

La persistencia y la sustitución final de la tabla Qt siguen siendo sincrónicas
e indivisibles. Con 10.000 cursos distintos se observó ~908 ms para esa fase y
~987 ms como mayor separación entre ticks del bucle; la lectura completa tardó
~6,76 s mientras el temporizador seguía activo. Con 1.000 cursos la fase final
fue ~113 ms, y la carga completa ~583 ms. Iniciar la operación devolvió el control
en ~1 ms en los cuatro tamaños ensayados. Esta limitación es explícita: no se
presenta como una importación totalmente libre de pausas a gran escala. Una
optimización posterior de renderizado debe mantener el reemplazo atómico y no
permitir editar una tabla aplicada parcialmente.

Una segunda ejecución de la misma carga, con menos contención de CPU, observó
~4,45 s totales y ~826 ms de aplicación final para 10.000 cursos (mayor separación
~915 ms). Esta variación es la razón para conservar ambos informes y evitar
atribuir una aceleración algorítmica a estas mediciones.

Evidencia incluida: `docs/evidence/import/measurements-first.json`,
`docs/evidence/import/measurements-repeat.json`, `docs/evidence/import/preview-es.png`,
`docs/evidence/import/preview-en.png`, `docs/evidence/import/loading-en-960.png`.

La revisión de atomicidad añade una previsualización interna de tablas antes de
confirmar. Las mediciones anteriores preceden ese refuerzo; deben repetirse
para comparar la latencia de la versión final. La presentación final sigue
siendo sincrónica y no se afirma ausencia de pausas.

La previsualización interna ahora prepara solo la vista que realmente se aplica:
una importación sin sesiones fijadas vacía el horario, por lo que no construye
una tabla oculta de todas las sesiones pendientes. Con sesiones fijadas conserva
la previsualización del horario parcial, incluidas las razones de pendientes.
La tabla de cursos y las validaciones de dominio y SQL no se omiten; la
presentación real permanece dentro de la transacción antes del commit.

Una comparación secuencial del mismo script y entorno Linux/Fusion, sobre el
commit base `ad4dc28f7fc8a383176b1dd0c5c2b2e3b6d9f85a` y este ajuste,
registró los siguientes tiempos (milisegundos, una observación por tamaño):

| Cursos | Total antes → después | Fase final antes → después | Mayor pausa antes → después |
| --- | --- | --- | --- |
| 100 | 134 → 83 | 72 → 23 | 79 → 35 |
| 1.000 | 928 → 558 | 575 → 238 | 577 → 319 |
| 10.000 | 9.641 → 5.554 | 5.759 → 1.945 | 5.804 → 2.048 |

Informes con versiones y cifras completas:
`docs/evidence/import/measurements-preflight-before.json` y
`docs/evidence/import/measurements-preflight-after.json`. La fase final sigue siendo
sincrónica: la pausa observada de unos dos segundos con 10.000 cursos continúa
siendo una limitación. Esta comparación no certifica rendimiento en Windows ni
predice la latencia con sesiones fijadas, cuya vista parcial sigue preparándose.
