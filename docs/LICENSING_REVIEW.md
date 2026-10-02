# Revisión de licencias antes de publicar

**Estado: GPL-3.0-only aprobada para el código propio; revisión de recursos y distribución pendiente.** La licencia está en [LICENSE](../LICENSE) y su alcance en [LICENSING.md](../LICENSING.md). No debe anunciarse que todos los materiales y binarios están listos para redistribuir hasta resolver lo siguiente.

## Decisión de licencia del proyecto

El mantenedor eligió **GNU GPL v3 únicamente (`GPL-3.0-only`)** para el código propio. [Riverbank](https://www.riverbankcomputing.com/software/pyqt) ofrece PyQt bajo GPLv3 o licencia comercial. No se presupone que SORTH tenga licencia comercial de PyQt. Una licencia permisiva del código propio no elimina las obligaciones de GPL de una distribución combinada con PyQt.

El mantenedor declara haber desarrollado SORTH con ayuda de agentes de IA y aprobó GPL-3.0-only para el código propio. Esto no acredita por sí mismo derechos sobre materiales incorporados: se debe revisar su procedencia y compatibilidad. No se ha añadido una cesión, CLA ni autorización automática sobre aportes ajenos.

Referencia: [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html). Esta revisión técnica identifica decisiones pendientes; no sustituye asesoría legal cuando haya dudas de titularidad o compatibilidad.

## Dependencias principales: inventario inicial

| Componente | Licencia/fuente oficial | Comprobación pendiente para la release |
| --- | --- | --- |
| PyQt6 | [GPLv3 o comercial](https://www.riverbankcomputing.com/software/pyqt) | Incluir textos/avisos del wheel exacto y satisfacer la modalidad elegida. |
| Qt incluido por PyQt6-Qt6 | [Licencias de Qt 6 y terceros](https://doc.qt.io/qt-6/licenses-used-in-qt.html) | Inventariar módulos/plugins y avisos realmente incluidos; no asumir una licencia única. |
| pandas | [BSD-3-Clause](https://pandas.pydata.org/docs/getting_started/overview.html#license) | Conservar avisos y licencias de la versión distribuida. |
| openpyxl | [MIT/Expat](https://openpyxl.readthedocs.io/en/stable/) | Conservar texto y copyright de la versión distribuida. |
| PyInstaller | [GPL con excepción de distribución y componentes Apache](https://pyinstaller.org/en/stable/license.html) | La excepción no elimina las obligaciones de las dependencias empaquetadas. |
| Python, NumPy, SIP y otras dependencias | Metadatos y archivos de licencia de cada distribución exacta | Inventariar todo `requirements-windows.lock`, incluyendo herramientas si se redistribuyen. |
| Generación PDF y pruebas | `requirements-docs.txt`, `requirements-dev.txt` | Revisar licencias, fuentes y avisos si se incluyen en un paquete o entregable. |

Los avisos de los 29 wheels exactos, incluidos transitivos, están recopilados en [third_party](../third_party/README.md), con hashes verificados contra el lock y textos originales. El ZIP de revisión incluye este inventario, LICENSE y avisos. Este cuadro **no es un SBOM del ejecutable ni una certificación de cumplimiento**. Las versiones exactas están en los requirements y el lock; al cambiar el lock debe repetirse la revisión. Antes de la release, completar el inventario de DLL/plugins realmente enviados y los avisos nativos faltantes, además de [preparar las fuentes correspondientes](SOURCE_AVAILABILITY.md). Los enlaces de esta guía no sustituyen los textos que deban acompañar la distribución.

## Recursos originales y sintéticos de esta edición

El icono geométrico SVG/PNG/ICO fue creado para SORTH y es reproducible con `project_root/tools/generate_demo_assets.py`, sin imágenes ni trazados externos. Se sustituyeron los anteriores recursos gráficos de terceros; no se distribuyen aquí.

El ejemplo `project_root/data/input/Cursos_Ejemplo.xlsx`, su JSON y las capturas usan datos ficticios. Incluye 8 aulas, 12 cursos, 36 grupos y 42 sesiones. La procedencia y reproducción están en [PROVENANCE.md](../project_root/data/input/PROVENANCE.md). Los PDFs académicos y el conjunto institucional anterior no forman parte de este repositorio limpio.

Las pruebas comparan cada celda del libro con su fuente sintética y verifican la reproducción de los iconos. No se ha trasladado el historial del repositorio anterior.

## Alcance de la revisión de distribución

El paquete incluye el icono original y los datos sintéticos mediante `assets` y `data/input`. Los avisos de dependencias siguen teniendo sus licencias propias. La compilación Windows debe verificar los módulos nativos y plugins efectivamente empaquetados antes de una release; esta preparación de código y avisos no constituye certificación legal ni firma del ejecutable.

Para nuevos recursos externos, registrar ruta, autor/titular, URL, versión, licencia exacta, evidencia y obligaciones antes de incluirlos. No añadir documentos institucionales o sesiones reales como muestras.
