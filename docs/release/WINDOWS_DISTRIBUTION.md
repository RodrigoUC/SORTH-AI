# Distribución de SORTH para Windows

## Objetivo y límites

El programa debe usarse con las protecciones de seguridad activas. Un cambio de empaquetado no demuestra que un archivo sea seguro ni garantiza que desaparezcan las alertas. Distinguir:

- **SmartScreen / aplicación no reconocida:** reputación del archivo y del editor.
- **Defender / amenaza detectada:** requiere investigar el nombre de la detección y el archivo exacto; puede ser una detección real o un falso positivo.
- **Smart App Control o política institucional:** puede bloquear una aplicación por sus propias reglas. El responsable de TI debe evaluar la distribución.

No recomendar desactivar antivirus, crear exclusiones ni omitir advertencias. Conservar el mensaje exacto, versión del producto de seguridad, versión de SORTH, origen de descarga y SHA-256 del archivo afectado.

## Preparación y compilación

Compilar en Windows desde un entorno virtual limpio, como usuario estándar. Revisar las versiones de Python, dependencias y PyInstaller antes de instalarlas. No reutilizar los ejecutables históricos del repositorio como resultado de una nueva compilación.

```powershell
# Python 3.12.10 x64, Windows
python -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-windows.lock
.\.venv-build\Scripts\python.exe -m pip check
.\.venv-build\Scripts\python.exe -m pytest -q
.\.venv-build\Scripts\python.exe tools/build_manual.py --output build/docs/MANUAL_USUARIO.pdf
```

El lock de Windows fija 29 paquetes transitivos y sus hashes de wheels para CPython 3.12 x64; incluye pruebas, PDF y PyInstaller. `requirements.txt` fija las dependencias directas de ejecución; `requirements-dev.txt` añade pruebas y documentación. `requeriments.txt` conserva el nombre histórico como alias de desarrollo. No instalar el lock de Windows en Linux o macOS.

La resolución de dependencias es reproducible; esto no promete ejecutables idénticos byte por byte ni demuestra ausencia de vulnerabilidades. La imagen `windows-2025` del runner sigue recibiendo actualizaciones. Guardar el inventario y revisar cambios del lock antes de aprobarlos.

```powershell
.\build_exe.ps1
# Alternativa opcional de archivo único:
.\build_exe.ps1 -OneFile
# Sólo desarrollo: GUI sin paquete MCP (la interfaz informa que no está incluido):
.\build_exe.ps1 -WithoutMcp
```

La salida predeterminada es `dist/SORTH/SORTH.exe`, acompañada de sus dependencias. Distribuir **toda** la carpeta `dist/SORTH` en un ZIP; extraerla completa antes de abrir el programa. El modo opcional de archivo único genera `dist/SORTH.exe`. Si existen ambos, no confundir el ejecutable antiguo con la salida de la compilación actual.

La compilación predeterminada ejecuta primero `build_mcp.ps1`: descarga wheels
verificados y crea un entorno aislado para el compañero. No instala MCP en el
entorno base de la GUI. Esa descarga ocurre en el equipo de compilación, no al
preparar el complemento desde la aplicación del usuario. `-McpPrepared` permite
reutilizar el paquete previamente generado y verificado, como hace CI.
`-WithoutMcp` es una alternativa explícita para desarrollo, no el artefacto de
revisión completo. Invocar directamente `SORTH.spec` conserva la GUI base sin el
paquete y tampoco demuestra aceptación del complemento.

El script detiene errores de compilación y deshabilita UPX. Usa metadatos de `windows_version_info.txt`; actualizar la versión con cada publicación. Estos metadatos no sustituyen una firma digital. La salida local del script no está firmada automáticamente.

El modo de carpeta facilita inspeccionar las dependencias y evita la extracción temporal propia del modo de archivo único. Es una elección de empaquetado y diagnóstico; no una solución garantizada para alertas de antivirus.

## Compañero MCP aislado

