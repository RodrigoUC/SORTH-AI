# MCP opcional: propuestas de horarios sin guardar

SORTH funciona sin MCP, Internet, modelos, claves o pagos. La distribución Windows
puede incluir un complemento MCP empaquetado; **no se prepara, activa ni inicia
automáticamente al abrir la GUI**. Es un adaptador local `stdio` que el cliente elegido inicia por
decisión explícita. No abre puertos, HTTP, SSE ni escucha en la red.

## Preparar el complemento desde Configuración

1. Pulsa **Configuración → Preparar complemento MCP**. La confirmación muestra
   la versión y el destino exacto dentro de
   `%LOCALAPPDATA%/SORTH/components/mcp/<versión-commit>/`.
2. Revisa y confirma. Se comprueban el archivo incluido, sus tamaños y hashes,
   se preparan archivos en una carpeta temporal propia y se ejecuta una prueba
   local limitada antes del cambio atómico final. No hay descarga, `pip`, búsqueda
   de otros intérpretes ni instalación en Python del sistema. No hace falta que
   Python esté instalado en el equipo del usuario.
3. Espera **Complemento MCP preparado y verificado**. Esto no marca la casilla
   de permiso, no inicia un servidor y no configura ningún cliente o proveedor.
4. Si deseas permitir el servidor, marca **Permitir servidor MCP local** y pulsa
   **Guardar**. La comprobación local debe pasar antes de una nueva activación.
5. Abre **Ver guía de conexión**. Copia la configuración del cliente elegido
   y combínala manualmente con su configuración existente. La ruta del ejecutable
   procede del complemento preparado/verificado, no de una ruta supuesta.

Configuración organiza el flujo en tres pasos: preparar/verificar, guardar el
permiso local y configurar el cliente. **Permiso guardado** informa lo que ya está
vigente; **Cambio pendiente** corresponde a la casilla sin guardar. Mientras se
verifica una nueva activación, Guardar espera al resultado. Desmarcar la casilla
permite guardar sin exigir que pase la verificación. **Cancelar verificación MCP**
cancela la comprobación sin cerrar Configuración. Un complemento listo no necesita
prepararse de nuevo; la comprobación sigue disponible para revisarlo.

La guía consulta el permiso compartido al abrirse sin aceptar ni descartar cambios
pendientes. Abrirla no evita la advertencia de conflicto si el CLI cambió el permiso.
Los pasos para OpenCode y Claude son manuales; el permiso local no significa que el
cliente esté configurado ni conectado. La guía conserva Cerrar fuera del área de
desplazamiento y permite salir de la configuración JSON con Tab.

**Preparar es una operación independiente de Guardar/Cancelar.** Tras confirmar,
la preparación se aplica inmediatamente. Cancelar Configuración conserva un
complemento ya preparado y no guarda cambios en el permiso. Durante la preparación,
**Cancelar preparación MCP**, Escape y cerrar solicitan cancelación segura: la
ventana espera al trabajador sin bloquear el bucle de interfaz. Antes del punto
de confirmación atómico se retira sólo su carpeta temporal; después de ese punto
el complemento permanece preparado. Nunca se borra una instalación previa para
simular una cancelación. Si no se pueden retirar temporales, se informa del fallo
sin prometer limpieza completa. Repetir la preparación de la misma versión
verifica la existente y no crea otra copia ni cambia el permiso.

La ausencia de paquete se muestra como **no incluido en esta compilación**;
no es éxito ni desencadena descargas. El complemento empaquetado actual es para
Windows x64. La compilación base sin complemento sigue disponible; véase
[Distribución Windows](WINDOWS_DISTRIBUTION.md). En desarrollo desde fuente se
mantiene la ruta Python separada descrita abajo.

