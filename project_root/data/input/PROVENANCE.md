# Datos de demostración

`Cursos_Ejemplo.xlsx`, `courses_config.json` y `demo_source.json` contienen datos
creados desde cero para probar SORTH. Todos los códigos, aulas, campus y cursos
son ficticios. No representan una institución, oferta académica ni plan de estudios.
No se han copiado filas ni nombres de personas del material anterior.

El ejemplo contiene 8 aulas (6 regulares y 2 laboratorios), 12 cursos y 36 filas
de grupos. El proyecto largo genera tres sesiones por grupo: el resultado tiene
42 sesiones. También incluye duración de 90 minutos, preferencias individuales,
acentos y seis días. Con semilla 42 se asignan las 42 sesiones.

## Regeneración

Desde `project_root`, ejecutar `python tools/generate_demo_assets.py` regenera
exactamente las fuentes JSON y los tres formatos del icono original.
`python generate_courses_json.py` es un alias compatible para este comando.

Para volver a crear el Excel desde `demo_source.json`, usar Node.js con
`@oai/artifact-tool` 2.8.58 o posterior disponible y ejecutar:

```sh
node tools/build_demo_workbook.mjs .
```

Esta dependencia es sólo de autoría, no de ejecución ni de pruebas de SORTH.
El XLSX se verifica por valores y esquema, no por igualdad binaria: los metadatos
del generador pueden cambiar. La suite comprueba que cada celda de entrada
coincida con la fuente sintética, además de la planificación y exportación.

Los PDF académicos y el Excel previo se retiraron de la distribución actual.
La limpieza de la versión actual no elimina por sí sola copias históricas.
