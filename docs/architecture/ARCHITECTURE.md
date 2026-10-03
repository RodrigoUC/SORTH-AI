# Arquitectura y mapa del repositorio

La referencia principal sigue siendo la arquitectura por capas del
[README de la aplicación](../../project_root/README.md#arquitectura) y del
[README general](../../README.md#arquitectura-del-sistema). Esta guía amplía sus
responsabilidades y reglas; no sustituye `scheduling`, `application`,
`infrastructure` ni `gui` por una estructura ajena al proyecto.

La decisión de evolución es un **monolito modular con puertos/adaptadores puntuales**:
una aplicación local, módulos con responsabilidades explícitas y contratos pequeños
cuando hay una dependencia real que sustituir. Consulta la
[decisión y las alternativas investigadas](decisions/0001-modular-layers.md).

## Dónde va cada archivo

```text
SORTH-AI/
├── README.md, CONTRIBUTING.md, DESIGN.md    referencias generales y de interfaz
├── LICENSE, LICENSING.md, SECURITY.md       políticas y licencia del proyecto
├── docs/
│   ├── README.md                           índice por audiencia
│   ├── user/                               uso y comportamiento observable
│   ├── architecture/                       límites y decisiones de arquitectura
│   ├── development/                        flujo de trabajo, accesibilidad, idiomas
│   ├── release/                            compilación y distribución Windows
│   ├── design/                             propuestas y decisiones de producto
│   ├── evidence/                           capturas y evidencia sintética
│   └── performance/                        mediciones y su metodología
├── project_root/
│   ├── gui_app.py, main.py, mcp_app.py      entradas públicas estables
│   ├── src/
│   │   ├── scheduling/                     dominio y algoritmo
│   │   ├── application/                    casos de uso y coordinación
│   │   ├── infrastructure/                 Excel, PDF, SQLite, archivos
│   │   ├── gui/                            interfaz PyQt6
│   │   ├── bootstrap/                      composición explícita de colaboradores
│   │   ├── mcp_adapter/                    protocolo MCP opcional
│   │   └── ui/                             adaptador Tkinter histórico
│   ├── tests/                              regresiones por capa y contratos
│   ├── tools/                              desarrollo, documentación, builds, QA
│   ├── assets/                             recursos usados o generados por la app
│   ├── data/input/                         fixtures de demostración y procedencia
│   ├── installer/                          definición del instalador Windows
│   ├── security/                           configuración y revisiones de seguridad
│   └── requirements*, *.spec, build_*.ps1   contratos estables de instalación/build
├── third_party/                            avisos originales e inventarios
└── .github/                                automatización y plantillas de revisión
```

`data/output`, `build`, `dist`, entornos virtuales, cachés y bases locales son
salidas de trabajo ignoradas por Git. Las bases de usuarios no pertenecen al
repositorio. Los ejemplos de `data/input` son sintéticos y permanecen en su ruta
porque las entradas y el paquete congelado la consumen.

## Responsabilidades y dependencias

| Área | Responsabilidad | Dependencias internas admitidas |
| --- | --- | --- |
| `scheduling` | Entidades, intervalos, restricciones, asignación, algoritmo y validación | Solo `scheduling`; biblioteca estándar, sin Qt/Excel/SQLite/MCP como adaptadores |
| `application` | Coordinar casos de uso, validación de entradas/salidas, edición y propuestas | `application`, `scheduling`; adaptadores de `infrastructure` existentes mientras se extraen contratos concretos |
| `infrastructure` | Convertir formatos, guardar/cargar archivos y bases, exportar | `infrastructure`, `scheduling`; no importa aplicación ni GUI |
| `gui` | Widgets, controladores, traducción, presentación, revisión humana | `gui`, `application`, `infrastructure`, `scheduling` |
| `mcp_adapter` | Transporte, esquema de llamadas, aislamiento/cancelación, opt-in | `mcp_adapter`, `application`; SDK MCP aislado del arranque normal |
| `ui` | Adaptador Tkinter existente, conservado por compatibilidad | `ui`, `scheduling` |
| `bootstrap` | Conectar contratos de aplicación con adaptadores concretos | `application`, `infrastructure`, `scheduling`; sin reglas de negocio |
| `tools` | Compilar, medir, generar documentación y verificar | Puede consumir la app; `src` nunca importa `tools` ni `tests` |

Reglas prácticas:

1. Las restricciones de horario y la política LAB se implementan y prueban en
   `scheduling`; no se reescriben en botones, servidores o exportadores.
2. Un caso de uso recibe datos y colaboradores explícitos. Se introduce un `Protocol`
   donde un lector, repositorio o exportador deba sustituirse; no una interfaz por
   cada clase ni un contenedor global de dependencias.
3. El adaptador traduce al modelo compartido y los límites revalidan los datos.
   El protocolo MCP no se vuelve propietario de las reglas ni de la sesión GUI.
4. Los workers operan sobre datos separados. Solo el hilo GUI actualiza widgets y
   modelos vinculados a vistas. Cancelar o descartar un resultado obsoleto no aplica
   un estado parcial ni destruye prematuramente un worker activo.
5. Cada mutación conserva sus pruebas de fallo, persistencia y restauración.
   Una transacción SQLite no demuestra atomicidad conjunta de GUI, Excel y backups.

## Excepciones existentes, expresas y pequeñas

El repositorio tiene integración histórica; no se afirma que toda `application`
sea pura o que la separación hexagonal ya esté terminada.

- `application.packaged_smoke` y `application.packaged_workflow` orquestan pruebas
  del ejecutable y pueden importar GUI/Qt. No extiendas esa excepción a otros casos
  de uso ni llames a estos módulos desde el dominio.
- `infrastructure.gui_session_lock` usa `QLockFile` para la exclusión de instancias.
  Esto no permite Qt en todos los repositorios o lectores.
- `application.recovery_command` integra recuperación con el repositorio actual.
  Las preferencias, verificación y preparación MCP también contienen E/S local.
- La composición de exportación MCP se limita a `mcp_adapter.worker` →
  `infrastructure.schedule_exporter`. No habilita persistencia de la sesión ni
  importaciones de GUI para el adaptador entero.
- El guard admite el puente concreto `application.scheduling_service` →
  `bootstrap.scheduling` para conservar la API histórica basada en ruta cuando se
  introduce una fábrica de lector externa. `bootstrap` es composición, no una
  nueva capa de negocio; los clientes nuevos deben inyectar el colaborador. La
  composición GUI se limita a `gui.scheduler_worker` → `bootstrap.scheduling`.

## Controles ejecutables

Desde `project_root`:

```sh
python tools/check_architecture.py
python -m pytest -q tests/test_architecture tests/test_documentation
```

El guard usa AST: normaliza imports relativos/absolutos e inspecciona los imports
locales dentro de funciones sin cargar Qt ni ejecutar la app. Las pruebas también
comprueban casos prohibidos para evitar un guard que siempre devuelve éxito.
No analiza strings de import dinámico o de comandos de subprocesos; las pruebas
MCP sin `site-packages` y las pruebas reales de importación/ejecución cubren esos
contratos por separado.

Los enlaces Markdown locales se resuelven desde cada documento, incluidas imágenes
y referencias. Las rutas públicas de ejecución, el manual canónico, el destino PDF
y los documentos del ZIP se verifican por pruebas. Este control no prueba enlaces
externos, validez semántica del texto ni todos los anchors de Markdown.

La suite completa de Windows ya descubre estos tests nuevos. El job MCP aislado
mantiene su selección propia para no añadir dependencias de GUI o documentación.

## Cómo ampliar un área sin dispersarla

- Empieza por la responsabilidad y el contrato; el nombre de una función no basta
  para crear una nueva capa o carpeta.
- Agrega módulos cohesivos en la capa actual. Cuando una familia crezca y tenga
  varios colaboradores estables, extrae un subpaquete conservando adaptadores de
  importación donde haya consumidores externos.
- Evita carpetas genéricas `utils`, `common` o `helpers` sin dueño. Usa nombres del
  propósito: `calendar_transition`, `schedule_exporter`, `import_candidate`.
- Documenta cambios de frontera en una decisión breve en `architecture/decisions`:
  contexto, alternativas, decisión, consecuencias y cómo comprobarla.
- No muevas al mismo tiempo código, comportamiento, locks y esquema persistido.
  Prefiere commits de movimiento/adaptadores, comportamiento y pruebas distinguibles.
- Mantén la [guía de desarrollo](../development/WORKFLOW.md), documentación de usuario
  y pruebas junto al cambio que afecta su contrato.
