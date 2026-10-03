# ADR: evolución incremental de la arquitectura de SORTH

- Fecha de investigación: 2026-10-03
- Ámbito: aplicación local PyQt6, motor de horarios, Excel/SQLite y adaptador MCP opcional.
- Decisión: conservar las cuatro capas del README y reforzarlas como un **monolito modular con puertos y adaptadores puntuales**. No existe una arquitectura universalmente mejor; esta decisión responde al código y al despliegue actuales.

## Alternativas contrastadas

1. **Capas existentes + puertos/adaptadores: elegida.** `scheduling` conserva reglas y algoritmo; `application`, los casos de uso; `infrastructure`, archivos y persistencia; `gui`, interacción y presentación. El adaptador `mcp_adapter` es otra entrada al mismo motor. El patrón original de Cockburn propone poder ejecutar y probar la aplicación sin su interfaz ni su base de datos. En SORTH esto permite sustituir un lector real por un doble de prueba sin duplicar el planificador. [Fuente primaria: Cockburn, Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture).
2. **MVVM / Presentation Model como reorganización general: no se adopta.** Es útil para separar estado y comportamiento de una pantalla de sus controles, pero resuelve un problema de presentación; no sustituye las fronteras entre motor, archivos y protocolo. En Qt, Model/View permite desacoplar datos, vistas y delegados. Se puede incorporar por pantalla si reduce sincronización duplicada o un cuello de botella medido, sin reescribir ahora todas las tablas. [Presentation Model, Fowler](https://martinfowler.com/eaaDev/PresentationModel.html); [Qt Model/View Programming](https://doc.qt.io/qt-6/model-view-programming.html).
3. **Microservicios: descartados para el alcance actual.** El producto se distribuye como aplicación de escritorio y no muestra una necesidad de despliegue o escalado independiente por subsistemas. Separarlo en servicios añadiría operación de red, despliegue y modos de fallo. Fowler describe ese coste adicional y recomienda conservar buena modularidad interna cuando el sistema no requiere distribución. Esta conclusión es una evaluación de SORTH, no una prohibición general. [Fuente primaria: Microservice Premium](https://martinfowler.com/bliki/MicroservicePremium.html).

## Evidencia del código revisado

- `src/scheduling/` no importa `gui`, `application`, `infrastructure` ni MCP.
- `application/schedule_preview.py` ya acepta un `SchedulingPort` y vuelve a validar resultados. `tests/test_mcp/test_preview.py` comprueba su ejecución con Python `-S`, sin Qt, SDK MCP, pandas, openpyxl ni SQLite.
- En la base revisada, `application/scheduling_service.py` seleccionaba directamente `ExcelReader` para el flujo histórico basado en ruta. Esta revisión sustituye esa selección por un `SchedulingReaderFactory` inyectable y composición externa en `bootstrap.scheduling`, con un puente lazy para conservar la llamada histórica.
- `application/packaged_smoke.py`, `packaged_workflow.py` y `recovery_command.py` son integración/compatibilidad. Las preferencias y preparación MCP también incluyen E/S. Por eso no se describe toda la carpeta `application` como funcionalmente pura.
- `gui/scheduler_worker.py` toma copias de los datos, ejecuta el servicio y emite resultados. La GUI conserva la aplicación del resultado y su persistencia. El refactor no altera el algoritmo, la semilla ni la política LAB.

## Cambios acotados de esta revisión

1. Documentar las responsabilidades con los nombres existentes y comprobar importaciones mediante pruebas AST. Las excepciones deben nombrar módulos concretos, explicar su propósito y no convertirse en permisos generales de capa.
2. Aplicado: contrato de lectura en `application.scheduling_ports`, fábrica en `bootstrap.scheduling` e inyección desde los puntos de composición GUI/CLI. La selección de `ExcelReader` pertenece a composición externa, no al algoritmo. Conservar la firma histórica y documentar su puente de compatibilidad si se mantiene. Los `Protocol` de Python permiten contratos estructurales sin exigir herencia a adaptadores o dobles de prueba. [Fuente primaria: PEP 544](https://peps.python.org/pep-0544/).
3. Mantener MCP opcional y dirigido a casos de uso compartidos. Para la exportación en memoria, permitir únicamente la composición `mcp_adapter.worker` → `infrastructure.schedule_exporter` y el modelo `scheduling.time_model`; el contrato/preview no adquiere dependencias de GUI o archivos. No duplicar validaciones ni reglas de asignación en el servidor MCP.
4. Conservar el propietario de cada estado: datos de trabajo separados en el worker; widgets/modelos Qt en su hilo; aceptación del resultado en la GUI. `QThread.run()` puede especializarse para este trabajo finito; la advertencia importante es que los slots del objeto `QThread` no pasan automáticamente al hilo nuevo. [Qt Threads and QObjects](https://doc.qt.io/qt-6/threads-qobject.html); [QThread](https://doc.qt.io/qt-6/qthread.html). Los modelos enlazados a vistas deben actualizarse en el hilo GUI. [QAbstractItemModel: thread safety](https://doc.qt.io/qt-6/qabstractitemmodel.html#thread-safety).
5. Conservar validación y persistencia antes de aceptar el estado visible. SQLite ofrece atomicidad dentro de una transacción, pero eso no prueba por sí solo la atomicidad de la GUI, archivos exportados o varios almacenes. Mantener pruebas de fallo y rollback de SORTH. [SQLite: Atomic Commit](https://www.sqlite.org/atomiccommit.html).

## Verificación exigida

- Guardia AST de dependencias, incluidas importaciones relativas, absolutas y diferidas.
- Lector falso: carga validada una sola vez si faltan ambos conjuntos; carga solo de la parte faltante si el llamante aporta la otra.
- Inyección: el flujo con datos completos no llama a ningún lector; errores/cancelación no alteran los objetos de entrada.
- Compatibilidad: la llamada histórica por ruta y la ruta explícitamente compuesta producen el mismo resultado con la misma semilla y fixture sintética.
- Aislamiento: generar propuestas y usar lectores falsos con `python -B -S`; sin Qt, SDK MCP ni paquetes de Excel cargados accidentalmente.
- Regresiones: pruebas de scheduling/application, importación/exportación, MCP, cancelación y aceptación atómica de GUI. Ejecutar la suite completa tras integrar cambios paralelos.

## Consecuencias y límites

Se obtiene una frontera de sustitución comprobable y menor acoplamiento sin cambiar el comportamiento del usuario. Se conservan adaptadores y compatibilidad donde el coste de moverlos ahora no aporta una mejora demostrada. No se introduce contenedor de inyección, bus global, ORM, event sourcing ni despliegue distribuido. La extracción de controladores/modelos de pantallas grandes queda para cambios concretos con pruebas y mediciones; este ADR no afirma que esa migración esté realizada.
