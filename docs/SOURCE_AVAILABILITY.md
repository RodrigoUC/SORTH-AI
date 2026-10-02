# Fuentes correspondientes y cierre de distribución

La GPL del código propio está elegida. La entrega de fuentes de cada binario sigue siendo una tarea de release, no una promesa de que un paquete anterior ya la cumpla.

## Material verificado

- **SORTH:** cada ZIP de revisión registra `source_commit`. La fuente debe corresponder a ese commit exacto e incluir configuración, scripts y modificaciones necesarias para construirlo; no usar sólo `main` como referencia.
- **PyQt6 6.11.0:** el [paquete oficial de la versión en PyPI](https://pypi.org/project/PyQt6/6.11.0/#files) ofrece `pyqt6-6.11.0.tar.gz`. SHA-256 publicado de la fuente: `45dd60aa69976de1918b5ced6b4e7b6a25abd2a919ecef5fd5826ecc76718889`. Esto verifica disponibilidad upstream, no demuestra que se haya archivado y ofrecido junto al binario de SORTH.
- **Qt 6.11.2 / PyQt6-Qt6:** el wheel auditado declara LGPLv3. Debe obtenerse la fuente exacta y cualquier parche/configuración usados para producir las bibliotecas distribuidas, y contrastar los plugins y terceros. La fuente de PyQt no es la fuente de Qt. No se ha confirmado todavía ese paquete de fuentes correspondiente ni los avisos de cada DLL.
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
