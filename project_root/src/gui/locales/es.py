"""es presentation catalog. Keep keys stable; edit values to revise wording."""

MESSAGES = {
    'Cancelar generación': 'Cancelar generación',
    'Cancelando generación; se conservarán el horario y las sesiones fijadas.': 'Cancelando generación; se conservarán el horario y las sesiones fijadas.',

    'La generación cambió sesiones fijadas. Se conserva el horario anterior.': 'La generación cambió sesiones fijadas. Se conserva el horario anterior.',
    'La sesión fijada {gid} requiere confirmar una excepción LAB.': 'La sesión fijada {gid} requiere confirmar una excepción LAB.',
    'Sesión fijada': 'Sesión fijada',
    'Desfije la sesión antes de cambiar su asignación.': 'Desfije la sesión antes de cambiar su asignación.',
    'La estructura dividida de {gid} cambió.': 'La estructura dividida de {gid} cambió.',
    'Sesiones fijadas en conflicto': 'Sesiones fijadas en conflicto',
    'Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.': 'Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.',
    'Fijar sesión': 'Fijar sesión',
    'Conservar solo esta sesión al regenerar; no es una preferencia.': 'Conservar solo esta sesión al regenerar; no es una preferencia.',
    'Desfijar sesión': 'Desfijar sesión',
    'Fijada · {state}': 'Fijada · {state}',
    'Desfije las sesiones antes de limpiar el horario.': 'Desfije las sesiones antes de limpiar el horario.',

    'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.': 'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.',
    'Versión del formato': 'Versión del formato',
    'Aula: preferencias pendientes / desconocidas': 'Aula: preferencias pendientes / desconocidas',
    'Hora: preferencias pendientes / desconocidas': 'Hora: preferencias pendientes / desconocidas',
    'Día: preferencias pendientes / desconocidas': 'Día: preferencias pendientes / desconocidas',
    'Valores diferentes (izquierda / derecha)': 'Valores diferentes (izquierda / derecha)',
    'Nombre (1–120 caracteres)': 'Nombre (1–120 caracteres)',
    'Proyectos y escenarios': 'Proyectos y escenarios',
    'Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.': 'Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.',
    'Proyecto': 'Proyecto',
    'Escenario': 'Escenario',
    'Guardado (UTC)': 'Guardado (UTC)',
    'Escenarios guardados': 'Escenarios guardados',
    'Crear proyecto desde la sesión': 'Crear proyecto desde la sesión',
    'Guardar como escenario': 'Guardar como escenario',
    'Abrir escenario': 'Abrir escenario',
    'Duplicar': 'Duplicar',
    'Renombrar': 'Renombrar',
    'Comparar': 'Comparar',
    'Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.': 'Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.',
    'No se pudo completar la operación. El escenario guardado se conserva. {detail}': 'No se pudo completar la operación. El escenario guardado se conserva. {detail}',
    'Escenario guardado. Las ediciones posteriores no cambian esta copia.': 'Escenario guardado. Las ediciones posteriores no cambian esta copia.',
    'Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?': 'Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?',
    'Comparar escenarios': 'Comparar escenarios',
    'Indicadores descriptivos, sin ganador ni puntuación global.': 'Indicadores descriptivos, sin ganador ni puntuación global.',
    'No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.': 'No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.',
    'Cursos': 'Cursos',
    'Aulas': 'Aulas',
    'Restricciones': 'Restricciones',
    'Sesiones fijas': 'Sesiones fijas',
    'Semilla': 'Semilla',
    'Calendario': 'Calendario',
    'Versión del algoritmo': 'Versión del algoritmo',
    'Versión de métricas': 'Versión de métricas',
    'Diferencias: {details}': 'Diferencias: {details}',
    'Ninguna': 'Ninguna',
    'Indicador': 'Indicador',
    'El calendario guardado no es compatible. No se recalcularon indicadores con reglas diferentes.': 'El calendario guardado no es compatible. No se recalcularon indicadores con reglas diferentes.',
    'Sesiones asignadas / total': 'Sesiones asignadas / total',
    'Sesiones pendientes': 'Sesiones pendientes',
    'Preferencia de día: satisfechas / evaluadas': 'Preferencia de día: satisfechas / evaluadas',
    'Preferencia de hora: satisfechas / evaluadas': 'Preferencia de hora: satisfechas / evaluadas',
    'Preferencia de aula: satisfechas / evaluadas': 'Preferencia de aula: satisfechas / evaluadas',
    'Ocupación: minutos-aula / disponibles': 'Ocupación: minutos-aula / disponibles',
    'Excepciones activas': 'Excepciones activas',
    'Docencia, día {day} (min)': 'Docencia, día {day} (min)',
    'No se pudo abrir el catálogo. La sesión actual se conserva. {detail}': 'No se pudo abrir el catálogo. La sesión actual se conserva. {detail}',
    'Cambios posteriores a la copia': 'Cambios posteriores a la copia',
    'Copia guardada': 'Copia guardada',
    '{name} · {state} · {save}': '{name} · {state} · {save}',
    'Ningún archivo seleccionado': 'Ningún archivo seleccionado',
    'El PDF filtrado requiere el total global de asignaciones.': 'El PDF filtrado requiere el total global de asignaciones.',
    'El alcance y el total de asignaciones no coinciden.': 'El alcance y el total de asignaciones no coinciden.',
    'El número de sesiones pendientes no puede ser negativo.': 'El número de sesiones pendientes no puede ser negativo.',
    'El PDF no admite algunos caracteres o escrituras de los datos. Use Excel/CSV para conservarlos.': 'El PDF no admite algunos caracteres o escrituras de los datos. Use Excel/CSV para conservarlos.',
    'Vista filtrada': 'Vista filtrada',
    'Todas las asignaciones': 'Todas las asignaciones',
    'Estado global: pendientes no informados': 'Estado global: pendientes no informados',
    'Horario PARCIAL: {pending} pendientes': 'Horario PARCIAL: {pending} pendientes',
    'Horario completo: 0 pendientes': 'Horario completo: 0 pendientes',
    '{scope} | {count} exportadas de {total} asignadas | {state}': '{scope} | {count} exportadas de {total} asignadas | {state}',
    'SORTH - Horario por aula': 'SORTH - Horario por aula',
    'SORTH {version} | Horario por aula': 'SORTH {version} | Horario por aula',
    'Horas exactas HH:mm | Texto seleccionable | SORTH': 'Horas exactas HH:mm | Texto seleccionable | SORTH',
    'Página {page}': 'Página {page}',
    'Un texto es demasiado largo para la página PDF.': 'Un texto es demasiado largo para la página PDF.',
    'No aplicados (se exportan todas las asignaciones).': 'No aplicados (se exportan todas las asignaciones).',
    'Filtros no informados por el solicitante.': 'Filtros no informados por el solicitante.',
    'Alcance y leyenda': 'Alcance y leyenda',
    'Filtros: {filters}': 'Filtros: {filters}',
    'Un color por curso; los nombres completos aparecen en cada fila. CONFLICTO identifica sesiones simultáneas. EXCEPCIÓN LAB identifica una autorización de aula registrada. Continuación repite día, horas y grupo cuando un nombre ocupa varias páginas. Los pendientes corresponden al horario global, no sólo a esta vista.': 'Un color por curso; los nombres completos aparecen en cada fila. CONFLICTO identifica sesiones simultáneas. EXCEPCIÓN LAB identifica una autorización de aula registrada. Continuación repite día, horas y grupo cuando un nombre ocupa varias páginas. Los pendientes corresponden al horario global, no sólo a esta vista.',
    'Día no válido para {group}.': 'Día no válido para {group}.',
    'Sin sesiones asignadas en este alcance.': 'Sin sesiones asignadas en este alcance.',
    'Aula: {room} | Sesiones: {count}': 'Aula: {room} | Sesiones: {count}',
    'El nombre del aula es demasiado largo para el encabezado PDF.': 'El nombre del aula es demasiado largo para el encabezado PDF.',
    'Inicio - Fin': 'Inicio - Fin',
    'Nombre completo del curso': 'Nombre completo del curso',
    'Avisos': 'Avisos',
    'CONFLICTO': 'CONFLICTO',
    'EXCEPCIÓN LAB': 'EXCEPCIÓN LAB',
    '(Sin nombre de curso)': '(Sin nombre de curso)',
    'Continuación': 'Continuación',
    'Buscar': 'Buscar',
    '(sin búsqueda)': '(sin búsqueda)',
    'Guardar el horario generado en Excel (.xlsx), CSV o PDF.\nEl Excel incluye una grilla visual; el PDF, tablas por aula para imprimir.': 'Guardar el horario generado en Excel (.xlsx), CSV o PDF.\nEl Excel incluye una grilla visual; el PDF, tablas por aula para imprimir.',
    "Archivos Excel (*.xlsx);;Archivos CSV (*.csv);;Documentos PDF (*.pdf)": 'Archivos Excel (*.xlsx);;Archivos CSV (*.csv);;Documentos PDF (*.pdf)',
    'El libro supera el límite de importación. Divídalo en archivos más pequeños.': 'El libro supera el límite de importación. Divídalo en archivos más pequeños.',
    '⚠️ Horario parcial: {p1}/{p3} grupos; {pending} pendientes': '⚠️ Horario parcial: {p1}/{p3} grupos; {pending} pendientes',
    'Sin resultado': 'Sin resultado',
    'No se obtuvo un resultado. Revise los datos y vuelva a generar el horario.': 'No se obtuvo un resultado. Revise los datos y vuelva a generar el horario.',

    '{scope} · horario parcial, {pending} pendientes': '{scope} · horario parcial, {pending} pendientes',
    '{gid}: identificador de grupo duplicado': '{gid}: identificador de grupo duplicado',
    '{gid}: asignación mal formada': '{gid}: asignación mal formada',
    'Exportar todas las asignaciones': 'Exportar todas las asignaciones',
    'todas las asignaciones': 'todas las asignaciones',

    "\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.": "\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.",
    "\n⚠️  {p1} grupo(s) sin asignar.\nRevisa la Lista Detallada (marcados en rojo).": "\n⚠️  {p1} grupo(s) sin asignar.\nRevisa la Lista Detallada (marcados en rojo).",
    "  {p1}  {p3}": "  {p1}  {p3}",
    "  ·  Cargue un Excel para comenzar": "  ·  Cargue un Excel para comenzar",
    "  ·  Listo para generar": "  ·  Listo para generar",
    "  ·  {p1}/{p3} sesiones asignadas": "  ·  {p1}/{p3} sesiones asignadas",
    "  ⚠️  {p1}": "  ⚠️  {p1}",
    "  💾  Sesión anterior encontrada": "  💾  Sesión anterior encontrada",
    " Consulte las sesiones sin asignar en Lista detallada.": " Consulte las sesiones sin asignar en Lista detallada.",
    " · {p1} tramo(s) con conflicto": " · {p1} tramo(s) con conflicto",
    "&Aula:": "&Aula:",
    "&Buscar:": "&Buscar:",
    "&Día:": "&Día:",
    "&Estado:": "&Estado:",
    "(Sin preferencia)": "(Sin preferencia)",
    ". No hay coincidencias; cambie o restablezca los filtros.": ". No hay coincidencias; cambie o restablezca los filtros.",
    "1. Cargue un Excel con las hojas Aulas y Cursos (nombres exactos).\n2. Revise los cursos y configure aulas o restricciones.\n3. Genere el horario, revise los grupos pendientes y exporte.": "1. Cargue un Excel con las hojas Aulas y Cursos (nombres exactos).\n2. Revise los cursos y configure aulas o restricciones.\n3. Genere el horario, revise los grupos pendientes y exporte.",
    "Abrir": "Abrir",
    "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: # DE AULA y CAPACIDAD (entero ≥ 0)\n  • Cursos: Curso; cada fila es un grupo sugerido\nOpcionales: Nombre de Curso, Horas (0800-1055), Aula y Días (L,I,M,J,V,S).\nLos encabezados van en la fila 1; el orden de columnas no importa.": "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: # DE AULA y CAPACIDAD (entero ≥ 0)\n  • Cursos: Curso; cada fila es un grupo sugerido\nOpcionales: Nombre de Curso, Horas (0800-1055), Aula y Días (L,I,M,J,V,S).\nLos encabezados van en la fila 1; el orden de columnas no importa.",
    "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: código, descripción, campus, capacidad\n  • Cursos: cada fila es un grupo sugerido": "Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: código, descripción, campus, capacidad\n  • Cursos: cada fila es un grupo sugerido",
    "Aceptar": "Aceptar",
    "Activar hora preferida": "Activar hora preferida",
    "Activar para usar una semilla aleatoria en cada generación": "Activar para usar una semilla aleatoria en cada generación",
    "Active un aula para restringirla. Luego marque los cursos que pueden usarla (los desmarcados quedan libres).": "Active un aula para restringirla. Luego marque los cursos que pueden usarla (los desmarcados quedan libres).",
    "Advertencia": "Advertencia",
    "Agregar Aula": "Agregar Aula",
    "Agregar Curso": "Agregar Curso",
    "Agregar aula": "Agregar aula",
    "Agregar un aula nueva a la sesión actual.\nÚtil para aulas que no están en el Excel pero deben estar disponibles.": "Agregar un aula nueva a la sesión actual.\nÚtil para aulas que no están en el Excel pero deben estar disponibles.",
    "Agregar un nuevo curso manualmente a la lista": "Agregar un nuevo curso manualmente a la lista",
    "Aleatoria": "Aleatoria",
    "Archivo Excel:": "Archivo Excel:",
    "Asignaciones ordenadas por aula": "Asignaciones ordenadas por aula",
    "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual.": "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual.",
    "Asignado": "Asignado",
    "Asignados": "Asignados",
    "Asignar": "Asignar",
    "Asignar manualmente": "Asignar manualmente",
    "Asignar sesión manualmente": "Asignar sesión manualmente",
    "Aula": "Aula",
    "Aula Sugerida": "Aula Sugerida",
    "Aula Sugerida:": "Aula Sugerida:",
    "Aula de la &cuadrícula:": "Aula de la &cuadrícula:",
    "Aula de la cuadrícula": "Aula de la cuadrícula",
    "Aulas con Restricciones": "Aulas con Restricciones",
    "Aulas utilizadas": "Aulas utilizadas",
    "Aulas utilizadas:    {p1}": "Aulas utilizadas:    {p1}",
    "Aulas, fila {row}: '{room}' no tiene capacidad; se usará 0.": "Aulas, fila {row}: '{room}' no tiene capacidad; se usará 0.",
    "Aulas, fila {row}: CAPACIDAD debe ser un entero mayor o igual a 0.": "Aulas, fila {row}: CAPACIDAD debe ser un entero mayor o igual a 0.",
    "Aulas, fila {row}: el aula '{room}' está duplicada.": "Aulas, fila {row}: el aula '{room}' está duplicada.",
    "Aulas, fila {row}: falta # DE AULA.": "Aulas, fila {row}: falta # DE AULA.",
    "Aulas:": "Aulas:",
    "Aulas: agregue al menos un aula con # DE AULA.": "Aulas: agregue al menos un aula con # DE AULA.",
    "Automático (dividir si > 4.5h)": "Automático (dividir si > 4.5h)",
    "Automático: se divide solo si la duración supera 4.5 horas.\nForzar división: siempre se divide en bloques de 2h en días distintos.\nNo dividir: se asigna completo en un solo día sin importar la duración.": "Automático: se divide solo si la duración supera 4.5 horas.\nForzar división: siempre se divide en bloques de 2h en días distintos.\nNo dividir: se asigna completo en un solo día sin importar la duración.",
    "Avisos del archivo: {count}": "Avisos del archivo: {count}",
    "Aún no hay cursos. Cargue un Excel o agregue su primer curso.": "Aún no hay cursos. Cargue un Excel o agregue su primer curso.",
    "Buscar cursos": "Buscar cursos",
    "Buscar en todo el horario": "Buscar en todo el horario",
    "Buscar por código o nombre de curso…": "Buscar por código o nombre de curso…",
    "Cambiar idioma sin modificar los datos ni los formatos de exportación": "Cambiar idioma sin modificar los datos ni los formatos de exportación",
    "Cambios sin guardar": "Cambios sin guardar",
    "Campus:": "Campus:",
    "Cancelar": "Cancelar",
    "Capacidad *:": "Capacidad *:",
    "Cargar Excel": "Cargar Excel",
    "Cargue un Excel o agregue al menos un aula primero.": "Cargue un Excel o agregue al menos un aula primero.",
    "Cargue un Excel o agregue cursos y aulas para comenzar.": "Cargue un Excel o agregue cursos y aulas para comenzar.",
    "Cerrar": "Cerrar",
    "Configurar qué aulas están reservadas exclusivamente para ciertos cursos.\nLos cursos restringidos SOLO pueden asignarse a su aula designada.": "Configurar qué aulas están reservadas exclusivamente para ciertos cursos.\nLos cursos restringidos SOLO pueden asignarse a su aula designada.",
    "Confirmar": "Confirmar",
    "Confirmar eliminación": "Confirmar eliminación",
    "Confirmar excepción de laboratorio": "Confirmar excepción de laboratorio",
    "Conflicto de aula\n": "Conflicto de aula\n",
    "Controla la aleatoriedad del algoritmo.\nSemilla fija → mismo horario cada vez (reproducible).\nSemilla aleatoria → resultados distintos en cada ejecución.": "Controla la aleatoriedad del algoritmo.\nSemilla fija → mismo horario cada vez (reproducible).\nSemilla aleatoria → resultados distintos en cada ejecución.",
    "Corrija el archivo y vuelva a cargarlo:": "Corrija el archivo y vuelva a cargarlo:",
    "Cuadrícula por aula": "Cuadrícula por aula",
    "Cuadrícula semanal por aula": "Cuadrícula semanal por aula",
    "Curso ya existe": "Curso ya existe",
    "Cursos a programar": "Cursos a programar",
    "Cursos para {p1}:": "Cursos para {p1}:",
    "Cursos programados": "Cursos programados",
    "Cursos programados:  {p1}": "Cursos programados:  {p1}",
    "Cursos, fila {row}: Días admite L, I, M, J, V, S separados por comas; I=martes y M=miércoles.": "Cursos, fila {row}: Días admite L, I, M, J, V, S separados por comas; I=martes y M=miércoles.",
    "Cursos, fila {row}: Horas debe ser HHMM-HHMM, con fin posterior al inicio (ej. 0800-1055).": "Cursos, fila {row}: Horas debe ser HHMM-HHMM, con fin posterior al inicio (ej. 0800-1055).",
    "Cursos, fila {row}: el aula '{room}' no aparece en Aulas; se importará sin esa preferencia.": "Cursos, fila {row}: el aula '{room}' no aparece en Aulas; se importará sin esa preferencia.",
    "Cursos, fila {row}: falta Curso (código).": "Cursos, fila {row}: falta Curso (código).",
    "Cursos: agregue al menos una fila con Curso (código).": "Cursos: agregue al menos una fila con Curso (código).",
    "Código": "Código",
    "Código *:": "Código *:",
    "Código del Curso:": "Código del Curso:",
    "Código, nombre de curso, grupo o aula": "Código, nombre de curso, grupo o aula",
    "Datos actualizados. Genere un nuevo horario para exportar.": "Datos actualizados. Genere un nuevo horario para exportar.",
    "Dejar la sesión seleccionada sin asignar": "Dejar la sesión seleccionada sin asignar",
    "Desactiva las transiciones y el indicador animado.": "Desactiva las transiciones y el indicador animado.",
    "Descartar": "Descartar",
    "Descripción:": "Descripción:",
    "Desmarcar todos": "Desmarcar todos",
    "Detectado automáticamente por el código (L al inicio → LAB).\nPuedes cambiarlo manualmente si es necesario.": "Detectado automáticamente por el código (L al inicio → LAB).\nPuedes cambiarlo manualmente si es necesario.",
    "División en días:": "División en días:",
    "Domingo": "Domingo",
    "Duplicado": "Duplicado",
    "Duración": "Duración",
    "Duración:": "Duración:",
    "Día": "Día",
    "Día Preferido": "Día Preferido",
    "Día Preferido:": "Día Preferido:",
    "Editar Curso": "Editar Curso",
    "Editar curso": "Editar curso",
    "Editar curso {p1}": "Editar curso {p1}",
    "Editar el curso de la sesión seleccionada; será necesario generar de nuevo": "Editar el curso de la sesión seleccionada; será necesario generar de nuevo",
    "Editar el curso seleccionado en la tabla": "Editar el curso seleccionado en la tabla",
    "Ej: Aula General": "Ej: Aula General",
    "Ej: Biología General (opcional)": "Ej: Biología General (opcional)",
    "Ej: HO": "Ej: HO",
    "Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.": "Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.",
    "El aula '{p1}' ya existe.": "El aula '{p1}' ya existe.",
    "El curso '{p1}' ya existe en la lista.\n¿Deseas modificarlo en su lugar?": "El curso '{p1}' ya existe en la lista.\n¿Deseas modificarlo en su lugar?",
    "El curso {p1} no se encuentra en la lista de cursos.": "El curso {p1} no se encuentra en la lista de cursos.",
    "El código del aula es obligatorio.": "El código del aula es obligatorio.",
    "El código del curso es obligatorio.": "El código del curso es obligatorio.",
    "Eliminar el curso seleccionado de la lista": "Eliminar el curso seleccionado de la lista",
    "Eliminar todas las asignaciones del horario actual": "Eliminar todas las asignaciones del horario actual",
    "Eliminar todos los cursos de la lista": "Eliminar todos los cursos de la lista",
    "En curso": "En curso",
    "Error": "Error",
    "Error al cargar archivo Excel:\n{p1}": "Error al cargar archivo Excel:\n{p1}",
    "Error al exportar:\n{p1}": "Error al exportar:\n{p1}",
    "Error al generar el horario:\n{p1}": "Error al generar el horario:\n{p1}",
    "Espere a que termine la generación antes de cerrar.": "Espere a que termine la generación antes de cerrar.",
    "Estado": "Estado",
    "Estado de guardado": "Estado de guardado",
    "Excepción manual LAB": "Excepción manual LAB",
    "Excepción manual confirmada: laboratorio en aula regular.": "Excepción manual confirmada: laboratorio en aula regular.",
    "Exportar completo": "Exportar completo",
    "Exportar completo incluye todas las asignaciones. Exportar filtrado usa Buscar, Aula, Día y Estado; no el aula de la cuadrícula.": "Los archivos contienen sesiones asignadas. Exportar filtrado usa Buscar, Aula, Día y Estado; no el aula de la cuadrícula.",
    "Exportar filtrado (0)": "Exportar filtrado (0)",
    "Exportar filtrado ({p1})": "Exportar filtrado ({p1})",
    "Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.": "Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.",
    "Faltan las hojas: {missing}. Use esos nombres exactos. Hojas encontradas: {found}": "Faltan las hojas: {missing}. Use esos nombres exactos. Hojas encontradas: {found}",
    "Filtrar por aula": "Filtrar por aula",
    "Filtrar por día": "Filtrar por día",
    "Filtrar por estado": "Filtrar por estado",
    "Fin": "Fin",
    "Forzar división en varios días": "Forzar división en varios días",
    "Generando…": "Generando…",
    "Generar horario": "Generar horario",
    "Genere un horario para consultar sus sesiones y exportar los resultados.": "Genere un horario para consultar sus sesiones y exportar los resultados.",
    "Grupo": "Grupo",
    "Grupo / sesión": "Grupo / sesión",
    "Grupos": "Grupos",
    "Grupos asignados:    {p1} / {p3}": "Grupos asignados:    {p1} / {p3}",
    "Guardar": "Guardar",
    "Guardar el horario generado en formato Excel (.xlsx) o CSV.\nEl Excel incluye una grilla visual por aula.": "Guardar el horario generado en formato Excel (.xlsx) o CSV.\nEl Excel incluye una grilla visual por aula.",
    "Guardar horario {p1} · {p3} sesiones": "Guardar horario {p1} · {p3} sesiones",
    "Guía rápida": "Guía rápida",
    "Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.": "Hoja {sheet}, fila 1: columnas duplicadas: {columns}. Deje una sola columna de cada tipo.",
    "Hoja {sheet}, fila 1: falta la columna {columns}. Revise el encabezado.": "Hoja {sheet}, fila 1: falta la columna {columns}. Revise el encabezado.",
    "Hoja {sheet}: agregue los encabezados en la fila 1.": "Hoja {sheet}: agregue los encabezados en la fila 1.",
    "Hora": "Hora",
    "Hora Preferida": "Hora Preferida",
    "Hora Preferida:": "Hora Preferida:",
    "Hora de inicio preferida para este curso (ej: 08:00, 13:00)": "Hora de inicio preferida para este curso (ej: 08:00, 13:00)",
    "Horario eliminado.": "Horario eliminado.",
    "Horario no válido": "Horario no válido",
    "Horario {p1}: {p3} sesiones exportadas a {p5}": "Horario {p1}: {p3} sesiones exportadas a {p5}",
    "Horario {p1}: {p3} sesiones exportadas a:\n{p5}": "Horario {p1}: {p3} sesiones exportadas a:\n{p5}",
    "Idioma de la interfaz": "Idioma de la interfaz",
    "Idioma:": "Idioma:",
    "Importar con avisos": "Importar con avisos",
    "Info": "Info",
    "Inicio": "Inicio",
    "Jueves": "Jueves",
    "La búsqueda automática no encontró un horario compatible con las asignaciones actuales. Esto no demuestra que sea imposible; revise horarios, restricciones o asigne manualmente.": "La búsqueda automática no encontró un horario compatible con las asignaciones actuales. Esto no demuestra que sea imposible; revise horarios, restricciones o asigne manualmente.",
    "La duración no cabe en el horario permitido sin cruzar el almuerzo.": "La duración no cabe en el horario permitido sin cruzar el almuerzo.",
    "Las restricciones de cursos excluyen todas las aulas compatibles.": "Las restricciones de cursos excluyen todas las aulas compatibles.",
    "Libro de Excel (*.xlsx)": "Libro de Excel (*.xlsx)",
    "Limpiar horario": "Limpiar horario",
    "Lista detallada": "Lista detallada",
    "Lista detallada del horario": "Lista detallada del horario",
    "Listo. Cargue un archivo Excel para comenzar.": "Listo. Cargue un archivo Excel para comenzar.",
    "Lunes": "Lunes",
    "Marcar todos": "Marcar todos",
    "Martes": "Martes",
    "Miércoles": "Miércoles",
    "Mostrando {p1} de {p3} sesiones": "Mostrando {p1} de {p3} sesiones",
    "Mostrando {p1} de {p3} sesión": "Mostrando {p1} de {p3} sesión",
    "Motivo y excepciones de la sesión seleccionada": "Motivo y excepciones de la sesión seleccionada",
    "Ningún aula del tipo permitido tiene capacidad suficiente.": "Ningún aula del tipo permitido tiene capacidad suficiente.",
    "No": "No",
    "No dividir (asignar en un solo día)": "No dividir (asignar en un solo día)",
    "No hay aulas con cursos asociados en el Excel.": "No hay aulas con cursos asociados en el Excel.",
    "No hay horario para exportar.": "No hay horario para exportar.",
    "No hay laboratorios configurados. Puede elegir un aula regular manualmente y confirmar la excepción.": "No hay laboratorios configurados. Puede elegir un aula regular manualmente y confirmar la excepción.",
    "No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.": "No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.",
    "No se cargó el archivo. La sesión anterior se conserva.": "No se cargó el archivo. La sesión anterior se conserva.",
    "No se encontró el archivo. Selecciónelo nuevamente.": "No se encontró el archivo. Selecciónelo nuevamente.",
    "No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.": "No se pudo abrir el archivo. Revise sus permisos o guarde una copia .xlsx.",
    "No se pudo generar un horario válido.\n\nPosibles causas:\n  • No hay suficientes aulas disponibles\n  • Restricciones demasiado estrictas\n  • Conflictos de horario entre cursos": "No se pudo generar un horario válido.\n\nPosibles causas:\n  • No hay suficientes aulas disponibles\n  • Restricciones demasiado estrictas\n  • Conflictos de horario entre cursos",
    "No se pudo guardar la sesión. Si sales, perderás los cambios sin guardar.\nEl último guardado y las copias existentes se conservarán.\n\n{p1}": "No se pudo guardar la sesión. Si sales, perderás los cambios sin guardar.\nEl último guardado y las copias existentes se conservarán.\n\n{p1}",
    "No se pudo guardar la sesión: {p1}": "No se pudo guardar la sesión: {p1}",
    "No se pudo guardar o recuperar la sesión: {p1}": "No se pudo guardar o recuperar la sesión: {p1}",
    "No se pudo leer el libro. Ábralo en Excel y guarde una copia .xlsx sin contraseña.": "No se pudo leer el libro. Ábralo en Excel y guarde una copia .xlsx sin contraseña.",
    "Nombre": "Nombre",
    "Nombre del curso": "Nombre del curso",
    "Nombre:": "Nombre:",
    "Número de Grupos:": "Número de Grupos:",
    "Organización de horarios académicos": "Organización de horarios académicos",
    "Por aula": "Por aula",
    "Por favor agregue al menos un curso.": "Por favor agregue al menos un curso.",
    "Quitar del horario": "Quitar del horario",
    "Quitar sesión del horario": "Quitar sesión del horario",
    "Recuperación pendiente": "Recuperación pendiente",
    "Reducir animaciones": "Reducir animaciones",
    "Reintentar": "Reintentar",
    "Restablecer filtros": "Restablecer filtros",
    "Restricciones de aulas": "Restricciones de aulas",
    "Restricciones de aulas eliminadas.": "Restricciones de aulas eliminadas.",
    "Resultado de validación": "Resultado de validación",
    "Resumen del Horario": "Resumen del Horario",
    "Revisar importación": "Revisar importación",
    "SORTH - Sistema de Organización de Horarios": "SORTH - Sistema de Organización de Horarios",
    "Se encontró una sesión guardada.\n¿Deseas restaurarla?": "Se encontró una sesión guardada.\n¿Deseas restaurarla?",
    "Seleccionar archivo Excel": "Seleccionar archivo Excel",
    "Seleccione el aula, día y hora. Se comprobarán todas las restricciones.": "Seleccione el aula, día y hora. Se comprobarán todas las restricciones.",
    "Seleccione un aula": "Seleccione un aula",
    "Seleccione un aula.": "Seleccione un aula.",
    "Seleccione un curso para editar.": "Seleccione un curso para editar.",
    "Seleccione un curso para eliminar.": "Seleccione un curso para eliminar.",
    "Seleccione una fila para editar o quitar.": "Seleccione una fila para editar o quitar.",
    "Semilla:": "Semilla:",
    "Sesiones asignadas": "Sesiones asignadas",
    "Sesiones por aula": "Sesiones por aula",
    "Sesiones por día": "Sesiones por día",
    "Sesiones sin asignar (ver Lista detallada)": "Sesiones sin asignar (ver Lista detallada)",
    "Sesión anterior": "Sesión anterior",
    "Sesión no disponible": "Sesión no disponible",
    "Sin archivo seleccionado": "Sin archivo seleccionado",
    "Sin asignar": "Sin asignar",
    "Sin cambios pendientes": "Sin cambios pendientes",
    "Sin coincidencias": "Sin coincidencias",
    "Sin sesiones para esta aula y estos filtros.": "Sin sesiones para esta aula y estos filtros.",
    "Sin solución": "Sin solución",
    "Sábado": "Sábado",
    "Sí": "Sí",
    "Tipo de Sala:": "Tipo de Sala:",
    "Tipo de sala:": "Tipo de sala:",
    "Todas": "Todas",
    "Todos": "Todos",
    "Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).": "Use un archivo .xlsx. En Excel, elija Guardar como → Libro de Excel (.xlsx).",
    "Valor de semilla fija para resultados reproducibles": "Valor de semilla fija para resultados reproducibles",
    "Valor: ": "Valor: ",
    "Ver resumen": "Ver resumen",
    "Ver, agregar, editar y eliminar los cursos a programar": "Ver, agregar, editar y eliminar los cursos a programar",
    "Viernes": "Viernes",
    "Visualizar el horario generado en lista, cuadrícula o por aula": "Visualizar el horario generado en lista, cuadrícula o por aula",
    "classroom_count": {
        "one": "{n} aula",
        "other": "{n} aulas"
    },
    "completo": "completo",
    "course_count": {
        "one": "{n} curso",
        "other": "{n} cursos"
    },
    "filtrado": "filtrado",
    "placeholder.classroom_code": "Ej: A-DEMO-1, L-DEMO-1",
    "placeholder.course_code": "Ej: DEM101, DEM111L",
    "placeholder.preferred_classroom": "Ej: A-DEMO-1, L-DEMO-1 (opcional)",
    "result_count": {
        "one": "Mostrando {visible} de {n} sesión",
        "other": "Mostrando {visible} de {n} sesiones"
    },
    "session_count": {
        "one": "{n} sesión",
        "other": "{n} sesiones"
    },
    "{gid}: capacidad insuficiente": "{gid}: capacidad insuficiente",
    "{gid}: conflicto de aula": "{gid}: conflicto de aula",
    "{gid}: duración incorrecta": "{gid}: duración incorrecta",
    "{gid}: grupo o aula desconocido": "{gid}: grupo o aula desconocido",
    "{gid}: horario fuera del intervalo permitido": "{gid}: horario fuera del intervalo permitido",
    "{gid}: requiere laboratorio; falta confirmar la excepción manual": "{gid}: requiere laboratorio; falta confirmar la excepción manual",
    "{gid}: restricción de aula": "{gid}: restricción de aula",
    "{gid}: sesiones divididas deben usar días distintos y la misma hora": "{gid}: sesiones divididas deben usar días distintos y la misma hora",
    "{n} aula": "{n} aula",
    "{n} aulas": "{n} aulas",
    "{n} curso": "{n} curso",
    "{n} cursos": "{n} cursos",
    "{n} sesiones": "{n} sesiones",
    "{n} sesión": "{n} sesión",
    "{p0} cursos  ·  {p2} sesiones  ·  {p4} aulas": "{p0} cursos  ·  {p2} sesiones  ·  {p4} aulas",
    "{p0} requiere laboratorio. ¿Asignarlo al aula regular {p2}?\nEsta excepción manual quedará registrada en la sesión.": "{p0} requiere laboratorio. ¿Asignarlo al aula regular {p2}?\nEsta excepción manual quedará registrada en la sesión.",
    "{p0} sesiones asignadas · {p2} sin asignar · {p4} aulas utilizadas": "{p0} sesiones asignadas · {p2} sin asignar · {p4} aulas utilizadas",
    "{p0} sesiones{p2}. Horas exactas en cada bloque; detalle completo al señalarlo.": "{p0} sesiones{p2}. Horas exactas en cada bloque; detalle completo al señalarlo.",
    "{p0} · {p2} min · {p4} estudiantes": "{p0} · {p2} min · {p4} estudiantes",
    "¿Eliminar el curso {p1}?": "¿Eliminar el curso {p1}?",
    "¿Eliminar todas las asignaciones del horario actual?\nSe conservarán los cursos y las aulas para generar un horario nuevo.": "¿Eliminar todas las asignaciones del horario actual?\nSe conservarán los cursos y las aulas para generar un horario nuevo.",
    "¿Eliminar todos los cursos de la lista?\nEsta acción no se puede deshacer.": "¿Eliminar todos los cursos de la lista?\nEsta acción no se puede deshacer.",
    "¿Quitar {p1} del horario?\nLa sesión quedará sin asignar y no se exportará.": "¿Quitar {p1} del horario?\nLa sesión quedará sin asignar y no se exportará.",
    "Éxito": "Éxito",
    "… y {count} errores más.": "… y {count} errores más.",
    "⏳ Generando horario...": "⏳ Generando horario...",
    "⚠️ No se pudo restaurar la sesión: {p1}": "⚠️ No se pudo restaurar la sesión: {p1}",
    "✅ Aula '{p1}' agregada ({p3}, cap={p5})": "✅ Aula '{p1}' agregada ({p3}, cap={p5})",
    "✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)": "✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)",
    "✅ Horario generado: {p1}/{p3} grupos": "✅ Horario generado: {p1}/{p3} grupos",
    "✅ Sesión restaurada correctamente.": "✅ Sesión restaurada correctamente.",
    "✅ {p1} aula(s) con restricciones configuradas.": "✅ {p1} aula(s) con restricciones configuradas.",
    "✏️ Editar": "✏️ Editar",
    "❌ Error al generar horario": "❌ Error al generar horario",
    "❌ No se pudo generar el horario": "❌ No se pudo generar el horario",
    "➕ Agregar Curso": "➕ Agregar Curso",
    "🏫 REGULAR (detectado automáticamente)": "🏫 REGULAR (detectado automáticamente)",
    "📅 Horario Generado": "📅 Horario Generado",
    "📚 Gestión de Cursos": "📚 Gestión de Cursos",
    "🔒 Aulas con Restricciones": "🔒 Aulas con Restricciones",
    "🔒 Restricciones ({p1})": "🔒 Restricciones ({p1})",
    "🔬 LAB (detectado automáticamente)": "🔬 LAB (detectado automáticamente)",
    "🗑️ Eliminar": "🗑️ Eliminar",
    "🧹 Limpiar Todo": "🧹 Limpiar Todo"
}

