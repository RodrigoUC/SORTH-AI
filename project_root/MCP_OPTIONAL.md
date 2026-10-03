# MCP opcional: propuestas de horarios sin guardar

SORTH funciona sin MCP, Internet, modelos, claves o pagos. Esta integración **no se inicia con la GUI**, no forma parte del instalador Windows y no llama a ningún modelo. Es un adaptador local `stdio` que un cliente MCP puede iniciar por decisión explícita. No abre puertos, HTTP, SSE ni escucha en la red.

## Configuración: permiso local y disponibilidad

**Configuración → Permitir servidor MCP local** empieza desactivado. El botón
**Verificar disponibilidad local de MCP** ejecuta una prueba local de carga del SDK
y construcción del servidor en un subproceso fijo, sin iniciar stdio, sin datos de
horarios, sin red y con límite de cinco segundos. Se distingue SDK ausente,
versión incompatible (se admite exactamente `mcp==1.30.0`), error de carga y tiempo
agotado. La comprobación es asíncrona, se cancela al cerrar y no instala nada.
Solo se puede guardar una nueva activación si la comprobación tuvo éxito.
Guardar no inicia el servidor ni configura un cliente/modelo. Cancelar no activa
nada. Guarda los cambios de recursos y el permiso MCP por separado, tanto al
activar como al desactivar, para que una transacción de recursos fallida nunca
revierta una revocación o publique una activación parcial.

El **EXE estándar no incluye el SDK ni un servidor MCP ejecutable**: la opción
muestra esa limitación y no se puede activar desde ese entorno. Nunca se lanza
`sys.executable` del EXE como si fuera Python. Para MCP usa el código fuente y el
entorno Python separado descrito abajo; no hay descarga, compra ni instalación
automática de complementos. La GUI comprueba solo su propio entorno, no descubre
ni prueba otros intérpretes instalados.

GUI y servidor comparten un único registro `features.mcp_server` en
`SORTH/optional-features.json`: Linux usa `$XDG_CONFIG_HOME` o `~/.config`, macOS
`~/Library/Preferences`, Windows `%LOCALAPPDATA%`. El archivo no contiene claves,
proveedores ni datos de horarios. El servidor lee ese permiso al iniciar, al
recibir cada llamada y antes de devolver el resultado. Ausencia, corrupción,
versión de archivo desconocida o permiso desactivado cierran el acceso. Desactivar
bloquea nuevos inicios y llamadas y descarta una propuesta pendiente, incluso si
vuelves a activar MCP antes de que termine. Un identificador de generación
`mcp_generation` dentro del mismo registro cambia en cada transición de permiso;
las preferencias antiguas sin identificador se migran en la siguiente escritura
explícita, sin escrituras al leer. Un identificador inválido también cierra el
acceso. No mata el proceso que pertenece al cliente. Una generación ya iniciada puede terminar
internamente con su límite existente de diez segundos. Cierra el proceso desde
el cliente. No se revocan copias de resultados entregados previamente.

Para instalaciones sin Qt, el CLI de configuración siguiente usa el mismo archivo
y conserva sus demás preferencias mediante reemplazo atómico. `--preferences`
permite elegir explícitamente otro archivo; úsalo **igual** al configurar el
servidor y el CLI. La GUI refresca el permiso al abrir o comprobar Configuración y bloquea un guardado
si el CLI cambió el permiso desde la última lectura; revisa la casilla antes de
volver a guardar, incluso tras una secuencia OFF→ON. GUI, CLI y recuperación
usarán un bloqueo del SO no bloqueante durante toda la lectura y escritura: si
otro escritor lo tiene, el guardado falla sin cambiar las preferencias y puede
reintentarse después. El archivo auxiliar `.lock` permanece para conservar el
mismo bloqueo; no contiene preferencias, no lo borres para forzar un desbloqueo.
El SO libera el bloqueo al cerrar el proceso. Editores externos que no usen este
protocolo no están coordinados; no edites el JSON manualmente mientras se usa.
Los errores preservan el original y no lo reparan silenciosamente. El lector
rechaza claves duplicadas, valores no finitos y profundidad superior a 32 niveles. Ejecutar el
CLI con `--enable` es una autorización explícita; la comprobación de disponibilidad
se hace al arrancar el servidor y puede hacerse por separado sin activarlo.

## Activar, probar y desactivar

Requiere Python 3.12 y el código fuente con las correcciones de validación/persistencia de #2/#3. Desde `project_root`, crea un entorno separado; no alteres el entorno de la GUI:

