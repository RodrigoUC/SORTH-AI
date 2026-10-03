# Revisión automática de seguridad

## Alcance e inventario

`security-review.yml` es independiente de `windows-review.yml`: no construye ni
publica el instalador. Se ejecuta en PRs a `main`, pushes a `main`, manualmente y
los lunes a las 08:23 UTC. Tiene únicamente `contents: read`, checkout sin
credenciales persistentes, ningún secreto ni permisos de escritura. No usa
`pull_request_target`, no modifica ajustes del repositorio y no hace auto-merge.

- `requirements.txt`: pandas, openpyxl y PyQt6 de ejecución.
- `requirements-dev.txt`: ejecución, pytest y requisitos de documentación.
- `requirements-docs.txt`: reportlab, markdown-it-py y pypdf. pypdf se usa para
  comprobar PDFs en `tests/test_manual_generation.py`; no hay importación en la
  aplicación. Esto no prueba por sí solo la ausencia de un paquete en el binario.
- `requirements-windows.lock`: inventario completo con hashes de ejecución,
  pruebas, documentación, PyInstaller y transitivas para CPython 3.12/Windows x64.
- `requeriments.txt`: alias histórico de `requirements-dev.txt`.
- Si está habilitada la integración opcional, `requirements-mcp.txt` y
  `requirements-mcp-dev.txt` tienen su inventario transitivo separado
  `requirements-mcp.lock` (resolución universal/Python 3.12, incluye pruebas). Se audita en un
  paso independiente; nunca se instala dentro del entorno Windows principal.
  Un manifiesto opcional sin su lock bloquea el check.
- `security/requirements.txt`: Bandit 1.9.4 y pip-audit 2.10.1, en un entorno de
  análisis separado. Sus dependencias transitivas se resuelven en PyPI y no son
  parte del lock de distribución; no se afirma reproducibilidad binaria de ese
  entorno. No se instalan dependencias de la aplicación para analizarla.

Las acciones oficiales están fijadas por SHA completo. Las referencias v6 de
`actions/checkout`, v7 de `actions/setup-python` y v4 de `actions/upload-artifact`
se comprobaron contra sus repositorios oficiales el 2026-10-02. Dependabot sólo
propone actualizaciones semanales de **GitHub Actions**, hasta tres PRs abiertos.
Todo cambio exige revisión humana; esta configuración no cambia protección de
ramas ni obliga a GitHub a bloquear un merge.

## Herramientas y límites

Bandit analiza `src`, `tools` y todos los `.py` de primer nivel, incluyendo
scripts de empaquetado y el propio verificador. Excluye tests y directorios de
artefactos/entornos; las pruebas usan deliberadamente patrones sintéticos y
asserts. No ejecuta el código analizado ni lo envía a servicios externos. Se usa
`--ignore-nosec`: un comentario `nosec` nuevo no elude la revisión. Se conservan
**todos** los hallazgos originales en `bandit.json`.

La línea base `security/bandit-reviewed.json` contiene excepciones individuales
con archivo, regla, hash del contexto exacto, cantidad, fecha y motivo. Una
excepción no cubre otras apariciones de la misma regla; si queda obsoleta, el
check falla. No se regenera en bloque. La revisión inicial incluye 23 patrones:
14 asserts de invariantes del benchmark, aleatoriedad reproducible del
planificador, cuatro fallbacks opcionales de GUI y cuatro advertencias sobre
subprocess en comandos locales fijos. Los fallbacks silenciosos son límites de
diagnóstico conocidos, especialmente al recargar el mapa Excel durante la
restauración; no son una certificación de seguridad de esa lógica.

El verificador valida pins, hashes y sintaxis de marcadores con `packaging`.
Genera `audit-inventory.txt`, una lista de **auditoría solamente** que elimina
extras y marcadores sin evaluar la plataforma del host. Así se consulta la unión
de paquetes Linux/Windows, incluidos pywin32 y colorama desde Linux. Nunca se
instala ese archivo; la instalación siempre usa el lock original con marcadores.
Se rechazan versiones múltiples del mismo paquete, rangos y marcadores inválidos;
un futuro lock con versiones diferentes por plataforma necesita auditorías
separadas revisadas. Los hashes se conservan en el inventario derivado.

pip-audit consulta metadatos públicos de PyPI para **cada nombre/versión del lock**
con `--disable-pip --require-hashes --strict`. La misma validación se aplica al
lock MCP opcional cuando su manifiesto o lock están presentes. No resuelve, instala, ejecuta ni
corrige paquetes Windows en Linux. Comprueba que los requisitos directos
coinciden con el lock y que el inventario devuelto coincide exactamente. Los
hashes no se verifican contra ruedas descargadas en este paso: eso corresponde
al build Windows con `pip --require-hashes`. Una caída de red, un paquete omitido,
un informe ausente o inventario incompleto bloquean el check.

