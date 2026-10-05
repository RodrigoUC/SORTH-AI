# Primera release retenida: 2.0.0 / v2.0.0

Este procedimiento **prepara** la publicación. El archivo
`.github/release-approval.json` se entrega con `publish: false`, sin SHA aprobado,
sin archivos aprobados y con todos los controles pendientes. Integrar el código
no crea una etiqueta, borrador ni release. No cambia permisos generales del
repositorio, instala credenciales persistentes ni activa protecciones nuevas.

## Dos identidades distintas, sin aprobación circular

1. Integrar mediante revisión el código del workflow, los avisos/licencias y el
   generador de fuentes. El commit resultante de **main** será el candidato.
   No etiquetar el commit anterior ni describir una compilación con cambios
   superpuestos como si procediera del main anterior.
2. El push de ese commit ejecuta `Windows review build`. Conserva íntegros los
   cuatro lotes de regresión, su inventario exacto, PDF, compilación GUI/MCP,
   smoke congelado, recuperación, instalador y desinstalación. Un trabajo
   posterior, `release-candidate`, sólo se ejecuta si el trabajo Windows pasa.
3. Ese trabajo descarga el artefacto Windows **de la misma ejecución**, verifica
   el SHA-256 del ZIP de Actions, descarga fuentes oficiales fijadas por hash,
   compara los bytes reales del ZIP contra su inventario y la matriz de fuentes
   Qt/PyQt incluida, crea un `git archive` del SHA exacto y sella el inventario
   completo. Exige todas las filas nativas requeridas y comprueba también cada
   traducción realmente incluida; no exige traducciones que no se distribuyen. Tiene
   `contents: read` y `actions: read`; no ejecuta los binarios descargados.
4. Revisar los archivos finales de ese candidato. Después, sólo con aprobación
   explícita, crear `release-approval/v2.0.0` a partir del SHA candidato. Cambiar
   **únicamente** `.github/release-approval.json`. El SHA de esta aprobación es
   distinto del SHA de la aplicación: la aplicación ya fue construida y no se
   reconstruye. No es necesario predecir el hash del commit de aprobación.
5. El push autorizado de esa rama exacta activa `First release approval`.
   PRs, main y ramas ordinarias sólo validan. Al terminar la ejecución de
   aprobación, `Publish approved first release` recibe `workflow_run`: GitHub
   carga este controlador desde la rama predeterminada, no desde la rama de
   aprobación. Valida de nuevo repositorio, workflow, evento, rama, SHA y
   resultado del run de aprobación. El único trabajo con `contents: write` es
   `publisher` de este controlador; tanto su YAML como su código Python proceden
   del código integrado. No ejecuta código de la rama de aprobación ni assets.

No hay dependencia de `workflow_dispatch`, PAT, secreto nuevo, permiso global de
escritura, entorno nuevo o permiso `actions: write`. Se usa únicamente el
`GITHUB_TOKEN` efímero de ese trabajo. Si una política existente del repositorio
impide ese permiso, registrar el bloqueo y pedir la decisión del mantenedor;
no modificar políticas ni credenciales para eludirlo.

## Artefacto candidato y fuentes

`SORTH-release-candidate-<run_id>-<run_attempt>` dura 14 días e incluye:

- Un ZIP completo `SORTH-windows-x64-2.0.0-<sha12>-unsigned.zip`.
- Exactamente un instalador
  `SORTH-2.0.0-<sha12>-windows-x64-unsigned-setup.exe`, compatible con el
  reconocimiento estricto del actualizador, con un límite de 512 MiB.
- `MANUAL_USUARIO.pdf` y `build-info.json` del mismo resultado Windows.
- `SORTH-2.0.0-<sha40>-source.tar.gz`, producido desde el commit exacto.
- `THIRD-PARTY-SOURCES.tar.gz`.
- `SHA256SUMS.txt`, con una entrada por cada archivo público excepto él mismo.
- `release-candidate.json`, recibo de revisión con SHA, run, attempt y tamaños y
  SHA-256 de todos los archivos públicos, incluido `SHA256SUMS.txt`.

El recibo de candidato queda en Actions; los otros siete archivos son los
assets públicos. `build-info.json` identifica el código y la compilación. Los
hashes comprueban integridad, no identidad criptográfica del editor, ausencia de
malware ni cumplimiento jurídico.

Contrato del generador de terceros, desde `project_root`:

```powershell
python tools/prepare_release_sources.py --output build/release-sources/THIRD-PARTY-SOURCES.tar.gz
```

El generador debe usar fuentes oficiales públicas con tamaños/hashes fijados,
incluir procedencia, recetas/configuración y avisos correspondientes, y fallar
ante descarga o hash incorrecto. No se permite una URL privada del workspace.
El workflow registra la herramienta `7z` instalada y exige que funcione, sin
instalar software nuevo. El inventario oficial de `windows-2025` consultado el
2026-10-05 incluye 7zip 26.03; la imagen cambia, por lo que el log real sigue
siendo evidencia necesaria. Si falta el generador, el trabajo informa
explícitamente la retención y **no** sube un candidato publicable; el éxito de
los tests de aplicación no significa que exista el bundle de publicación.

## Completar la aprobación exacta

No cambiar solamente `publish`. Copiar del recibo del candidato `source_commit`,
`source_run_id`, `source_run_attempt` y `assets` completos. Obtener `artifact_id`
y `artifact_sha256` del registro de Actions y calcular/verificar
`candidate_sha256` sobre los bytes originales de `release-candidate.json`.
No reserializar ese recibo antes de calcular su hash. Adjuntar en `release_notes`
el texto final aprobado, incluidos estado sin firma y limitaciones aplicables.

