# Configuración de demostración

`Cursos_Ejemplo.xlsx` es el punto de entrada recomendado para la interfaz gráfica.
Contiene las hojas `Aulas` y `Cursos`, cuyos encabezados están en la primera fila.
Cada fila de `Cursos` representa un grupo; las sesiones largas se dividen al planificar.

`courses_config.json` permite usar `CourseConfigReader` en integraciones Python.
Cada objeto contiene `code`, `name`, `number_of_groups`, `duration` (horas) y
`suggested_classroom`. Los códigos que terminan en L o P indican laboratorio.
Se admiten también `room_type`, `preferred_day` y `preferred_hour` opcionales.
La interfaz no carga este JSON automáticamente al abrir el Excel.

Los 12 objetos JSON corresponden a los mismos cursos sintéticos que el Excel.
Ver `PROVENANCE.md` para cantidades, origen y regeneración.