```sh
python -m venv .venv-mcp
# Linux/macOS:
.venv-mcp/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-mcp.lock
.venv-mcp/bin/python -B -m src.mcp_adapter.availability
.venv-mcp/bin/python -B -m src.application.mcp_preferences --enable
.venv-mcp/bin/python -B -m src.mcp_adapter.server
# Windows: sustituye .venv-mcp/bin/python por .venv-mcp\Scripts\python.exe
```

El proceso espera mensajes MCP por stdin. No es una consola de conversación. Ctrl+C o cerrar el cliente lo termina. Para desactivar, desmarca la opción y guarda en Configuración, o ejecuta `.venv-mcp/bin/python -B -m src.application.mcp_preferences --disable`; después quita la entrada del cliente y cierra ese proceso. La GUI sigue funcionando igual. No hay servicio de sistema, inicio automático ni credenciales que revocar.

`requirements-mcp.txt` fija `mcp==1.30.0`, versión de la rama 1.x mantenida por el SDK oficial. Se elige explícitamente esa API; no se permite que una resolución sin límite la cambie a 2.x. `requirements-mcp-dev.txt` añade pytest. `requirements-mcp.lock` fija con hashes todas las dependencias del entorno opcional de ejecución y pruebas, resuelto de forma universal para Python 3.12; incluye pytest deliberadamente y las dependencias condicionales Windows `colorama` y `pywin32`. Se genera con `uv pip compile requirements-mcp-dev.txt --python-version 3.12 --universal --generate-hashes --no-build --output-file requirements-mcp.lock`; una resolución sólo Linux omitiría dependencias Windows. Las actualizaciones requieren regenerar el lock, auditar todos sus paquetes (también los condicionales) y repetir pruebas. El lock Windows de la aplicación no incorpora MCP.

## Conectar un cliente elegido por ti

En la configuración de servidores **locales stdio** de tu cliente, crea una entrada con:

- Nombre: `sorth-preview`
- Comando: ruta absoluta al Python de `.venv-mcp`
- Argumentos: `-B`, `-m`, `src.mcp_adapter.server`
- Directorio de trabajo (`cwd`): ruta absoluta a `SORTH-AI/project_root`
- Variables/credenciales: ninguna requerida
- Si elegiste un archivo alternativo: añade `--preferences`, `/ruta/absoluta/optional-features.json` a los argumentos. La GUI usa su archivo predeterminado; no alterna rutas desde este diálogo.

El formato de configuración depende del cliente. No pegues claves de proveedor en SORTH. Si tu cliente no admite `cwd`, usa su opción equivalente para lanzar desde `project_root`; no inventes una ruta de servidor remoto. Usa un cliente que soporte los esquemas de herramientas MCP y revisa sus permisos antes de compartir datos.

El cliente/host puede usar un modelo local, remoto o ninguno. **SORTH no configura ni verifica un proveedor.** Las cuentas, privacidad, envío de datos, retención y posibles cargos son responsabilidad de tu elección y configuración del cliente/proveedor. La prueba incluida usa el cliente de protocolo del SDK, sin modelo ni gasto de IA. No se ha probado un producto de host comercial ni su flujo de aprobación.

## Dos herramientas y un contrato estricto

- `validate_configuration`: valida la estructura, referencias y presupuesto de búsqueda. No ejecuta la búsqueda ni demuestra factibilidad.
- `generate_preview`: reutiliza `SchedulingService` y el validador independiente. Devuelve propuesta completa o parcial, sin guardarla.

Ambas reciben directamente el mismo objeto JSON; no un prompt en lenguaje natural. Ejemplo sintético:

```json
{
  "courses": [{
    "code": "BIO101", "name": "Biología sintética de ejemplo",
    "number_of_groups": 2, "duration_min": 60,
    "required_room_type": "LAB", "size": 20
  }],
  "classrooms": [{"name": "LAB1", "capacity": 30, "room_type": "LAB"}],
  "seed": 42,
  "classroom_restrictions": []
}
```

Consulta los esquemas de `tools/list` como contrato ejecutable (`preview_contract.py`). Los identificadores distinguen mayúsculas y minúsculas, tienen hasta 64 caracteres ASCII y sólo letras, números, `_` o `-`; el primer carácter debe ser letra/número. No son rutas. Los tamaños y capacidades son explícitos: 1–1000. No se acepta tamaño cero/desconocido, tipos numéricos coercionados, claves duplicadas ni campos no anunciados.