`requirements-mcp-build.txt` declara SDK MCP 1.30.0, openpyxl 3.1.5, PyInstaller y pip; su
`requirements-mcp-windows.lock` fija 40 paquetes, cada uno con el hash SHA-256 del
wheel exacto para CPython 3.12/Windows x64. Es independiente del lock base de 29
paquetes y del lock universal de pruebas de MCP. El compañero no incluye Qt,
pandas, pytest ni clientes de modelos. Incluye openpyxl/et-xmlfile para la exportación XLSX en memoria, con los mismos hashes revisados de la aplicación. `third_party/mcp/` conserva su
inventario y avisos de licencias; se verifican junto con los wheels antes de
redistribuir.

`build_mcp.ps1` genera `SORTH-MCP.exe` y su carpeta de dependencias, empaquetados
como `optional/mcp-component.zip`. `tools/mcp_payload.py` vincula versión, commit,
lista/tamaño/hash de archivos y hash del ZIP. `build_exe.ps1` incorpora ese paquete
dormido y el manifiesto de confianza compilado en la GUI. La GUI nunca importa el
SDK para abrir Configuración. `--probe` y `--serve` son entradas del compañero;
no son argumentos para convertir la GUI en un intérprete Python.

El botón **Preparar complemento MCP** copia sólo el paquete de esa compilación a
una carpeta de usuario versionada tras confirmar, valida integridad y ejecuta
`--probe` antes de aceptar. No requiere Python instalado, red ni pip en el equipo
final. No cambia el permiso predeterminado OFF, inicia stdio ni configura clientes.
Consulta [MCP opcional](../../project_root/MCP_OPTIONAL.md) para cancelación, errores y guías de conexión.

El workflow de Windows añade `tools/frozen_mcp_smoke.py`: revisa el manifiesto
compilado, ausencia del SDK en la GUI, preparación repetida, paquete corrupto,
permiso OFF, handshake/listado/validación/generación, cancelación por protocolo,
recuperación y revocación, con rutas Python eliminadas del PATH del proceso hijo.
Estos son controles configurados, **pendientes de ejecución real en Windows**
hasta que el workflow del commit concreto termine. Ejecutarlos en CI no equivale
a probar un Windows limpio sin Python o un host comercial; registrar ambas
aceptaciones por separado. No hay publicación ni firma automática.

## Lista de verificación de publicación

1. Ejecutar las pruebas en entornos limpios separados para GUI y compañero MCP. Guardar commit, versiones, arquitectura, registro de compilación y lista de dependencias. Revisar vulnerabilidades y licencias de las dependencias antes de redistribuir.
2. Generar desde código revisado. Excluir sesiones personales, datos privados, cachés y archivos de desarrollo del paquete. La configuración y ejemplos incluidos deben estar autorizados para distribución.
3. Probar la carpeta empaquetada como usuario estándar en Windows, sin Python instalado: abrir, importar un Excel, generar, exportar y cerrar/reabrir la sesión. En Configuración, probar confirmación/cancelación de MCP, preparación, repetición, verificación, permiso OFF/ON/OFF y conexión manual al host elegido. Mantener Defender actualizado y activo.
4. Para publicación con editor verificado, el propietario debe obtener una identidad/certificado de firma confiable o un servicio de firma, completar su validación y aprobar cualquier coste. Firmar con Authenticode y sello de tiempo según el proveedor, usando SHA-256. Nunca guardar claves privadas o contraseñas en este repositorio. No modificar los binarios después de firmarlos.
5. Verificar la firma final con el SDK de Windows: `signtool verify /pa /all /v dist\SORTH\SORTH.exe`. Si se publica sin firma, indicarlo expresamente; no declarar editor verificado. Conservar las firmas de las dependencias de terceros.
6. Analizar la distribución final con Defender y registrar el resultado y las versiones. Descargar el paquete desde su ubicación de publicación prevista en un Windows limpio para verificar también la experiencia real de SmartScreen. Una prueba local no reproduce necesariamente la reputación de una descarga.
7. Generar el ZIP después de firmar; calcular y publicar SHA-256 del ZIP final junto con versión, notas y procedencia. Una suma de verificación comprueba integridad, no ausencia de malware. No cambiar los archivos tras calcularla.
8. Generar el manual PDF desde `docs/user/MANUAL_USUARIO.md` (en la raíz del repositorio) en cada compilación. Este repositorio limpio no incluye PDF, EXE/ZIP, cachés, sesiones ni el historial del proyecto anterior. No deben añadirse como compilaciones nuevas.