QT_MESSAGES = {
    'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.': 'El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.',
    'Versión del formato': 'Versión del formato',
    'Aula: preferencias pendientes / desconocidas': 'Aula: preferencias pendientes / desconocidas',
    'Hora: preferencias pendientes / desconocidas': 'Hora: preferencias pendientes / desconocidas',
    'Día: preferencias pendientes / desconocidas': 'Día: preferencias pendientes / desconocidas',
    'Valores diferentes (izquierda / derecha)': 'Valores diferentes (izquierda / derecha)',
    "&Cancel": "&Cancelar",
    "&Close": "&Cerrar",
    "&Copy": "&Copiar",
    "&Delete": "&Eliminar",
    "&Discard": "&Descartar",
    "&No": "&No",
    "&OK": "&Aceptar",
    "&Open": "&Abrir",
    "&Paste": "&Pegar",
    "&Redo": "&Rehacer",
    "&Retry": "&Reintentar",
    "&Save": "&Guardar",
    "&Select All": "&Seleccionar todo",
    "&Undo": "&Deshacer",
    "&Yes": "&Sí",
    "Cancel": "Cancelar",
    "Clear": "Limpiar",
    "Clear contents": "Limpiar contenido",
    "Close": "Cerrar",
    "Copy": "Copiar",
    "Cu&t": "Cor&tar",
    "Cut": "Cortar",
    "Delete": "Eliminar",
    "Discard": "Descartar",
    "Hide Details...": "Ocultar detalles...",
    "No": "No",
    "OK": "Aceptar",
    "Open": "Abrir",
    "Paste": "Pegar",
    "Redo": "Rehacer",
    "Retry": "Reintentar",
    "Save": "Guardar",
    "Select All": "Seleccionar todo",
    "Show Details...": "Mostrar detalles...",
    "Undo": "Deshacer",
    "Yes": "Sí"
}