Los cursos aceptan opcionalmente `name` (hasta 160 caracteres, siempre datos no confiables), `suggested_classroom`, `preferred_day` (Lunes–Sábado), `preferred_start_min` (minutos desde medianoche) y `force_split` (booleano; omitido usa división automática del núcleo). Se requieren código, cantidad de grupos, duración, tipo y tamaño. La semilla entera 0–4294967295 es obligatoria. Se conservan orden de cursos/aulas y semilla para reproducción exacta con la misma versión del núcleo.

Las restricciones son objetos `{"classroom":"LAB1","allowed_courses":["BIO101"]}`. Una lista vacía prohíbe cursos en esa aula. Referencias desconocidas y duplicados se rechazan. Las reglas de reserva sugerida del núcleo siguen vigentes. Las preferencias son blandas: el núcleo puede relajarlas al reintentar.

### Reglas y límites visibles

- Máximo 32 cursos, 16 aulas, 16 grupos por curso; duración 1–540 minutos.
- Máximo 128 sesiones **después** de dividir cursos; presupuesto conservador de 100000 candidatos por construcción de dominios (`sesiones × aulas × 6 × 31`). El núcleo conserva su límite de reintentos; no se ofrece optimización ilimitada.
- Lunes–sábado, 07:00–22:00; almuerzo 12:00–13:00. Duración, capacidad, choques de aula, restricciones por curso y sesiones divididas se validan igual que en la aplicación.
- **LAB es estricto**. No existe herramienta de excepción. Una sugerencia textual nunca modifica esa política.
- No se modelan docentes, cohortes, viajes entre sedes, disponibilidad individual ni calendario personalizado. Un campo para esas reglas es un error; el host debe pedir aclaración, no inventarlas.
- Una sola generación en vuelo por proceso. Otra recibe `BUSY`, sin cola de trabajos. Validación de entrada es corta y acotada.
- Trama de entrada máxima: 128 KiB, profundidad JSON 20. Una trama excesiva cierra la conexión con diagnóstico fijo en stderr. El host debe reconectar con menos datos. JSON inválido recibe un aviso genérico del SDK, sin repetir contenido.
- Resultado del trabajador máximo: 256 KiB. El transporte MCP incluye contenido JSON estructurado y copia textual compatible; su trama puede ser mayor. No se truncan silenciosamente asignaciones.
- Tiempo del trabajador: 10 segundos desde su arranque. Cada generación usa un subproceso efímero; al vencer el plazo o cancelar, se termina y espera su salida. El tiempo de creación/recolección depende del SO y no es una garantía de tiempo real. El transporte usa I/O crudo en hilos daemon acotados (una lectura y una escritura); al terminar el proceso no espera indefinidamente que el host cierre stdin o consuma stdout. Una operación de pipe bloqueada puede sobrevivir hasta que el SO cierre los descriptores al salir, sin mantener vivo el proceso.

### Resultado y errores

Éxito: `status` es `validated`, `complete` o `partial`, con `normalized`, `session_count`, `candidate_upper_bound`, `assignments`, `pending`, `notices` y `capabilities`. Cada asignación incluye grupo, curso, aula, día 1–6 y minutos inicial/final. Cada pendiente incluye identificador y razón del núcleo. Un resultado parcial **no prueba que el problema sea imposible**. Un resultado completo sólo satisface las reglas declaradas, no restricciones ausentes. Revisa la configuración normalizada y los límites antes de usar una propuesta.

Errores de herramientas: `isError=true` y `structuredContent.error` con `code`, `path`, `message`. Ejemplos: `MISSING_FIELD`, `INVALID_TYPE`, `UNSUPPORTED_FIELD`, `UNKNOWN_REFERENCE`, `SESSION_LIMIT`, `CANDIDATE_LIMIT`, `BUSY`, `TIMEOUT`. Mensajes y rutas estructurales no repiten valores rechazados. Cancelación MCP puede no producir respuesta al request cancelado; el cliente debe dejar de esperarla según el protocolo. No se promete deshacer datos, porque ninguna operación los escribe.

## Arquitectura, privacidad y ACID

`preview_contract` y `schedule_preview` son casos de uso sin SDK, Qt, pandas, Excel ni SQLite. Un puerto pequeño permite sustituir la generación en pruebas. `SchedulingService` carga Excel de forma diferida sólo para el flujo de archivo existente; los datos proporcionados usan el planificador real, sin duplicarlo. El caso de uso conserva grupos y aulas canónicos independientes del puerto y rechaza grupos omitidos/alterados; una población vacía devuelta por un adaptador no puede convertirse en un éxito completo. El adaptador traduce herramientas/errores; un ejecutor efímero limita generación y cancelación. No hay llamadas a modelos, acceso a archivos arbitrarios, comandos elegidos por el usuario, herramientas de exportación ni acceso a sesión activa.

