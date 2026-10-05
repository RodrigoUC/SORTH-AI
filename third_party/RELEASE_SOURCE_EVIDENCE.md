# Evidencia de fuentes y avisos de la primera release

Revisión técnica del 5 de octubre de 2026. Esta evidencia no certifica cumplimiento legal ni identifica por sí sola los bytes del instalador final.

## Qt y PyQt

Los 20 DLL/plugins Qt del inventario PE de la revisión `b9fc583d4ece5c91b36892acb40413f5cb8aa88d` tienen correspondencia entre el wheel Windows fijado y los paquetes oficiales Qt 6.11.2 MSVC. Se compararon 253 archivos DLL/QM comunes y coincidieron todos, incluidas 217 traducciones. La comparación es proveedor → wheel; falta repetirla contra los archivos del paquete final de SORTH.

Los paquetes oficiales conservan SBOM de plataforma, opciones y resúmenes de configuración. Identifican CMake 3.30.5, MSVC 19.44.35227.0 y las fuentes/configuración seleccionadas. Los archivos de implementación y construcción enumerados por los SBOM corresponden a las fuentes archivadas, considerando LF/CRLF; las diferencias restantes se limitan a metadatos `.tag` y archivos Git auxiliares.

El wheel PyQt6 6.11.0 identifica PyQt-builder 1.19.1, SIP 6.15.3, ABI 13.8 y su configuración de módulos. Se conservan las fuentes originales y las interfaces instaladas; dos interfaces difieren únicamente en el orden de sus inclusiones. No se ejecutó una reconstrucción de Qt/PyQt. La reproducción bit a bit no se presenta como requisito universal ni como resultado verificado.

Los SBOM específicos del proveedor declaran BSD-3-Clause como alternativa de código abierto para las traducciones QM. No se infiere LGPL automáticamente de la licencia general de otros módulos. Se conservan también las traducciones editables.

El flujo de release prepara `THIRD-PARTY-SOURCES.tar.gz` mediante `project_root/tools/prepare_release_sources.py`, usando un manifiesto de URLs, tamaños y SHA-256 fijados. Conserva ocho archivos fuente originales, configuración/SBOM, interfaces y avisos, con sumas de verificación internas. Mesa/LLVM se entregan como materiales de sus versiones identificadas, sin afirmar correspondencia exacta con la compilación histórica. El hash del paquete final se calcula y verifica durante la preparación de la candidata. Este documento no afirma que esté publicado. Antes de redistribuir binarios, añadir junto a ellos instrucciones y acceso efectivo a estas fuentes, las fuentes exactas de SORTH y los demás componentes pertinentes. Verificar también los avisos y la sustitución de bibliotecas compartidas compatibles en la distribución final.

Fuentes oficiales:
- https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_6112/qt6_6112_msvc2022_64/qt.qt6.6112.win64_msvc2022_64/
- https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_6112/qt6_6112_msvc2022_64/qt.qt6.6112.addons.qtimageformats.win64_msvc2022_64/
- https://download.qt.io/archive/qt/6.11/6.11.2/submodules/
- https://raw.githubusercontent.com/qt/qt5/v6.11.2/coin/platform_configs/cmake_platforms.yaml
- https://pypi.org/project/PyQt6/6.11.0/
- https://pypi.org/project/PyQt6-Qt6/6.11.2/

## Avisos complementarios

- `licenses/cpython-3.12.10-embed-amd64-LICENSE.txt`: licencia completa Windows del paquete oficial Python, incluidas sus condiciones Microsoft. Los dos VCRUNTIME de la raíz inventariados coinciden byte por byte con ese paquete. Conservar las condiciones aplicables; esta correspondencia no cubre automáticamente las copias Qt o NumPy/pandas.
- `licenses/qt-v6.11.2-llvmpipe-NOTICES.txt`: textos originales de la atribución oficial Qt para `opengl32sw.dll` (MIT/Boost). La atribución no identifica el hash ni la receta histórica de Mesa 11.2.2. No convertir esa incertidumbre de reconstrucción en una obligación automática de entregar fuentes bajo una licencia copyleft no demostrada para ese componente.
- `licenses/llvm-3.6.2-MD5-NOTICES.txt`: avisos originales MD5 que complementan los textos LLVM 3.6.2 previamente conservados y nuevamente comparados con el archivo oficial. No se afirma una auditoría exhaustiva de objetos enlazados.

Fuentes:
- https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
- https://raw.githubusercontent.com/python/cpython/v3.12.10/PC/crtlicense.txt
- https://doc.qt.io/qt-6.11/qt-attribution-llvmpipe.html
- https://raw.githubusercontent.com/qt/qtdoc/v6.11.2/doc/src/legal/licenses.qdoc
- https://releases.llvm.org/3.6.2/llvm-3.6.2.src.tar.xz

## Runtimes Microsoft: alcance pendiente

Microsoft contempla distribuidores autorizados por sus proveedores; una licencia independiente de Visual Studio no es el único fundamento posible. La cadena de origen de las cinco copias Qt está verificada contra PyQt-builder 1.19.1. Sin embargo, los materiales revisados no documentan todavía la autorización/condiciones Microsoft aplicables a esas cinco copias y a las dos de NumPy/pandas. Falta documentar una vía de redistribución aplicable y conservar sus condiciones. Esta falta de evidencia no demuestra distribución ilícita ni implica comprar una licencia. Los runtimes no se relicencian bajo la GPL/LGPL/BSD de sus paquetes anfitriones.

- https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/
- https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution

Las comprobaciones de procedencia y licencias se deben reconciliar con los archivos realmente distribuidos. La firma, SmartScreen, aceptación manual y autorización de publicación permanecen como comprobaciones separadas.
