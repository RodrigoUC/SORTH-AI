# Checklist de versiones y publicación

Esta guía prepara una release; no autoriza publicarla, firmarla, modificar permisos ni activar ajustes del repositorio.

## Convención propuesta

Usar `MAJOR.MINOR.PATCH` y etiquetas `vMAJOR.MINOR.PATCH`; una candidata puede usar `-rc.1`. Un cambio incompatible en formato de entrada, persistencia o comportamiento público requiere explicar la migración y considerar incremento mayor; funciones compatibles incrementan menor y correcciones compatibles incrementan parche. El mantenedor decide el primer número después de revisar las etiquetas existentes. Los encabezados históricos v1.0/v2.0 del README no demuestran que haya releases publicadas.

Cada versión debe identificar un único commit, fecha, plataforma validada, cambios, limitaciones y procedimiento de actualización/retroceso. No se ofrece aún una API estable para importar módulos internos de Python.

## Antes de marcar una candidata

- [ ] Verificar alcance de GPL-3.0-only y texto LICENSE; comprobar procedencia del icono y datos sintéticos según [LICENSING_REVIEW.md](LICENSING_REVIEW.md).
- [ ] Confirmar soporte público por Issues y canal privado de seguridad; verificar que el canal funciona sin publicar información sensible.
- [ ] Revisar datos de ejemplo y capturas; retirar o sustituir del paquete aquello sin autorización de redistribución.
- [ ] Seleccionar commit y número sin reutilizar una etiqueta publicada.
- [ ] Registrar cambios y migraciones; comprobar coherencia entre README, manual, GUI y notas de versión.
- [ ] Revisar dependencias directas y transitivas del lock, avisos de seguridad y licencias de las versiones exactas.

## Verificación del commit exacto

- [ ] Ejecutar `python -m pip check` y la [suite completa en cuatro procesos con verificación de inventarios](development/WORKFLOW.md#suite-completa-en-cuatro-procesos) desde `project_root` en entorno limpio.
- [ ] Verificar CI Windows del mismo commit: pruebas, manual generado, empaquetado y smoke test del ejecutable.
- [ ] En Windows real sin Python, extraer la carpeta completa y probar inicio, carga válida/inválida/cancelada, edición, generación repetida, exportación y reapertura de sesión.
- [ ] Validar archivos Excel/CSV exportados y vista previa de impresión; contrastar asignaciones y totales con la aplicación.
- [ ] Probar teclado, escalado de pantalla, mensajes de error y cualquier idioma o movimiento reducido que incluya esa versión.
- [ ] Conservar evidencia del commit y distinguir validaciones automatizadas, manuales y pendientes. Un test omitido no cuenta como aprobado.

## Contenido y publicación

Seguir [WINDOWS_DISTRIBUTION.md](release/WINDOWS_DISTRIBUTION.md) para compilación, firmas y empaquetado.

- [ ] Preparar ZIP completo, manual vigente, hashes SHA-256, manifiesto de versiones y avisos/licencias de terceros.
- [ ] Para la distribución GPL, preparar el código fuente correspondiente de la versión, scripts de construcción y textos aplicables, con acceso junto al binario; un enlace a `main` mutable no identifica la versión distribuida.
- [ ] Confirmar que no se empaqueten sesiones, documentos personales, tokens, entornos de desarrollo ni evidencias privadas.
- [ ] Revisar procedencia/firma. Explicar claramente si sigue sin firma; no prometer ausencia de alertas antivirus.
- [ ] Obtener aprobación del mantenedor para etiqueta, release y archivos definitivos. Publicar sólo después de resolver bloqueos legales y de seguridad.
- [ ] Descargar la release publicada, verificar hashes y repetir el arranque del paquete descargado.
- [ ] Añadir enlaces de soporte, limitaciones, versión anterior y cambios incompatibles.

## Si aparece un fallo después

Reproducir con datos sintéticos, valorar gravedad y documentar mitigación. Ante una vulnerabilidad usar el canal privado. No sobrescribir una etiqueta ni reemplazar silenciosamente binarios de una versión publicada: preparar un parche y explicar qué versión sustituye. Cualquier retirada o cambio externo requiere autorización del mantenedor.