Un complemento alterado o de identidad incompatible no se ejecuta ni se sobrescribe
silenciosamente. Obtén la distribución verificada correspondiente o consulta soporte
antes de reparar sus archivos. Los hashes comprueban correspondencia con el
manifiesto integrado en el ejecutable de SORTH; no sustituyen la autenticidad del
origen de la distribución ni equivalen a una firma Authenticode. No copies
manifiestos o ejecutables de procedencia desconocida en la carpeta del complemento.

## Permiso local y disponibilidad

**Permitir servidor MCP local** empieza desactivado. **Verificar disponibilidad
local de MCP** comprueba la integridad fuera del hilo de interfaz y ejecuta el
compañero instalado con `--probe`, con límite de cinco segundos para el proceso.
Compara versión, commit, identidad de compilación, SDK y condición empaquetada;
no inicia `stdio`, no usa datos de horarios ni red. En desarrollo ejecuta únicamente
el Python actual con `-B -m src.mcp_adapter.availability`, sin buscar intérpretes
arbitrarios. Nunca se lanza el EXE de la GUI como si fuera Python. Se distingue
paquete/complemento ausente, plataforma/versión incompatible, integridad, carga y
tiempo agotado. Cerrar cancela la verificación; el hash se cancela cooperativamente.

Guardar no inicia el servidor ni configura un cliente/modelo. Cancelar no activa
nada. Guarda los cambios de recursos y el permiso MCP por separado, tanto al
activar como al desactivar, para que una transacción de recursos fallida nunca
revierta una revocación o publique una activación parcial.

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
el cliente. Una generación de permiso cambia al activar o desactivar: volver a activar
MCP no recupera propuestas iniciadas antes de la revocación. No se revocan
copias de resultados entregados previamente.

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

## Desarrollo desde código fuente: activar, probar y desactivar

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

`requirements-mcp.txt` fija `mcp==1.30.0`, versión de la rama 1.x mantenida por el SDK oficial. Se elige explícitamente esa API; no se permite que una resolución sin límite la cambie a 2.x. `requirements-mcp-dev.txt` añade pytest. `requirements-mcp.lock` fija con hashes todas las dependencias del entorno opcional de ejecución y pruebas, resuelto de forma universal para Python 3.12; incluye pytest deliberadamente y las dependencias condicionales Windows `colorama` y `pywin32`. Se genera con `uv pip compile requirements-mcp-dev.txt --python-version 3.12 --universal --generate-hashes --no-build --output-file requirements-mcp.lock`; una resolución sólo Linux omitiría dependencias Windows. Las actualizaciones requieren regenerar el lock, auditar todos sus paquetes (también los condicionales) y repetir pruebas. El lock Windows base de la GUI no incorpora MCP. El compañero empaquetado usa su propio entorno y `requirements-mcp-windows.lock`; no mezcla sus dependencias con la GUI.

## Conectar un cliente elegido por ti

La guía nativa ofrece OpenCode V2, Claude Desktop y ChatGPT. Sólo muestra texto y
copia al portapapeles al pulsar **Copiar configuración**. No escribe archivos de
clientes, abre conexiones, solicita claves ni activa un proveedor. Preparar o
verificar SORTH no prueba la conexión a un host comercial.

### OpenCode V2

En `opencode.jsonc`, combina una entrada bajo **`mcp.servers`**; V2 no coloca el
nombre directamente bajo `mcp`. La guía genera la ruta absoluta exacta:

```json
{
  "mcp": {
    "servers": {
      "sorth-preview": {
        "type": "local",
        "command": ["C:\\RUTA_EXACTA_COPIADA\\SORTH-MCP.exe", "--serve"],
        "disabled": true,
        "protocol": "legacy"
      }
    }
  }
}
```