El auditor detecta avisos conocidos, no malware ni todas las dependencias nativas
incluidas en Qt. No demuestra explotabilidad en SORTH. Bandit detecta patrones,
no hace análisis completo de flujo. Un resultado sin hallazgos nuevos no
certifica ausencia de vulnerabilidades. PRs pueden modificar este mismo control:
revisar siempre cambios de workflow, baseline y herramientas.

## Ejecución local

Desde `project_root`, con CPython 3.12:

```sh
python -m venv .venv-security
.venv-security/bin/python -m pip install --only-binary=:all: -r security/requirements.txt
.venv-security/bin/python -m pip check
.venv-security/bin/python -m unittest discover -s tests -p test_security_checks.py -v
.venv-security/bin/python tools/security_review.py static
.venv-security/bin/python tools/security_review.py dependencies
```

Si está presente el extra MCP, ejecutar también:

```sh
.venv-security/bin/python tools/security_review.py optional-dependencies --output-dir build/security/optional
```

En Windows sustituir `.venv-security/bin/python` por
`.venv-security\Scripts\python.exe`. No utilizar `.venv-build` para esto.

Los JSON se guardan en `project_root/build/security/`; CI los conserva 14 días.
Cada comando termina con 0 (completo, sin hallazgos nuevos), 1 (hallazgos nuevos)
o 2 (análisis incompleto/error). El informe `*-status.json` distingue estos estados.
La ausencia de artefacto o un fallo de instalación tampoco son un resultado limpio.
Los dos análisis se intentan aun si uno falla; ningún fallo se ignora. Las pruebas
incluyen un `eval` sintético real, un error sintáctico real y fallos de infraestructura
simulados; estos últimos deben devolver 2, nunca 0.

## Triage y actualizaciones

1. Leer primero el estado y logs: distinguir fallo del analizador de hallazgo.
2. Para un aviso de paquete, identificar versiones afectadas/fijas, alias, alcance
   y uso real; no contar registros duplicados como vulnerabilidades distintas.
3. Corregir con el cambio mínimo, pruebas de regresión y revisión humana. No usar
   `pip-audit --fix`, auto-merge ni ignorar todos los avisos de un paquete.
4. Actualizar versiones directas y, en el entorno Windows documentado, obtener
   ruedas verificadas y regenerar el lock con `tools/lock_windows.py`. Actualizar
   inventario y licencias; ejecutar tests, build y smoke del workflow Windows.
   No cambiar sólo el número de versión o hash manualmente. Dependabot **no**
   administra estos archivos porque desconoce el generador Windows específico.
5. Revisar las versiones de las herramientas de análisis mensualmente o cuando
   aparezca un aviso; actualizar sus pins en un PR y repetir los contratos
   sintéticos. Revisar cada SHA propuesto por Dependabot contra el upstream oficial.
6. Una excepción estática necesita justificación concreta y revisión. No existe
   una lista de excepciones de vulnerabilidades de dependencias en esta fase.
   Una necesidad futura requiere decisión explícita, aviso exacto, motivo,
   mitigación, responsable y caducidad; no desactivar el gate globalmente.

La primera auditoría (2026-10-02, lock con pypdf 6.10.0) devolvió 49 registros y
31 IDs distintos para pypdf; algunos IDs se repiten o pueden ser alias. El gate
falló correctamente. Esto es evidencia histórica, no una aceptación del riesgo:
la actualización del lock debe volver a pasar el auditor antes de integrar.
La candidata con pypdf 6.19.0 fue comprobada ese mismo día: los 29 paquetes
del inventario coincidieron y pip-audit terminó con 0, sin avisos conocidos.
El lock opcional candidato con MCP 1.30.0 también pasó: los 34 paquetes
coincidieron con el inventario y no hubo avisos conocidos ni omisiones.
La revisión universal posterior también pasó con los 36 paquetes, incluidos
pywin32 312 y colorama 0.4.6, auditados desde Linux sin omisiones.
CI debe repetirlo sobre el commit final; los avisos pueden cambiar.

No publicar fuentes privadas, sesiones, documentos institucionales ni detalles
sensibles en artefactos/issues. Seguir [SECURITY.md](../SECURITY.md) para reportes
privados. El control se limita al código público y metadatos públicos de paquetes.

## Fuentes oficiales

- [Bandit: configuración y supresiones](https://bandit.readthedocs.io/en/latest/config.html)
- [Bandit en PyPI](https://pypi.org/project/bandit/1.9.4/)
- [pip-audit: uso, modelo de seguridad y límites](https://github.com/pypa/pip-audit)
- [pip-audit en PyPI](https://pypi.org/project/pip-audit/2.10.1/)
- [Dependabot: opciones](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [GitHub: endurecimiento de Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