# Explainable schedule quality indicators.
MESSAGES.update({'No aplica': 'No aplica',
 'Calidad del horario completo': 'Calidad del horario completo',
 'Los filtros no cambian estos indicadores. Son descriptivos: no validan restricciones ni demuestran un óptimo.': 'Los '
                                                                                                                  'filtros '
                                                                                                                  'no '
                                                                                                                  'cambian '
                                                                                                                  'estos '
                                                                                                                  'indicadores. '
                                                                                                                  'Son '
                                                                                                                  'descriptivos: '
                                                                                                                  'no '
                                                                                                                  'validan '
                                                                                                                  'restricciones '
                                                                                                                  'ni '
                                                                                                                  'demuestran '
                                                                                                                  'un '
                                                                                                                  'óptimo.',
 'Grupos originales: {complete} completos, {partial} parciales, {pending} pendientes y {unknown} desconocidos, de {total}. Las preferencias cuentan cada sesión dividida por separado.': 'Grupos '
                                                                                                                                                                                         'originales: '
                                                                                                                                                                                         '{complete} '
                                                                                                                                                                                         'completos, '
                                                                                                                                                                                         '{partial} '
                                                                                                                                                                                         'parciales, '
                                                                                                                                                                                         '{pending} '
                                                                                                                                                                                         'pendientes '
                                                                                                                                                                                         'y '
                                                                                                                                                                                         '{unknown} '
                                                                                                                                                                                         'desconocidos, '
                                                                                                                                                                                         'de '
                                                                                                                                                                                         '{total}. '
                                                                                                                                                                                         'Las '
                                                                                                                                                                                         'preferencias '
                                                                                                                                                                                         'cuentan '
                                                                                                                                                                                         'cada '
                                                                                                                                                                                         'sesión '
                                                                                                                                                                                         'dividida '
                                                                                                                                                                                         'por '
                                                                                                                                                                                         'separado.',
 'Día preferido': 'Día preferido',
 'Hora preferida': 'Hora preferida',
 'Aula preferida': 'Aula preferida',
 'Preferencia': 'Preferencia',
 'Pendientes': 'Pendientes',
 'Desconocidas': 'Desconocidas',
 'Sin preferencia': 'Sin preferencia',
 'Coincidencia exacta de día, hora de inicio y aula. El denominador incluye sólo preferencias asignadas y conocidas; pendientes, desconocidas y ausentes se muestran aparte. Sin denominador: no aplica.': 'Coincidencia '
                                                                                                                                                                                                           'exacta '
                                                                                                                                                                                                           'de '
                                                                                                                                                                                                           'día, '
                                                                                                                                                                                                           'hora '
                                                                                                                                                                                                           'de '
                                                                                                                                                                                                           'inicio '
                                                                                                                                                                                                           'y '
                                                                                                                                                                                                           'aula. '
                                                                                                                                                                                                           'El '
                                                                                                                                                                                                           'denominador '
                                                                                                                                                                                                           'incluye '
                                                                                                                                                                                                           'sólo '
                                                                                                                                                                                                           'preferencias '
                                                                                                                                                                                                           'asignadas '
                                                                                                                                                                                                           'y '
                                                                                                                                                                                                           'conocidas; '
                                                                                                                                                                                                           'pendientes, '
                                                                                                                                                                                                           'desconocidas '
                                                                                                                                                                                                           'y '
                                                                                                                                                                                                           'ausentes '
                                                                                                                                                                                                           'se '
                                                                                                                                                                                                           'muestran '
                                                                                                                                                                                                           'aparte. '
                                                                                                                                                                                                           'Sin '
                                                                                                                                                                                                           'denominador: '
                                                                                                                                                                                                           'no '
                                                                                                                                                                                                           'aplica.',
 'Distribución de carga por día': 'Distribución de carga por día',
 'Minutos de docencia': 'Minutos de docencia',
 'Se suman minutos de cada sesión, incluso si son simultáneas. Se incluyen días sin carga; no se presupone que una distribución uniforme sea mejor.': 'Se '
                                                                                                                                                      'suman '
                                                                                                                                                      'minutos '
                                                                                                                                                      'de '
                                                                                                                                                      'cada '
                                                                                                                                                      'sesión, '
                                                                                                                                                      'incluso '
                                                                                                                                                      'si '
                                                                                                                                                      'son '
                                                                                                                                                      'simultáneas. '
                                                                                                                                                      'Se '
                                                                                                                                                      'incluyen '
                                                                                                                                                      'días '
                                                                                                                                                      'sin '
                                                                                                                                                      'carga; '
                                                                                                                                                      'no '
                                                                                                                                                      'se '
                                                                                                                                                      'presupone '
                                                                                                                                                      'que '
                                                                                                                                                      'una '
                                                                                                                                                      'distribución '
                                                                                                                                                      'uniforme '
                                                                                                                                                      'sea '
                                                                                                                                                      'mejor.',
 'Ocupación temporal de aulas': 'Ocupación temporal de aulas',
 'Minutos ocupados únicos / minutos disponibles, descontando almuerzo y exclusiones. Incluye aulas sin uso; no mide asientos ocupados ni compatibilidad de cursos.': 'Minutos '
                                                                                                                                                                     'ocupados '
                                                                                                                                                                     'únicos '
                                                                                                                                                                     '/ '
                                                                                                                                                                     'minutos '
                                                                                                                                                                     'disponibles, '
                                                                                                                                                                     'descontando '
                                                                                                                                                                     'almuerzo '
                                                                                                                                                                     'y '
                                                                                                                                                                     'exclusiones. '
                                                                                                                                                                     'Incluye '
                                                                                                                                                                     'aulas '
                                                                                                                                                                     'sin '
                                                                                                                                                                     'uso; '
                                                                                                                                                                     'no '
                                                                                                                                                                     'mide '
                                                                                                                                                                     'asientos '
                                                                                                                                                                     'ocupados '
                                                                                                                                                                     'ni '
                                                                                                                                                                     'compatibilidad '
                                                                                                                                                                     'de '
                                                                                                                                                                     'cursos.',
 'Minutos ocupados / disponibles': 'Minutos ocupados / disponibles',
 'Total': 'Total',
 'Ninguna': 'Ninguna',
 'Hay datos desconocidos o incompletos. Los indicadores no sustituyen la revisión de integridad.': 'Hay '
                                                                                                   'datos '
                                                                                                   'desconocidos '
                                                                                                   'o '
                                                                                                   'incompletos. '
                                                                                                   'Los '
                                                                                                   'indicadores '
                                                                                                   'no '
                                                                                                   'sustituyen '
                                                                                                   'la '
                                                                                                   'revisión '
                                                                                                   'de '
                                                                                                   'integridad.',
 'Cumplidas': 'Cumplidas',
 'Excepciones manuales activas de laboratorio / sesiones asignadas: {ratio}. Confirmadas: {ids}. Sin confirmar: {unconfirmed}. No evaluables: {unknown}. Registros inactivos: {inactive}.': 'Excepciones '
                                                                                                                                                                                            'manuales '
                                                                                                                                                                                            'activas '
                                                                                                                                                                                            'de '
                                                                                                                                                                                            'laboratorio '
                                                                                                                                                                                            '/ '
                                                                                                                                                                                            'sesiones '
                                                                                                                                                                                            'asignadas: '
                                                                                                                                                                                            '{ratio}. '
                                                                                                                                                                                            'Confirmadas: '
                                                                                                                                                                                            '{ids}. '
                                                                                                                                                                                            'Sin '
                                                                                                                                                                                            'confirmar: '
                                                                                                                                                                                            '{unconfirmed}. '
                                                                                                                                                                                            'No '
                                                                                                                                                                                            'evaluables: '
                                                                                                                                                                                            '{unknown}. '
                                                                                                                                                                                            'Registros '
                                                                                                                                                                                            'inactivos: '
                                                                                                                                                                                            '{inactive}.'})

