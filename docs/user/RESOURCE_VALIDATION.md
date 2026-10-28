# Validación de recursos

Los recursos opcionales comparten las reglas del dominio desde GUI, persistencia
y generación. Los catálogos conservan identidades, alias, disponibilidad declarada
y asociaciones explícitas por sesión. Desactivar controles no elimina los datos.

## Contratos comprobados

- Cruces de docentes, grupos y estudiantes explícitamente asociados.
- Disponibilidad desconocida frente a disponibilidad explícitamente vacía.
- Referencias desconocidas, identificadores duplicados y tipos inválidos.
- Persistencia de sesiones fijadas, excepciones LAB y recursos desactivados.
- Guardado atómico y rechazo de JSON duplicado o dañado sin reparar su contenido.
- Comparación de escenarios, calendario propio y restauración de snapshots actuales.

La sesión admite únicamente el esquema 5 y el catálogo el esquema 2. Las bases
anteriores se rechazan sin migración ni reemplazo. Las omisiones de calendario o
recursos en una actualización parcial conservan el valor ya aceptado; no crean
contratos faltantes dentro de una sesión guardada dañada.

## Límites

Las asociaciones no se infieren de la matrícula ni de otros catálogos. Cada sesión
admite un docente; no se infiere codocencia. Los estudiantes individuales deben
asociarse explícitamente cuando se necesita esa protección. La importación Excel
no añade un formato alternativo de matrícula.

Las pruebas de dominio, aplicación, infraestructura e interfaz cubren estos
contratos. La aceptación nativa del instalador y las pruebas con usuarios son
controles independientes; no se deducen de resultados sin pantalla.
