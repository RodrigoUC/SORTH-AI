# Contribuir a SORTH

Gracias por ayudar a mejorar la organización de horarios académicos. Puedes reportar errores, mejorar documentación, proponer funciones o enviar cambios pequeños y comprobables. Aceptamos issues y PRs en español o inglés.

## Antes de empezar

- Busca un issue existente y lee [soporte](SUPPORT.md), [conducta](CODE_OF_CONDUCT.md) y [seguridad](SECURITY.md).
- Para cambios amplios, describe primero el problema, el alcance y cómo comprobarías la solución en un issue.
- Usa datos sintéticos. No subas bases de sesión, planillas institucionales, nombres de estudiantes, credenciales ni rutas personales.
- Las contribuciones de código destinadas a integrarse en SORTH deben ser compatibles con [GPL-3.0-only](LICENSING.md). Declara la procedencia y licencia de código o recursos externos. Conservas la titularidad de tu aporte; no se exige una cesión ni un CLA. No incluyas material que no tengas derecho a aportar.

## Entorno de desarrollo

La referencia del empaquetado Windows es CPython 3.12.10 x64. Otras versiones o plataformas requieren su propia validación.

```sh
git clone https://github.com/RodrigoUC/SORTH-AI.git
cd SORTH-AI/project_root
python -m venv .venv
```

Activa el entorno con `.venv\Scripts\Activate.ps1` en PowerShell o `source .venv/bin/activate` en Linux/macOS. Después:

```sh
python -m pip install -r requirements-dev.txt
python -m pip check
python gui_app.py
```

Para las pruebas, sigue la [suite completa en cuatro procesos](docs/development/WORKFLOW.md#suite-completa-en-cuatro-procesos): incluye colección completa, cuatro lotes en serie, verificación de cobertura y configuración offscreen por shell. No uses un único `pytest` sin selección como sustituto de ese procedimiento. Los comandos focalizados siguen siendo útiles durante el desarrollo; no certifican la suite completa.

Para reproducir el paquete Windows, sigue [WINDOWS_DISTRIBUTION.md](docs/release/WINDOWS_DISTRIBUTION.md): usa el lock con hashes en `.venv-build`, no el entorno genérico anterior.

## Organización y revisión

La [arquitectura del README](project_root/README.md#arquitectura) sigue siendo la
referencia. Consulta el [mapa y límites](docs/architecture/ARCHITECTURE.md) y el
[flujo de desarrollo](docs/development/WORKFLOW.md) para ubicar archivos, revisar
dependencias y coordinar cambios grandes en etapas.

Desde `project_root`, ejecuta también `python tools/check_architecture.py` y
`python -m pytest -c pytest.ini --rootdir=. -q tests/test_architecture tests/test_documentation`. Estas
pruebas forman parte de la suite completa; comprueban los límites estáticos, las
rutas públicas y los enlaces locales de la documentación.

- La aplicación está en `project_root/`: dominio en `src/scheduling`, orquestación en `src/application`, archivos/persistencia en `src/infrastructure` e interfaz en `src/gui`.
- Mantén cada PR enfocado. Evita reformatear archivos no relacionados o cambiar el lock sin necesidad.
- Añade una prueba de regresión para cada fallo corregido. Conserva semilla, datos y restricciones al comparar resultados del planificador.
- Para GUI, adjunta capturas sin información privada y verifica teclado, escalado, cancelación, repetición y restauración de sesión. Revisa `DESIGN.md` si está presente.
- Para importación/exportación, comprueba archivos mínimos, vacíos e inválidos y vuelve a abrir los archivos exportados.
- Actualiza documentación si cambian formatos, comandos, comportamiento o compatibilidad.
- Abre el PR como borrador mientras falten pruebas; indica qué pasó, qué falló y qué no se pudo ejecutar. No declares soporte de una plataforma sólo por pasar tests sin pantalla.

El mantenedor revisa alcance, corrección, pruebas, privacidad y licencias antes de integrar. Un PR puede requerir ajustes o quedar fuera de alcance. No hay un tiempo de respuesta garantizado.

## Controles de seguridad

Antes de proponer cambios de código o dependencias, sigue
[SECURITY_CHECKS.md](docs/SECURITY_CHECKS.md). La revisión estática y la auditoría
son independientes del build Windows. No suprimas avisos globalmente ni aceptes
actualizaciones automáticamente. Los cambios de Python requieren mantener
sincronizados los requisitos, el lock Windows con hashes y el inventario/licencias.
