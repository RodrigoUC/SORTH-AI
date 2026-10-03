# Créditos y Atribuciones

## Icono de la Aplicación

El icono actual es una composición geométrica original creada para SORTH.
`project_root/tools/generate_demo_assets.py` genera el SVG, PNG e ICO sin
imágenes, fuentes ni trazados externos. Véase `project_root/assets/README_ICONO.txt`.

Los datos de ejemplo son completamente sintéticos. Su origen y reproducción
se documentan en `project_root/data/input/PROVENANCE.md`.

---

## Librerías y Dependencias

- **PyQt6**: Framework GUI
- **pandas**: Procesamiento de datos
- **openpyxl**: Manipulación de archivos Excel
- **ReportLab**: Exportación directa de horarios PDF (licencia BSD; versión ya incluida en el inventario Windows)
- **DejaVu Sans**: Fuente incrustada en los horarios PDF, en `project_root/assets/fonts/`; licencia preservada junto al archivo y en `third_party/licenses/dejavu-font.txt`
- **PyInstaller**: Compilación a ejecutable

## Textos de licencia preservados

Consulta [third_party/README.md](third_party/README.md) para los avisos exactos de 29 wheels Windows, CPython y fuentes del manual, con hashes y procedencia. No sustituye la revisión del ejecutable final.
