# Consulta y exportación de horarios

## Consultar

- Buscar combina palabras y no distingue mayúsculas ni acentos. Aula, Día y Estado se aplican a las tres vistas.
- Las tablas son de solo lectura. Editar curso y Quitar del horario operan sobre la identidad seleccionada aunque se ordene la tabla.
- Las sesiones quitadas siguen visibles como Sin asignar. El resumen usa las asignaciones vigentes, no metadatos antiguos del grupo.
- La cuadrícula conserva minutos exactos, sesiones cortas y adyacentes, y muestra todos los participantes de un conflicto. Los colores por curso son estables y coinciden con Excel.

## Exportar

- **Exportar completo** conserva el comportamiento existente: exporta todas las asignaciones, sin aplicar los filtros. Ctrl+S mantiene esta acción.
- **Exportar filtrado (N)** es una acción adicional para Excel y CSV. N cuenta las sesiones asignadas que cumplen Buscar, Aula, Día y Estado. La pestaña activa y el selector local del aula de la cuadrícula no restringen esta exportación; use el filtro compartido Aula para exportar un aula.
- El diálogo de guardado y el mensaje final indican alcance y cantidad. Si no hay coincidencias asignadas, la acción filtrada está desactivada. Sin asignar no produce filas de horario ficticias.
- Generar o invalidar un horario desactiva ambas acciones. Cancelar el guardado no modifica filtros ni datos.
- Si la exportación falla, el error permanece en la barra y en **Leer estado (F6)** después de cerrar el diálogo. Identifica el último destino por su nombre, sin añadir su ruta al estado. Un nuevo resultado sustituye este mensaje; cancelar el selector conserva el último resultado.

## Compatibilidad y seguridad

CSV conserva las siete columnas, orden, separador coma y UTF-8 con BOM. Las tablas Asignaciones y Por Aula mantienen el contrato, incluido Grupo sin sufijo de parte; la cuadrícula muestra el identificador completo de cada sesión.

Asignaciones y CSV se ordenan por curso y grupo con orden natural (G2 antes de G10), y las sesiones de cada grupo por día de la semana y hora exacta. Por Aula se ordena por aula natural, día y hora. Las pestañas también siguen el orden natural de aulas y no duplican el prefijo «Aula».

Texto que pudiera interpretarse como fórmula recibe un apóstrofo inicial en ambos formatos. CR/CRLF se normalizan a LF y controles no admitidos por XML se convierten en espacios en ambos formatos. Los nombres de hojas se sanean y resuelven colisiones sin distinguir mayúsculas.

Excel y CSV se escriben primero en un archivo temporal del mismo directorio y reemplazan el destino únicamente al terminar correctamente. Un fallo de escritura, cierre, sincronización o reemplazo conserva el archivo anterior y elimina el temporal.

Excel incorpora encabezados repetidos al imprimir, filtros, paneles congelados, filas alternas, texto ajustado y orientación horizontal A4. Cada aula imprime solo su rango ocupado para evitar páginas iniciales vacías; no elimina sesiones ni modifica el horario. Las celdas combinadas reciben alturas explícitas.

Las cuadrículas incorporan saltos de página explícitos y dividen las celdas combinadas en cada salto. Si una sesión continúa en otra página, se repite su etiqueta completa con el mismo horario original. Esto evita recortar texto al imprimir sin reducir el tamaño de letra; no añade asignaciones a las tablas ni al CSV.

## Verificación

Ejecutar desde project_root: `QT_QPA_PLATFORM=offscreen python -m pytest -q`.

Esta revisión se probó en Linux con Qt offscreen a 1200×800 y 960×640, con el Excel de ejemplo (249 asignaciones), nombres largos, acentos, saltos de línea, fórmulas, conflictos y sesiones de pocos minutos. La suite incluye paridad CSV/Excel, invariantes de intervalos, filtros, ordenación, selección, cancelación, eliminación, limpieza, exportación completa y filtrada, estado vacío y bloqueo por datos obsoletos/generación.

No se ha validado Microsoft Excel ni la aplicación nativa en Windows. No se reconstruyen ni publican ejecutables en este cambio.

Auditoría adicional: renderizado PDF con LibreOffice en Linux del archivo completo (249 sesiones), exportación filtrada, nombres extensos, acentos y conflictos. Se verificaron paridad CSV/Asignaciones, filtros y paneles, días y minutos exactos, orden natural y ausencia de celdas combinadas que atraviesen saltos de página. La vista de impresión no equivale a validación en Microsoft Excel ni a impresión física.

## Nota sobre los datos históricos

Las mediciones anteriores con 249 asignaciones corresponden a un conjunto retirado y no describen el ejemplo actual. La distribución actual incluye exclusivamente `Cursos_Ejemplo.xlsx`, sintético, con 42 sesiones. Las pruebas actuales vuelven a comprobar planificación, restricciones y paridad de exportación con ese archivo.
