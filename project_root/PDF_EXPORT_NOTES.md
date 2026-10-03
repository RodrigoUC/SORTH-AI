# Exportación directa de horarios PDF

En **Exportar todas las asignaciones** o **Exportar filtrado**, elija **Documentos PDF (*.pdf)** en el diálogo Guardar. Al cambiar el idioma de la interfaz se traducen los nombres de los formatos. El PDF usa los títulos, días y leyenda del idioma seleccionado; los datos introducidos por el usuario permanecen intactos. Excel y CSV conservan sus contratos actuales. La ruta es la seleccionada por el usuario; cancelar no crea archivos.

El PDF contiene texto seleccionable, versión de SORTH, aulas, días, horas exactas HH:mm, identificadores de sesión, nombres completos y páginas numeradas. Presenta una tabla cronológica por aula, en A4 horizontal, sin requerir Excel. No reduce las sesiones cortas a bloques visuales ilegibles. Cada fila conserva el intervalo original y cada aula comienza una sección. Los encabezados de aula y columnas se repiten al paginar; los nombres extraordinariamente largos se continúan con el día, las horas y el grupo repetidos.

## Alcance y validación

- La aplicación valida el horario global antes de abrir Guardar, también para una vista filtrada. Un filtro no puede ocultar una asignación inválida.
- Todas las páginas muestran cuántas asignaciones se exportaron, el total global asignado y cuántas sesiones permanecen pendientes. Un resultado parcial se rotula **PARCIAL**. Sin contexto global, la API informa que los pendientes son desconocidos; la API filtrada exige el total global.
- La primera sección detalla Buscar, Aula, Día y Estado. La pestaña activa y el selector local del aula de la cuadrícula no se aplican. En una exportación total se indica que no se aplicaron filtros.
- **EXCEPCIÓN LAB** identifica autorizaciones registradas para sesiones exportadas. La API de representación marca **CONFLICTO** usando la misma proyección de intervalos exactos que Excel y el visor; la GUI impide exportar un horario inválido. El color por curso es complementario: texto e identificadores conservan el sentido en escala de grises.
- Un filtro vacío no abre Guardar en la GUI. La API puede generar un documento explícitamente vacío, conservando los conteos globales.

La API PDF acepta un mapa opcional `labels` de claves de presentación a plantillas traducidas. No depende de Qt ni distingue idiomas dentro del exportador. Las claves ausentes o plantillas inválidas vuelven al español; los llamadores directos usan español si no suministran un catálogo.

## Conservación de datos y dependencias

El documento se genera primero en memoria. Sólo después se escribe un temporal en el directorio elegido y se reemplaza el destino atómicamente. Un fallo de generación o de reemplazo conserva un destino anterior y elimina el temporal. No se imprime automáticamente, no se envían datos y no se crea otra copia permanente.

Las cadenas se escapan como texto PDF: fórmulas, etiquetas y símbolos como `=SUM(1,2)`, `<b>` o `&` son literales. Excel y CSV mantienen sus contratos sin cambios.

ReportLab 4.4.9 pasa del conjunto de documentación al conjunto de ejecución; la versión y licencia ya constan en el lock e inventario Windows. DejaVu Sans se incluye en assets con su licencia y queda incrustada en el PDF. pypdf sólo se usa para pruebas.

## Límites que deben verificarse

- Se prueban acentos, nombres largos, griego y cirílico. Escrituras que requieren conformación contextual (por ejemplo árabe o índicas) y glifos ausentes (por ejemplo CJK) se rechazan antes de escribir, con indicación de usar Excel/CSV. No se sustituyen silenciosamente por cuadrados. No se afirma soporte Unicode universal.
- Linux/offscreen y el render de Poppler no equivalen a una prueba nativa de Windows. La prueba de humo del ejecutable ahora genera un PDF, comprobando la disponibilidad del motor y de la fuente. La apertura visual en visores Windows, diálogo nativo, impresora real, márgenes físicos, escala de grises y políticas de carpeta requieren la aceptación Windows del commit integrado.
- Un nombre de aula que por sí solo ocupe un encabezado de más de 96 puntos produce un error explícito, sin truncar el dato ni dañar un archivo existente.
