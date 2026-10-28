# Arquitectura y responsabilidades

SORTH es un monolito modular con dominio independiente, casos de uso y adaptadores.
Cada responsabilidad tiene una implementación canónica. No se incluyen interfaces
Tkinter, scripts de reenvío, migraciones de formatos retirados ni lectores de cursos
alternativos al contrato vigente.

## Dirección de dependencias

| Capa | Responsabilidad | Dependencias internas permitidas |
| --- | --- | --- |
| `scheduling` | Modelos, reglas, validación, planificación y calidad | `scheduling` y biblioteca estándar |
| `application` | Casos de uso y contratos de entrada | `application`, `scheduling` |
| `infrastructure` | Excel/PDF, SQLite, preferencias, red y procesos del sistema | `infrastructure`, `application`, `scheduling` |
| `gui` | Presentación PyQt6 y coordinación de interacción | `gui`, `application`, `infrastructure`, `scheduling` |
| `mcp_adapter` | Transporte y recursos efímeros del servidor opcional | `mcp_adapter`, `application`, `infrastructure`, `scheduling` |
| `bootstrap` | Composición de ejecutables, recuperación y diagnósticos empaquetados | Las capas necesarias para conectar el programa |
| `tools` | Desarrollo, mediciones, compilación y controles | Consume la aplicación; nunca es importado desde `src` |

`SchedulingService` recibe datos de dominio o una fábrica de lector explícita.
No selecciona ni importa infraestructura. La GUI y el CLI componen `ExcelReader`
mediante `bootstrap.scheduling`; no existe una fábrica implícita por compatibilidad.

## Presentación

`MainWindow` construye la ventana y conecta sus acciones. Los controladores tienen
una responsabilidad delimitada:

- `ImportController`: revisión, cancelación y aceptación de importaciones.
- `ExportController`: validación, alcance, destino y mensajes de exportación.
- `SessionController`: guardado, recuperación y estado de persistencia.

Los workers reciben datos separados; únicamente el hilo Qt modifica widgets.
Una operación cancelada o un resultado obsoleto no reemplaza el estado aceptado.
La materialización de una edición y su guardado conservan rollback y pruebas de fallo.

## Persistencia y formatos vigentes

La sesión usa SQLite, esquema 5. `schedule_present` distingue una sesión sin generar
(`assignments=None`) de un resultado vacío (`assignments={}`). Ambos estados se
conservan al guardar, restaurar, respaldar y comparar escenarios. Todas las
asignaciones se validan con las mismas reglas de dominio antes de escribir o cargar.

El catálogo de proyectos usa esquema 2; los metadatos de escenario usan formato 2
y un único calendario serializado por `ProjectCalendar.to_dict()`. Las bases y los
metadatos de otras versiones se rechazan sin convertirlos ni sobrescribirlos.
Los archivos de usuario antiguos no se eliminan. Para trabajar con el contrato
vigente se importa el Excel de origen en una sesión nueva.

Las funciones opcionales usan un único JSON y una única escritura atómica compartida
por GUI y CLI. QSettings conserva idioma y movimiento; no aporta permisos ni flags.
Un permiso MCP activo requiere una identidad de revocación validada.

## Verificación

Desde `project_root`:

```sh
python tools/check_architecture.py
python -m pytest -c pytest.ini --rootdir=. -q tests/test_architecture tests/test_documentation
```

El control AST inspecciona imports absolutos, relativos y locales sin importar la
aplicación. Rechaza infraestructura en los casos de uso, Qt en dominio, aplicación
e infraestructura, y dependencias desde producción hacia herramientas o pruebas.
La única conexión excepcional de composición es `gui.scheduler_worker` hacia
`bootstrap.scheduling`. Los diagnósticos empaquetados pertenecen a `bootstrap`.

La [suite completa en cuatro procesos](../development/WORKFLOW.md#suite-completa-en-cuatro-procesos)
verifica también la unión exacta de inventarios. La aceptación del ejecutable en
Windows sigue siendo independiente de las pruebas sin pantalla.
