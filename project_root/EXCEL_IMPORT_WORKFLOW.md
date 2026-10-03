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

## Accesibilidad y localización

Controles nativos y nombres accesibles en ES/EN; Escape y Cancelar conservan la
sesión. Cancelar es la opción predeterminada del resumen. El contenido es texto
seleccionable y desplazable; nunca depende solo de colores. La preferencia
Reducir animaciones mantiene un indicador estático. F6 permite leer el estado
completo si la barra de estado es demasiado estrecha. Las capturas Qt offscreen
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

Evidencia incluida: `docs/import/measurements-first.json`,
`docs/import/measurements-repeat.json`, `docs/import/preview-es.png`,
`docs/import/preview-en.png`, `docs/import/loading-en-960.png`.

La revisión de atomicidad añade una previsualización interna de tablas antes de
confirmar. Las mediciones anteriores preceden ese refuerzo; deben repetirse
para comparar la latencia de la versión final. La presentación final sigue
siendo sincrónica y no se afirma ausencia de pausas.