El host conoce lo que envía y recibe (incluidos nombres, cantidades y horarios). Puede enviarlo a su proveedor según su configuración. Usa datos sintéticos o códigos mínimos hasta revisar permisos institucionales. Los nombres se devuelven como datos; cualquier host que los convierta en instrucciones debe aplicar sus propias defensas contra inyección. SORTH no evalúa código, URLs ni órdenes en ellos. Se suprimen trazas/datos personales en diagnósticos; stdout es sólo protocolo. Python lee su código y dependencias; `-B` impide cachés de bytecode. No se afirma que el proceso esté aislado por sandbox ni que un host externo carezca de otras herramientas.

La base SQLite y sus transacciones no se importan ni se abren en este MVP. ACID sigue siendo responsabilidad del repositorio transaccional de la aplicación. Una propuesta o llamada de modelo **no es una transacción ACID**. Guardar/aplicar/exportar requeriría otro diseño y revisión: autorización explícita, versión de sesión y concurrencia, transacción atómica corta, validación, aislamiento, durabilidad, rollback y pruebas de fallos. Nunca mantener una transacción abierta esperando inferencia.

## Pruebas y compatibilidad

```sh
# En el entorno opcional, sin instalar Qt/pandas/modelos:
.venv-mcp/bin/python -B -m pytest tests/test_mcp -q
# En el entorno base, los casos puros siguen corriendo; el módulo stdio se omite:
python -m pytest -q
```

Las pruebas cubren cliente SDK real `initialize`/`tools/list`/`tools/call`, contrato JSON, cancelación por cable, cierre SIGINT con stdin abierto y stdout bloqueado, límites, fallo/timeout y posterior recuperación, LAB estricto, resultados parciales, reproducibilidad frente al servicio directo, texto adversario y directorios de sesión sin cambios. Un proceso `python -B -S` verifica casos de uso sin paquetes externos. Se negocian y prueban las revisiones MCP `2025-06-18` y `2025-11-25` con SDK 1.30.0. No se presupone compatibilidad con borradores o revisiones posteriores; el host debe negociar una soportada. El flujo CI opcional tiene jobs aislados Linux y Windows/Python 3.12: instala el lock con hashes, exige el SDK presente y Qt/pandas/modelo ausentes, comprueba cierre transitivo de dependencias según plataforma y ejecuta las pruebas stdio reales; empaquetado/GUI base mantienen su flujo sin MCP. Los casos POSIX de señal SIGINT y backpressure de descriptores se omiten explícitamente en Windows porque sus señales y consola son distintas; no se presentan como pruebas Windows aprobadas. La negociación, listado, llamadas, cancelación MCP, timeout, recolección de subprocesos y todos los demás contratos se ejecutan en ambos jobs. La ejecución nativa Windows queda pendiente del resultado de ese CI; descargar sus wheels desde Linux no equivale a ejecutarlos. Hosts comerciales: no probados aquí.

### Aceptación manual de consola Windows

Antes de afirmar cierre nativo por teclado, abre una consola Windows real, ejecuta el comando documentado, deja el proceso esperando stdin y pulsa Ctrl+C. Debe volver al prompt sin cerrar primero stdin y sin dejar procesos Python hijos. Después, en el host MCP elegido, genera/cancela una propuesta y cierra el host; comprueba que servidor y trabajador finalizan y que la sesión de la GUI queda intacta. Verifica también un host que deja de consumir stdout. El CI de pipes/protocolo no sustituye esta aceptación de consola/host; regístrala por separado con versión de Windows, Python, host y commit.

Base de trabajo: correcciones de validación y persistencia #2/#3, no un reemplazo de ellas. La aplicación incluye [indicadores explicables de calidad](QUALITY_METRICS.md) y [exportación PDF bilingüe](PDF_EXPORT_NOTES.md); este contrato MCP se limita a validación y propuestas, sin exponer esos indicadores ni herramientas de exportación. No modifica la sesión, las métricas ni los archivos de la GUI.

Fuentes oficiales consultadas al implementar (2 de octubre de 2026):

- [SDK Python v1.30.0 y mantenimiento de 1.x](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/README.md)
- [Servidor de bajo nivel y resultado estructurado, v1.30.0](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/docs/low-level-server.md)
- [Herramientas MCP 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Cancelación MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)
