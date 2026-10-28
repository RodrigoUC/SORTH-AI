# Fuentes correspondientes y cierre de distribución

La GPL del código propio está elegida. La entrega de fuentes de cada binario sigue siendo una tarea de release, no una promesa de que un paquete anterior ya la cumpla.

## Material verificado

- **SORTH:** cada ZIP de revisión registra `source_commit`. La fuente debe corresponder a ese commit exacto e incluir configuración, scripts y modificaciones necesarias para construirlo; no usar sólo `main` como referencia.
- **PyQt6 6.11.0:** el [paquete oficial de la versión en PyPI](https://pypi.org/project/PyQt6/6.11.0/#files) ofrece `pyqt6-6.11.0.tar.gz`. SHA-256 publicado de la fuente: `45dd60aa69976de1918b5ced6b4e7b6a25abd2a919ecef5fd5826ecc76718889`. El generador preserva esa fuente en el paquete de terceros verificado. La [evidencia de preparación](evidence/release-readiness-3.0/REPORT.md) identifica la candidata comprobada; no acredita publicación ni acceso permanente.
- **Qt 6.11.2 / PyQt6-Qt6:** el wheel auditado declara LGPLv3. La fuente de PyQt no es la fuente de Qt. Se preservan fuentes, configuración/SBOM oficiales y correspondencia proveedor → wheel; véase [la evidencia detallada](../third_party/RELEASE_SOURCE_EVIDENCE.md). El gate de candidata compara los bytes Qt/PyQt efectivamente distribuidos contra esa matriz, incluidos todos sus archivos obligatorios. Quedan la revisión de avisos/condiciones y la publicación con acceso efectivo.
- **CPython 3.12.10:** [release oficial con fuentes](https://www.python.org/downloads/release/python-31210/) y licencia preservada en `third_party/licenses/cpython-3.12.10.txt`. Revisar además las bibliotecas nativas/runtimes que incluya el ejecutable Windows.
- **Otros wheels:** `third_party/wheel-inventory.json` identifica versiones, hashes, procedencia y avisos disponibles; inspeccionar el ejecutable para determinar qué componentes llegan al usuario y qué términos se aplican.

## Checklist por release

- [ ] Guardar un inventario de archivos del binario final y mapear DLL, plugins y módulos a versiones/licencias, incluyendo componentes transitivos y runtime de Python/Windows.
- [ ] Conservar junto al ZIP el código fuente de SORTH y componentes cubiertos que correspondan, con scripts/configuración/parches necesarios. Revisar la modalidad de cumplimiento aplicable de GPL/LGPL y los derechos de reemplazo/modificación pertinentes.
- [ ] Verificar descarga y hashes de las fuentes, correspondencia con el binario y persistencia del acceso. Un artefacto temporal de Actions que expira no es una estrategia de conservación de releases.
- [ ] Añadir avisos faltantes de Qt/componentes nativos identificados. El inventario de wheels no sustituye esta revisión.
- [ ] Comprobar que LICENSE, avisos de terceros y límites de recursos ajenos estén dentro del ZIP descargado.
- [ ] Obtener aprobación del mantenedor antes de publicar. Si hay dudas legales, resolverlas antes de redistribuir.

No se emite una oferta escrita de fuentes sin un responsable y un método que puedan cumplirla. Las URLs upstream de esta guía son evidencia de origen, no reemplazo automático de las obligaciones de quien distribuye el binario.

## Perímetro nativo del nuevo modo carpeta

El paso `prune_unused_qt_pdf.py` excluye qpdf/Qt6Pdf sólo tras comprobar las
importaciones PE normales y diferidas del resto del paquete. El inventario final
debe confirmar su ausencia; entonces no se atribuye Qt PDF/PDFium a ese paquete.
No cambia las obligaciones de artefactos antiguos que sí los contenían, ni elimina
las de Qt Core/GUI/Widgets/Network/SVG/ImageFormats, traducciones o PyQt retenidos.
Mesa/LLVM y los runtimes Microsoft permanecen; requieren sus propios avisos y
condiciones, no una etiqueta LGPL inferida del wheel. La evidencia del 5 de octubre identifica configuración y fuentes del proveedor Qt
mediante SBOM y comparación de archivos. La candidata identificada en
[el registro técnico](evidence/release-readiness-3.0/REPORT.md) tiene comparación
Qt/PyQt contra sus bytes empaquetados. No se ha ejecutado una reconstrucción del
proveedor ni cerrado la revisión de todos los componentes nativos; véanse
[el alcance y los pendientes](../third_party/RELEASE_SOURCE_EVIDENCE.md).
