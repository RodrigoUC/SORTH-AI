# Preparación técnica de SORTH 3.0.0

Fecha de revisión: 28 de octubre de 2026. Estado: **candidata con un defecto de
identidad PDF detectado; no autorizar su publicación**. La corrección y la
aceptación de otra candidata requieren su propia evidencia.

## Candidata identificada

| Campo | Valor verificado |
| --- | --- |
| Commit de `main` | `772b1e6bef48be23ccf278bd4e0bb6503f7ad4c5` |
| Build | `3.0.0-772b1e6bef48` |
| Ejecución Windows | [40649425365](https://github.com/RodrigoUC/SORTH-AI/actions/runs/40649425365), intento 1 |
| Artefacto de candidata | `SORTH-release-candidate-40649425365-1`, ID `12799149690` |
| SHA-256 del ZIP de Actions | `f2bd7c90316204f3fd523904967ca2259674692b6863a847b0d69eead2ee5656` |
| SHA-256 del recibo | `bbc2ee0c38ec2d22ec957e680717febcddb9c0c1e18160a5bb33a723a14e1918` |

Los hashes de los siete archivos públicos preparados están en
[el registro estructurado](candidate-772b1e6.json). El artefacto de Actions
caduca el 11 de noviembre de 2026; no es un canal de publicación permanente.

Esta revisión no autoriza una candidata posterior, aunque sólo cambie su
documentación. Un nuevo `main` debe producir su propia candidata y evidencia.

## Comprobaciones realizadas

- CI del commit exacto: regresión completa, cobertura de inventarios, manual,
  GUI/MCP empaquetados, recuperación, instalador y desinstalación aprobados.
  La generación y subida de candidata también terminaron correctamente.
- Descarga local del artefacto y comprobación de su SHA-256 contra la metadata
  de Actions. El recibo, las identidades y los siete archivos coinciden en
  nombres, tamaños y hashes; no hay assets inesperados.
- Extracción controlada y comprobación de los 1.173 archivos del inventario de
  aplicación. Se verificaron 21 documentos legales presentes y 69 avisos de
  wheels idénticos a los bytes del commit. La matriz de fuentes se contrastó
  otra vez con el ZIP descargado: 120 archivos Qt/PyQt, incluidos los 24 obligatorios.
- Paquete de fuentes: 619 miembros; SHA-256
  `d5ad900abb41cef58791dc05ca5e4c2d8fe0df624d01f1d6aaa725024bb49c2d`.
- Smoke local del EXE congelado con perfil sintético y Python fuera del PATH
  hijo: 42/42 sesiones del ejemplo y 500/500 del fixture grande. Pasaron
  exportaciones Excel/CSV/PDF, edición, restauración en otra ventana, errores de
  importación sin pérdida de sesión, ES/EN y reinicios de temas.

El equipo local es Windows 11 x64, sin elevación, con Python instalado. El smoke
usa Qt offscreen y fuentes del sistema. No acredita un PC limpio, interacción
humana, lectores de pantalla, Excel real ni experiencia de descarga en navegador.

Los hashes de los archivos de aplicación permanecieron iguales después del
análisis y del smoke. Los datos del flujo automatizado son sintéticos y sus
preferencias están dentro del perfil aislado de la prueba.

## Defecto detectado durante la revisión PDF

Los PDF de esta candidata identifican `SORTH 2.0.0`, aunque el manifiesto del
ejecutable declara 3.0.0. El smoke anterior validaba generación y contenido,
pero no contrastaba la versión del encabezado. Esa omisión no se considera
aceptación del archivo ni se oculta tras el CI aprobado.

La corrección de esta revisión elimina el literal y comparte el lector de
identidad validada entre exportación y actualizaciones. Un manifiesto corrupto
interrumpe el PDF sin reemplazar el destino. Se añade un gate que compara todas
las páginas de los PDF congelados ES/EN con la versión del ejecutable.
Los PDF del smoke se conservan también en el artefacto de evidencia de CI para
permitir su revisión visual posterior.

Los previews de fuente corregidos, con datos sintéticos, pasaron el contraste de
versión en sus ocho páginas por idioma y la revisión visual de tablas, márgenes,
texto y numeración. Permanecen en el directorio local de evidencia. No son los
PDF congelados de una nueva candidata: esa comprobación corresponde al CI nuevo.

## Análisis Defender del artefacto exacto

Se ejecutó `Start-MpScan -ScanType CustomScan -ScanPath` por separado sobre el
instalador y la carpeta extraída. Se correlacionaron eventos 1000 y 1001 por
identificador de análisis para ambos objetivos. No se observaron eventos 1116 o
1117 asociados a esas rutas en la ventana registrada.

Motor/producto: `4.18.26090.9`; firmas: `1.463.1.0`. Servicio, antivirus y
protección en tiempo real estaban activos. No se cambiaron protecciones ni
exclusiones. El instalador tiene Authenticode `NotSigned`.

Es evidencia de análisis completado con esas firmas y archivos, no una garantía
de ausencia de malware ni una aprobación de SmartScreen o de distribución sin
firma. Los XML y datos de entorno sin sanitizar permanecen en
`project_root/build/release-review/772b1e6/`, excluidos de Git.

## Pendientes que requieren otro entorno o decisión

| Control | Evidencia aún necesaria |
| --- | --- |
| Aceptación Windows | PC sin Python, interfaz nativa, escalado, teclado, Excel/impresión y piloto con usuarios |
| Dos builds | Aislamiento de datos y recuperación con snapshots compatibles; no hay migraciones de formatos antiguos |
| Correspondencia nativa y licencias | Revisión final de avisos, condiciones y componentes fuera del perímetro Qt/PyQt, incluidos runtimes Microsoft |
| Firma | Elección del mantenedor o aceptación explícita de distribución sin firma |
| Canal privado | La API de GitHub devolvió `enabled: false`; el mantenedor debe habilitar y comprobar el reporte privado |
| Publicación | Aprobación humana del commit, artefacto y hashes finales; acceso duradero a binarios y fuentes |

No se modificó `.github/release-approval.json`: `publish=false` y los seis gates
siguen sin aprobar. Se prepararon [notas de versión](../../release/NOTES_3.0.0.md)
para revisión, con incompatibilidades y límites del producto.

## Referencias

Microsoft. (s. f.). *Start-MpScan* [Documentación de PowerShell]. Microsoft Learn. Recuperado el 28 de octubre de 2026, de https://learn.microsoft.com/en-us/powershell/module/defender/start-mpscan

Microsoft. (s. f.). *Troubleshoot Microsoft Defender Antivirus scan issues*. Microsoft Learn. Recuperado el 28 de octubre de 2026, de https://learn.microsoft.com/en-us/defender-endpoint/troubleshoot-mdav-scan-issues