# Keyboard and assistive-technology labels.
MESSAGES.update({'Use flechas para recorrer celdas y Tab para salir. En tablas ordenables, Ctrl+Mayús+Arriba o Abajo ordena la columna actual.': 'Use '
                                                                                                                                 'flechas '
                                                                                                                                 'para '
                                                                                                                                 'recorrer '
                                                                                                                                 'celdas '
                                                                                                                                 'y '
                                                                                                                                 'Tab '
                                                                                                                                 'para '
                                                                                                                                 'salir. '
                                                                                                                                 'En '
                                                                                                                                 'tablas '
                                                                                                                                 'ordenables, '
                                                                                                                                 'Ctrl+Mayús+Arriba '
                                                                                                                                 'o '
                                                                                                                                 'Abajo '
                                                                                                                                 'ordena '
                                                                                                                                 'la '
                                                                                                                                 'columna '
                                                                                                                                 'actual.',
 'Aulas con restricciones': 'Aulas con restricciones',
 'Use flechas para seleccionar y Espacio para marcar o desmarcar.': 'Use flechas para seleccionar y Espacio '
                                                                    'para marcar o desmarcar.',
 'Cursos permitidos en el aula seleccionada': 'Cursos permitidos en el aula seleccionada',
 'Duración en horas': 'Duración en horas',
 'Duración en minutos': 'Duración en minutos',
 'Hora de inicio preferida': 'Hora de inicio preferida',
 'Semilla fija': 'Semilla fija',
 'Progreso de generación': 'Progreso de generación',
 'Leer estado (F6)': 'Leer estado (F6)',
 'Estado actual': 'Estado actual',
 'Use flechas para recorrer la cuadrícula y Tab para salir. La Lista detallada ofrece las mismas sesiones en filas, con estado y acciones.': 'Use '
                                                                                                                                             'flechas '
                                                                                                                                             'para '
                                                                                                                                             'recorrer '
                                                                                                                                             'la '
                                                                                                                                             'cuadrícula '
                                                                                                                                             'y '
                                                                                                                                             'Tab '
                                                                                                                                             'para '
                                                                                                                                             'salir. '
                                                                                                                                             'La '
                                                                                                                                             'Lista '
                                                                                                                                             'detallada '
                                                                                                                                             'ofrece '
                                                                                                                                             'las '
                                                                                                                                             'mismas '
                                                                                                                                             'sesiones '
                                                                                                                                             'en '
                                                                                                                                             'filas, '
                                                                                                                                             'con '
                                                                                                                                             'estado '
                                                                                                                                             'y '
                                                                                                                                             'acciones.'})