Cada entrada de `gates` exige `passed: true` y una referencia no vacía en
`evidence`. Conservar evidencias privadas fuera del texto público de las notas.
Estos campos son registros revisados por el mantenedor, **no** una prueba
automática de su contenido:

- `windows_acceptance`: aceptación del binario final y su digest en Windows real.
- `defender_review`: análisis del candidato final con protecciones activas,
  versión del motor/firmas y resultado; no promesa de reputación SmartScreen.
- `native_source_correspondence`: correspondencia de archivos nativos finales,
  fuentes/configuraciones y parches pertinentes. La investigación de un build
  anterior no certifica automáticamente este candidato.
- `license_and_redistribution`: avisos integrados y derechos de distribución,
  incluidos los siete archivos Microsoft identificados en la revisión separada.
- `unsigned_distribution_accepted`: aceptación expresa de distribuir sin firma.
- `public_release_authorized`: aprobación del mantenedor de etiqueta, SHA,
  notas y lista/digests exactos que se harán públicos.

El manifiesto requiere versión 2.0.0, tag v2.0.0, repositorio correcto, IDs
enteros, hashes completos, lista exacta y todos los controles anteriores.
Poner `publish: true` y hacer push de la rama de aprobación es la acción que
habilita publicación; requiere esa autorización. La aprobación de preparar o
integrar este workflow no autoriza completar los controles ficticiamente.

## Qué verifica el publicador

- El SHA aprobado sigue siendo el main exacto y ancestro de la aprobación.
- La rama de aprobación aún apunta al mismo commit: moverla (incluido un nuevo
  `publish: false`) o borrarla retiene el publicador. Esto se comprueba también
  inmediatamente antes del cambio público.
- La diferencia completa entre ambos commits sólo contiene el JSON de aprobación.
- El checkout del publicador es el main aprobado y está limpio.
- La ejecución de origen es un push de main de este repositorio, su workflow es
  `windows-review.yml`, y terminó correctamente con el intento aprobado.
- Artefacto no expirado, ID/nombre/run/SHA/digest correctos, ZIP íntegro sin
  duplicados, alias normalizados o de mayúsculas, enlaces simbólicos ni rutas
  inseguras. Los metadatos y el número/tamaño de entradas tienen límites; las
  redirecciones se validan en cada salto HTTPS de almacenamiento oficial, sin
  enviar el token fuera de api.github.com.
- Coincidencia exacta entre archivos, manifiesto, tamaños y hashes aprobados;
  checksums completos y una sola identidad/versión/instalador.
- Ni tag ni release preexistente, incluidos borradores sin etiqueta detectados
  enumerando todas las páginas de releases autenticadas. Se crea la etiqueta sin
  actualizar referencias.
- Se crea un borrador, se suben los siete assets una vez y se compara cada digest
  `sha256:` devuelto por GitHub, estado y tamaño. Se vuelve a listar para excluir
  archivos extra, duplicados o faltantes. Digest ausente bloquea publicación,
  aunque la carga parezca correcta.
- Se comprueba de nuevo etiqueta, main, ejecución de origen y el texto/nombre,
  prerelease, destino y estado borrador exactos antes de hacerlo público; también
  se valida la respuesta final. Un cambio en notas o metadatos bloquea el paso.

Operación de un solo escritor: mientras corre el publicador no modificar
manualmente la rama de aprobación, main, la etiqueta ni el borrador. Las
comprobaciones REST y la transición pública no son una transacción atómica;
no pueden impedir por completo un cambio concurrente de otro actor autorizado.
El publicador detecta los cambios que observa y se detiene, pero una revocación
en el último intervalo entre comprobación y PATCH requiere intervención humana.

No existe `--clobber`, reanudación automática, reintento de escrituras, borrado o
movimiento de etiquetas. Si falla después de crear tag/borrador, se mantiene ese
estado y se requiere inspección humana; repetir automáticamente el workflow
será rechazado. Una respuesta incierta exige comprobar GitHub antes de cualquier
otra acción. No asumir éxito por haber enviado la petición.

## Comprobaciones y límites pendientes

Pruebas sin red/escritura, también ejecutadas en el workflow de aprobación:

```sh
python -m unittest discover -s project_root/tests -p test_release_pipeline.py -v
python project_root/tools/release_pipeline.py validate
```

Cubren versión/SHA incorrecto, assets/checksums/digests ausentes, instalador
adicional, gates incompletos, ejecución PR/fallida/reintentada, cambio de main,
diff no permitido, rutas ZIP inseguras, tag/release preexistente y fallo parcial
de carga. La API se simula; esto no demuestra que un nuevo workflow haya corrido
correctamente en GitHub. La ejecución real del commit integrado, descarga del
candidato, revisión de fuentes/derechos, aceptación del binario final y
publicación/descarga verificadas siguen siendo controles separados.

Si el candidato caduca, main cambia o es necesario corregir avisos/código,
preparar otro candidato de main y aprobar sus nuevos digests. No reutilizar
silenciosamente la aprobación del anterior. Tras una publicación autorizada,
descargar desde la release pública y repetir integridad/arranque y detección por
el actualizador antes de declarar cerrada la entrega.

## Referencias oficiales

- [Artefactos de Actions y sus digests](https://docs.github.com/en/rest/actions/artifacts).
- [Creación y actualización de releases](https://docs.github.com/en/rest/releases/releases).
- [Assets de releases](https://docs.github.com/en/rest/releases/assets).
- [Referencias Git](https://docs.github.com/en/rest/git/refs).
- [Software de windows-2025](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md).