La ruta mostrada aquí es un marcador, no un comando ejecutable. Usa la copia de la
GUI. `disabled: true` evita conexión automática; después de guardar el permiso en
SORTH, revisa las herramientas y conecta desde `/mcps`. `legacy` corresponde a
las revisiones MCP de 2025 probadas por SORTH. Conserva las entradas existentes y
verifica si la configuración del proyecto reemplaza la global. Véase la
[guía oficial OpenCode V2](https://opencode.ai/v2/docs/mcp-servers).

### Claude Desktop

La guía genera un objeto `mcpServers.sorth-preview` con `command` igual al ejecutable
absoluto y `args: ["--serve"]`. Combínalo con la configuración local desde las
opciones de desarrollador del cliente; no reemplaces otros servidores. Reiniciar
Claude Desktop puede iniciar el proceso, por lo que primero debes guardar el
permiso MCP en SORTH y revisar las aprobaciones del cliente. Consulta la
[configuración local oficial de MCP](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

Claude Desktop también admite extensiones `.mcpb`, incluidos servidores locales,
según su [guía oficial de extensiones](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).
Este flujo de SORTH no genera ni instala un `.mcpb` y no se presenta como extensión
publicada o revisada por Anthropic. La guía JSON y el ejecutable requieren una
aceptación independiente en la versión de Claude Desktop elegida.

### ChatGPT de escritorio: formulario STDIO

Si tu cliente de escritorio muestra **Conectar a un MCP personalizado** con tipo
**STDIO**, usa **Ver guía de conexión → ChatGPT de escritorio (STDIO)**. Requiere
ejecución local en el mismo equipo donde está preparado SORTH. Tras preparar y
verificar el complemento y guardar **Permitir servidor MCP local**, la guía muestra:

- Nombre: `sorth-preview`
- Tipo: `STDIO`
- Comando para iniciar: ruta absoluta verificada de `SORTH-MCP.exe`
- Argumentos: `--serve` (separado del campo de comando)
- Variables del entorno: ninguna requerida

Copia cada valor en su campo; el bloque es una referencia de campos, no JSON ni un
comando de terminal. No uses `SORTH.exe` ni el ejemplo del formulario. La guía no
inventa rutas cuando el complemento no está verificado. En desarrollo desde
fuente, consulta la sección de Python y `cwd` más abajo; no uses la ruta de la GUI.
Guardar o reiniciar el cliente puede iniciar el servidor: revisa sus permisos
primero. No se ha probado la conexión comercial con ChatGPT. Consulta la
[guía oficial de MCP de escritorio](https://learn.chatgpt.com/docs/extend/mcp).

### ChatGPT web: conexión remota

Una ruta local no se pega como URL de servidor. Hace falta una conexión separada:
un endpoint HTTPS con transporte HTTP compatible, o Secure MCP Tunnel que alcance
el servidor `stdio`. El complemento SORTH no proporciona un servidor HTTP. La
configuración de ChatGPT, permisos de organización, autenticación y eventual
exposición de datos deben revisarse y autorizarse aparte. SORTH no crea túneles,
claves, permisos persistentes ni puertos abiertos. Sigue la
[conexión oficial en ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt)
y, si corresponde, la [guía de Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
La disponibilidad depende de cuenta y políticas; no se ha probado ese flujo aquí.

### Otros clientes y desarrollo desde fuente

En la configuración de servidores **locales stdio** de tu cliente, crea una entrada con:

- Nombre: `sorth-preview`
- Comando: ruta absoluta al Python de `.venv-mcp`
- Argumentos: `-B`, `-m`, `src.mcp_adapter.server`
- Directorio de trabajo (`cwd`): ruta absoluta a `SORTH-AI/project_root`
- Variables/credenciales: ninguna requerida
- Si elegiste un archivo alternativo: añade `--preferences`, `/ruta/absoluta/optional-features.json` a los argumentos. La GUI usa su archivo predeterminado; no alterna rutas desde este diálogo.

El formato de configuración depende del cliente. No pegues claves de proveedor en SORTH. Si tu cliente no admite `cwd`, usa su opción equivalente para lanzar desde `project_root`; no inventes una ruta de servidor remoto. Usa un cliente que soporte los esquemas de herramientas MCP y revisa sus permisos antes de compartir datos.

El cliente/host puede usar un modelo local, remoto o ninguno. **SORTH no configura ni verifica un proveedor.** Las cuentas, privacidad, envío de datos, retención y posibles cargos son responsabilidad de tu elección y configuración del cliente/proveedor. La prueba incluida usa el cliente de protocolo del SDK, sin modelo ni gasto de IA. No se ha probado un producto de host comercial ni su flujo de aprobación.

## Cuatro herramientas: aclarar, validar, proponer y devolver Excel

- `prepare_configuration`: recibe los campos conocidos y devuelve todas las preguntas faltantes (`needs_input`) o una configuración validada. El host hace las preguntas en el chat de la IA y vuelve a enviar los datos; el servidor no fuerza un turno de chat ni llama a un modelo.
- `generate_excel`: tras confirmar datos y alcance, genera y valida una propuesta y devuelve un recurso binario XLSX temporal. Reutiliza exactamente los estilos, colores por curso, grillas y tablas del exportador de escritorio, sin la antigua leyenda instructiva.
- `validate_configuration`: valida la estructura, referencias y presupuesto de búsqueda. No ejecuta la búsqueda ni demuestra factibilidad.
- `generate_preview`: reutiliza `SchedulingService` y el validador independiente. Devuelve propuesta completa o parcial, sin guardarla.

Reciben directamente un objeto JSON; el host convierte la conversación en campos explícitos, no el servidor. Los esquemas de entrada permiten omitir campos todavía desconocidos para que ni el cliente ni el SDK bloqueen la devolución de preguntas. Los valores presentes siguen teniendo tipos, rangos y campos cerrados: omitir es válido para preguntar; `null`, capacidades inventadas, campos desconocidos o valores mal formados no lo son. Las funciones puras de dominio conservan su validación estricta.

`prepare_configuration` y `generate_excel` exigen además `classroom_restrictions` explícito (puede ser `[]`) y `scope_confirmed: true`. Este último representa la confirmación del usuario, no un permiso que el modelo deba asumir. Se pregunta por días, disponibilidad y patrón de sesiones: el calendario fijo y las preferencias blandas no pueden sustituir requisitos obligatorios del usuario. `false` devuelve `UNSUPPORTED_CONSTRAINTS`, sin archivo. Una duración es el total semanal de cada grupo; el núcleo divide automáticamente las duraciones superiores a 270 minutos. Un patrón solicitado distinto debe aclararse antes de aceptar este alcance.

Ejemplo sintético de datos completos para `prepare_configuration` o `generate_excel`:

```json
{
  "courses": [{
    "code": "BIO101", "name": "Biología sintética de ejemplo",
    "number_of_groups": 2, "duration_min": 60,
    "required_room_type": "LAB", "size": 20
  }],
  "classrooms": [{"name": "LAB1", "capacity": 30, "room_type": "LAB"}],
  "seed": 42,
  "classroom_restrictions": [],
  "scope_confirmed": true
}
```

Si el usuario dice «Biología BIF401 y Química QIM500, aulas 201 y 202», el host envía únicamente esos datos conocidos. La respuesta incluye `status: "needs_input"`, `next_action: "ask_user_then_resubmit"` y una lista `questions` con `path` y `question`: grupos, duración semanal/sesiones, tamaño, tipo de aula, capacidades, semilla, restricciones y confirmación de alcance. El host pregunta sólo lo necesario: agrupa cuestiones compartidas y datos de cursos en tandas, traduce al idioma de la conversación y no pega una lista extensa de campos. Los valores comunes y patrones de sesiones necesitan confirmación explícita; conserva lo ya respondido y vuelve a enviar el objeto completo. No se genera una propuesta ni un archivo durante esa aclaración. No hay estado de conversación retenido en SORTH.

Para compatibilidad, `validate_configuration` y `generate_preview` siguen aceptando el contrato anterior completo, sin el campo `scope_confirmed`; también devuelven `needs_input` ante campos omitidos. Los hosts nuevos deben empezar por `prepare_configuration` y conservar la confirmación al llamar `generate_excel`.

Consulta los esquemas de `tools/list` como contrato ejecutable (`preview_contract.py` y `preview_clarification.py`). Los identificadores distinguen mayúsculas y minúsculas, tienen hasta 64 caracteres ASCII y sólo letras, números, `_` o `-`; el primer carácter debe ser letra/número. No son rutas. Los tamaños y capacidades son explícitos: 1–1000. No se acepta tamaño cero/desconocido, tipos numéricos coercionados, claves duplicadas ni campos no anunciados.

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
- Resultado del trabajador máximo: 256 KiB para propuestas y 1 MiB para Excel (incluye base64 interno); archivo XLSX máximo: 512 KiB. La lectura del trabajador se interrumpe al alcanzar el límite, sin acumular salida ilimitada. El transporte MCP incluye contenido JSON estructurado y copia textual compatible; su trama puede ser mayor. No se truncan silenciosamente asignaciones.
- Tiempo del trabajador: 10 segundos desde su arranque. Cada generación usa un subproceso efímero; al vencer el plazo o cancelar, se termina y espera su salida. El tiempo de creación/recolección depende del SO y no es una garantía de tiempo real. El transporte usa I/O crudo en hilos daemon acotados (una lectura y una escritura); al terminar el proceso no espera indefinidamente que el host cierre stdin o consuma stdout. Una operación de pipe bloqueada puede sobrevivir hasta que el SO cierre los descriptores al salir, sin mantener vivo el proceso.

### Resultado y errores

Faltan datos: `status: "needs_input"`, preguntas estructuradas y ninguna generación; es una respuesta normal, no un error.

Éxito de validación/propuesta: `status` es `validated`, `complete` o `partial`, con `normalized`, `session_count`, `candidate_upper_bound`, `assignments`, `pending`, `notices` y `capabilities`. Cada asignación incluye grupo, curso, aula, día 1–6 y minutos inicial/final. Cada pendiente incluye identificador y razón del núcleo. Un resultado parcial **no prueba que el problema sea imposible**. Un resultado completo sólo satisface las reglas declaradas, no restricciones ausentes. Revisa la configuración normalizada y los límites antes de usar una propuesta.

Errores de herramientas: `isError=true` y `structuredContent.error` con `code`, `path`, `message`. Ejemplos: `UNSUPPORTED_CONSTRAINTS`, `OUTPUT_LIMIT`, `INVALID_TYPE`, `UNSUPPORTED_FIELD`, `UNKNOWN_REFERENCE`, `SESSION_LIMIT`, `CANDIDATE_LIMIT`, `BUSY`, `TIMEOUT`. Mensajes y rutas estructurales no repiten valores rechazados. Cancelación MCP puede no producir respuesta al request cancelado; el cliente debe dejar de esperarla según el protocolo. No se promete deshacer datos, porque ninguna operación los escribe.

### Entrega de Excel y compatibilidad del host

`generate_excel` devuelve `preview` con el resultado completo y `artifact` con URI opaca, nombre fijo `sorth-preview.xlsx`, MIME XLSX, tamaño, SHA-256, caducidad y `delivery: "mcp_resource"`. El contenido MCP incluye un `resource_link`; `resources/read` devuelve `BlobResourceContents.blob` en base64. No se inventa un `file_id` de proveedor ni una URL HTTP. Los nombres suministrados nunca son rutas de archivo.

El cliente debe leer el recurso en **la misma conexión/proceso antes de cinco minutos**, decodificar los bytes y usar su función de guardar o adjuntar. La representación como descarga es decisión del host: soportar herramientas MCP no garantiza adjuntos XLSX visibles. No se ha aceptado todavía este flujo en OpenCode, Claude o ChatGPT reales. La IA no debe afirmar «archivo adjunto» hasta que su host haya confirmado la entrega. ChatGPT tiene extensiones e integración de archivos propias; este recurso stdio por sí solo no configura una integración remota ni convierte el archivo en un adjunto nativo.

Se conservan como máximo cuatro recursos de 512 KiB en memoria del proceso. Un quinto elimina el más antiguo; la caducidad y cualquier cambio de generación del permiso se purgan al siguiente acceso. Desactivar y reactivar MCP no recupera recursos anteriores. Cerrar el proceso los elimina. Cada lectura comprueba el permiso de nuevo. Recursos desconocidos, caducados o revocados fallan con un mensaje genérico, sin abrir archivos ni revelar rutas. El host puede conservar copias que ya recibió; revocar SORTH no las borra.

Excel contiene las grillas de aulas con sesiones asignadas, `Asignaciones`, `Por Aula`, `Estado` y `Pendientes`. Estado conserva `complete`/`partial`, recuentos y límites del resultado; los pendientes incluyen sus razones y nunca aparecen como sesiones asignadas. Las fórmulas y enlaces procedentes de etiquetas no se ejecutan. No se omiten sesiones silenciosamente para caber en el límite. Esta exportación cubre toda la solicitud explícita; no accede a filtros ni a la sesión activa de la GUI.

## Arquitectura, privacidad y ACID

`preview_contract`, `preview_clarification` y `schedule_preview` son casos de uso sin SDK, Qt, pandas, Excel ni SQLite. Un puerto pequeño permite sustituir la generación en pruebas. `SchedulingService` carga Excel de forma diferida sólo para el flujo de archivo existente; los datos proporcionados usan el planificador real, sin duplicarlo. El caso de uso conserva grupos y aulas canónicos independientes del puerto y rechaza grupos omitidos/alterados; una población vacía devuelta por un adaptador no puede convertirse en un éxito completo. El adaptador traduce herramientas/errores; un ejecutor efímero limita generación y cancelación. No hay llamadas a modelos, acceso a archivos arbitrarios, comandos elegidos por el usuario ni acceso a sesión activa. Sólo el trabajador de Excel compone el caso de uso puro con `ScheduleExporter`; pandas se carga únicamente en la ruta CSV de escritorio. openpyxl 3.1.5 y et-xmlfile 2.0.0 están fijados con los mismos hashes y avisos revisados que la aplicación, en el entorno MCP separado. La serialización mantiene también los XML intermedios en memoria (guardar un Workbook en BytesIO por sí solo crearía temporales de openpyxl).

El host conoce lo que envía y recibe (incluidos nombres, cantidades y horarios). Puede enviarlo a su proveedor según su configuración. Usa datos sintéticos o códigos mínimos hasta revisar permisos institucionales. Los nombres se devuelven como datos; cualquier host que los convierta en instrucciones debe aplicar sus propias defensas contra inyección. SORTH no evalúa código, URLs ni órdenes en ellos. Se suprimen trazas/datos personales en diagnósticos; stdout es sólo protocolo. Python lee su código y dependencias; `-B` impide cachés de bytecode. No se afirma que el proceso esté aislado por sandbox ni que un host externo carezca de otras herramientas.

La base SQLite y sus transacciones no se importan ni se abren en este MVP. ACID sigue siendo responsabilidad del repositorio transaccional de la aplicación. Una propuesta o llamada de modelo **no es una transacción ACID**. Guardar/aplicar a la sesión requeriría otro diseño y revisión: autorización explícita, versión de sesión y concurrencia, transacción atómica corta, validación, aislamiento, durabilidad, rollback y pruebas de fallos. Nunca mantener una transacción abierta esperando inferencia.

## Pruebas y compatibilidad

```sh
# En el entorno opcional, sin instalar Qt/pandas/modelos:
.venv-mcp/bin/python -B -m pytest tests/test_mcp -q
# En el entorno base, los casos puros siguen corriendo; el módulo stdio se omite:
python -m pytest -q
```

Las pruebas cubren cliente SDK real `initialize`/`tools/list`/`tools/call`/`resources/read`, aclaración sin inferir datos, apertura real de XLSX completos y parciales, estilo compartido, ausencia de fórmulas y escritura a disco, caducidad/evicción/revocación de recursos, contrato JSON, cancelación por cable, cierre SIGINT con stdin abierto y stdout bloqueado, límites, fallo/timeout y posterior recuperación, LAB estricto, resultados parciales, reproducibilidad frente al servicio directo, texto adversario y directorios de sesión sin cambios. Un proceso `python -B -S` verifica casos de uso sin paquetes externos. Se negocian y prueban las revisiones MCP `2025-06-18` y `2025-11-25` con SDK 1.30.0. No se presupone compatibilidad con borradores o revisiones posteriores; el host debe negociar una soportada. El flujo CI opcional tiene jobs aislados Linux y Windows/Python 3.12: instala el lock con hashes, exige el SDK presente y Qt/pandas/modelo ausentes, comprueba cierre transitivo de dependencias según plataforma y ejecuta las pruebas stdio reales; la GUI base mantiene su entorno sin SDK MCP. El flujo Windows empaqueta el compañero en un entorno separado y verifica el artefacto; la aceptación nativa sigue dependiendo del resultado real de ese flujo. Los casos POSIX de señal SIGINT y backpressure de descriptores se omiten explícitamente en Windows porque sus señales y consola son distintas; no se presentan como pruebas Windows aprobadas. La negociación, listado, llamadas, cancelación MCP, timeout, recolección de subprocesos y todos los demás contratos se ejecutan en ambos jobs. La ejecución nativa Windows queda pendiente del resultado de ese CI; descargar sus wheels desde Linux no equivale a ejecutarlos. Hosts comerciales: no probados aquí.

### Aceptación manual de consola Windows

Antes de afirmar cierre nativo por teclado, abre una consola Windows real, ejecuta el comando documentado, deja el proceso esperando stdin y pulsa Ctrl+C. Debe volver al prompt sin cerrar primero stdin y sin dejar procesos Python hijos. Después, en el host MCP elegido, genera/cancela una propuesta y cierra el host; comprueba que servidor y trabajador finalizan y que la sesión de la GUI queda intacta. Verifica también un host que deja de consumir stdout. El CI de pipes/protocolo no sustituye esta aceptación de consola/host; regístrala por separado con versión de Windows, Python, host y commit.

Base de trabajo: correcciones de validación y persistencia #2/#3, no un reemplazo de ellas. La aplicación incluye [indicadores explicables de calidad](../docs/user/QUALITY_METRICS.md) y [exportación PDF bilingüe](../docs/user/PDF_EXPORT_NOTES.md); este contrato MCP incluye aclaración, validación, propuestas y Excel temporal, sin exponer los indicadores ni PDF. No modifica la sesión, las métricas ni los archivos de la GUI.

Fuentes oficiales consultadas al implementar el adaptador (2 de octubre de 2026); guías de clientes revisadas el 3 de octubre de 2026:

- [SDK Python v1.30.0 y mantenimiento de 1.x](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/README.md)
- [Servidor de bajo nivel y resultado estructurado, v1.30.0](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/docs/low-level-server.md)
- [Herramientas MCP 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Cancelación MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)

Fuentes oficiales revisadas para aclaración y archivos (3 de octubre de 2026):

- [Herramientas, contenido estructurado y enlaces de recursos MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Recursos binarios y control de acceso MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [Servidor MCP y metadatos de instrucciones en OpenAI](https://developers.openai.com/plugins/build/mcp-server)
- [Extensiones OpenAI para archivos e interfaces](https://developers.openai.com/plugins/build/extensions)
