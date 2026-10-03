# Avisos de terceros / Third-party notices

Este directorio conserva textos de licencia y avisos originales extraídos de los **29 wheels exactos** del lock Windows. Se verificó el SHA-256 de cada wheel contra `project_root/requirements-windows.lock`; `wheel-inventory.json` registra versiones, hashes, metadatos y rutas/hashes de los avisos internos. El hash del archivo lock se calcula como texto UTF-8 con saltos LF para ser estable ante la conversión CRLF de Git en Windows; los hashes de los wheels y avisos de origen se calculan sobre sus bytes originales. No se instalaron ni ejecutaron wheels durante la recopilación.

Los textos de `licenses/` están delimitados por origen; su contenido no se sustituye por la licencia de SORTH. Incluyen avisos transitivos y vendorizados de NumPy, Pillow, pip y setuptools, además de las fuentes Vera de ReportLab. `dejavu-font.txt` conserva el aviso del DejaVu incluido en `tools/fonts`; `cpython-3.12.10.txt` proviene del [LICENSE oficial del intérprete de referencia](https://github.com/python/cpython/blob/v3.12.10/LICENSE).

## Reproducir la recopilación

Desde `project_root`, con todos los wheels del lock en un directorio limpio:

```sh
python tools/collect_license_notices.py --wheel-dir RUTA_A_WHEELS --output ../third_party
```

El script falla ante un wheel modificado, inesperado, repetido o faltante. Comprueba el diff antes de publicar cambios; los avisos adicionales de CPython y DejaVu se conservan por separado y deben actualizarse al cambiar esas versiones.

## Interpretación

Este inventario abarca el entorno de construcción, no sólo el ejecutable. Por ejemplo, pytest y pip pueden no incluirse en el binario. Mantener sus avisos aquí no declara que se distribuyan sus programas. No es un SBOM del ejecutable final ni una certificación legal: faltan inventariar los DLL/plugins realmente recolectados, contrastarlos con los componentes de Qt y revisar los runtimes que agrega PyInstaller.

La metadata LGPLv3 del wheel PyQt6-Qt6 no identifica por sí sola todas las licencias de código incorporado en sus DLL. Antes de una release, la [lista oficial de terceros de la versión de Qt](https://doc.qt.io/qt-6/licenses-used-in-qt.html) debe contrastarse con los módulos distribuidos y conservar los avisos aplicables. No basta con el LICENSE del wheel.

Consulta [la revisión de licencias](../docs/LICENSING_REVIEW.md) y [la entrega de fuentes](../docs/SOURCE_AVAILABILITY.md). Los iconos y datos de ejemplo de esta edición son originales/sintéticos; los antiguos documentos académicos no se incluyen.

## Suplemento nativo verificado

[Native source evidence](NATIVE_SOURCE_EVIDENCE.md) conserva avisos originales y
hashes de fuentes Qt/Mesa/LLVM, la lista pública de sufijos editable con cadena
verificada hasta Qt6Network.dll y recursos de versión de los nueve runtimes
Microsoft. Es evidencia complementaria; las obligaciones y bloqueos de entrega
de fuentes/configuración y permisos siguen indicados explícitamente.