## Compilación de revisión en GitHub Actions

`Windows review build` ejecuta el commit exacto del PR en Windows x64, con permisos de lectura y acciones fijadas a SHA. Instala el lock base con verificación de hashes, ejecuta la suite, genera el PDF y prepara el compañero en un entorno aislado con su propio lock. Compila la GUI con `-McpPrepared`, ejecuta los controles del compañero y abre la GUI en Qt offscreen. La prueba importa el Excel incluido, genera en QThread, exporta Excel/CSV, verifica SQLite y captura la ventana, usando una sesión temporal separada.

Qt offscreen en Windows usa una base de fuentes FreeType que no descubre por sí
sola las fuentes del escritorio. El CI establece `QT_QPA_FONTDIR` con la carpeta
especial de fuentes instaladas de Windows antes de iniciar Qt, y registra sólo
la ruta y el número de archivos compatibles en `qt-font-discovery.json`. No copia,
redistribuye ni sube fuentes del sistema. La aplicación normal no cambia su familia
tipográfica ni su plataforma Qt. Esta ruta se basa en el código oficial de Qt
6.11.2: [offscreen](https://github.com/qt/qtbase/blob/v6.11.2/src/plugins/platforms/offscreen/qoffscreenintegration.cpp),
[FreeType](https://github.com/qt/qtbase/blob/v6.11.2/src/gui/text/freetype/qfreetypefontdatabase.cpp)
y [directorio de fuentes](https://github.com/qt/qtbase/blob/v6.11.2/src/gui/text/qplatformfontdatabase.cpp).

Antes de aceptar capturas, el smoke exige una base de fuentes no vacía, cobertura
de caracteres ingleses/españoles en las fuentes reales de los controles visibles
y rásteres de texto con tinta y formas diferentes. Guarda `text-rendering-*.json`
y `.png` al inicio, en ambos idiomas y en cada reinicio. Un PNG no vacío por sí
solo no pasa el control: los cuadros de glifos ausentes deben causar fallo. Los
20 pasos funcionales siguen vigentes. Revisar también las capturas reales del
paquete y del instalado; esta comprobación no es OCR ni garantiza todos los
caracteres de datos de usuario. La aceptación visual de escritorio nativo Windows
(con su plataforma `windows`, DPI y fuentes reales) continúa pendiente por separado.

Antes de medir o capturar una pantalla, el smoke entrega solamente los eventos
nativos `LayoutRequest` pendientes hasta estabilizar la geometría. Así evita
pintar una etiqueta nueva con el ancho anterior de «Generando…» o del otro idioma.
No bombea entradas, temporizadores ni señales del trabajador, y no cambia fuentes,
textos, tamaños de ventana o reglas de la interfaz normal. El informe registra los
límites de contenido y texto de cada botón visible; una etiqueta que realmente
no cabe, o una geometría que no se estabiliza, hace fallar el smoke. Esta prueba
acotada no certifica todos los encabezados de tabla ni la accesibilidad completa.

La misma prueba usa un perfil sintético separado para apariencia, QSettings y
preferencias opcionales; nunca escribe preferencias normales del usuario. Idioma,
movimiento y lectura de preferencias heredadas reciben un QSettings con archivo
INI explícito y fallbacks desactivados; no dependen del formato predeterminado de
Qt ni del registro de Windows. El informe registra las rutas efectivas de cada
consumidor dentro del perfil sintético. Comprueba
los temas integrados con Vista previa/Cancelar/Aplicar, importa un tema JSON local,
rechaza contenido no permitido y conserva los bytes de la sesión, permisos MCP,
idioma y reducción de movimiento. Después inicia dos procesos nuevos del mismo
`SORTH.exe`: uno recupera el tema personalizado sin el archivo importado, y otro
muestra Original claro con aviso al encontrar preferencias de apariencia dañadas,
sin reescribirlas. Los informes `theme-*-restart.json` y capturas acompañan a
`smoke-result.json`. También se ejecuta esta secuencia desde la aplicación instalada.

Estos controles desde `python gui_app.py --smoke-test` son evidencia **de fuentes**:
los informes deben indicar `frozen: false`. Sólo ejecutar el EXE construido en
Windows y comprobar `frozen: true` en el informe principal y ambos reinicios valida
ese paquete. Qt offscreen sigue sin sustituir la revisión visual, DPI, SmartScreen
ni la aceptación en una PC limpia. No se conecta un proveedor de IA ni se habilita MCP.

Después crea un ZIP **sin firma**, `SHA256SUMS.txt`, un inventario con el commit y el manual actual. Los artefactos `SORTH-windows-review-*` y `SORTH-windows-checks-*` se conservan siete días en la ejecución de Actions. Se necesitan permisos de lectura de la ejecución para descargarlos. No se crea una GitHub Release, no se firma, no se despliega y no se modifica la protección de Windows.

Las pruebas automatizadas no sustituyen probar interactivamente en un Windows limpio sin Python, con un usuario estándar y las protecciones activas. En particular, no se presentan como análisis de Defender ni prueba de reputación de descarga SmartScreen.

Para una prueba local aislada, use una carpeta de resultados nueva:

```powershell
.\dist\SORTH\SORTH.exe --smoke-test --smoke-output C:\Temp\SORTH-review-nueva
.\.venv-build\Scripts\python.exe tools/package_windows.py --commit (git rev-parse HEAD)
```

La herramienta de empaquetado rechaza bases de sesión y cachés dentro de la carpeta de la aplicación. La suma de verificación corresponde al ZIP final; `build-info.json` deja explícito que no está firmado.

### Actualizar el lock conscientemente

Descargar wheels para CPython 3.12/Windows x64 desde el índice aprobado, con versiones directas revisadas. Incluir explícitamente `pefile`, `pywin32-ctypes`, `tzdata` y `colorama`: un `pip download --platform` ejecutado en Linux puede evaluar marcadores contra el host. Luego ejecutar `python tools/lock_windows.py --wheel-dir RUTA --output requirements-windows.lock`. El generador comprueba las dependencias con marcadores de Windows y calcula SHA-256 de cada wheel. Revisar el diff y ejecutar el CI de Windows antes de aceptar el nuevo lock. Para el compañero, usa su manifiesto y lock separados con `--scope mcp --output requirements-mcp-windows.lock`; revisa también `third_party/mcp/` y ejecuta `tools/security_review.py companion-dependencies`. No agregues el SDK al lock base.

## Si aparece una detección

Detener la publicación del archivo afectado. Revisar procedencia, entorno de compilación y dependencias antes de afirmar que es un falso positivo. Si la revisión indica una detección incorrecta, el propietario puede enviar el archivo exacto a [Microsoft Security Intelligence](https://www.microsoft.com/en-us/wdsi/filesubmission), como desarrollador, con nombre de detección, SHA-256, versión de Defender y explicación del comportamiento legítimo. El envío comparte el archivo con Microsoft y debe autorizarlo el propietario. Respetar los límites de tamaño que muestre el portal; no enviar datos de usuarios. Conservar el resultado del análisis y repetir la validación de la distribución final.

La revisión de una detección de malware no equivale a obtener reputación SmartScreen. Microsoft indica que una aplicación firmada nueva todavía puede mostrar advertencias y que los certificados EV ya no conceden reputación inmediata. Mantener una identidad de editor consistente ayuda; no existe una promesa de ausencia de alertas. La distribución mediante Microsoft Store es otra opción que requiere cuenta, preparación del paquete y revisión del propietario.

## Fuentes primarias

- [Reputación SmartScreen para desarrolladores](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
- [SignTool y verificación Authenticode](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool)
- [Envío de archivos a Microsoft](https://learn.microsoft.com/en-us/defender-xdr/submission-guide)
- [Funcionamiento de PyInstaller: carpeta y archivo único](https://pyinstaller.org/en/stable/operating-mode.html)
- [Opciones de PyInstaller, UPX y recursos de versión](https://pyinstaller.org/en/stable/usage.html)
