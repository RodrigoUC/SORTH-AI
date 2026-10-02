# Seguridad

## Cómo comunicar una vulnerabilidad

No publiques datos afectados, archivos privados, secretos ni una prueba de explotación en un issue o PR público.

1. Abre la pestaña **Security** del repositorio. Si aparece **Report a vulnerability**, utiliza ese formulario de reporte privado.
2. Si la opción no aparece, **no hay un canal privado de seguridad verificado en esta documentación todavía**. Espera a que el mantenedor habilite el reporte privado en GitHub. Puedes solicitar un canal de contacto en un issue sin revelar detalles técnicos, personas afectadas ni adjuntos sensibles.

La presencia de este archivo no activa el reporte privado de GitHub. Su habilitación debe ser confirmada por el mantenedor antes de una release pública.

En el canal privado confirmado, describe versión/commit, plataforma, impacto, pasos mínimos con datos sintéticos y posible mitigación. Comparte sólo lo necesario para reproducir. Coordina la divulgación con el mantenedor; no se promete un plazo de respuesta ni recompensa.

## Versiones y actualizaciones

Mientras no se publique una política de versiones mantenidas, no se ofrece una garantía de soporte de seguridad para versiones históricas ni artefactos de revisión. Cada release deberá indicar qué versión sustituye y cualquier mitigación pendiente.

## Uso seguro

- Importa únicamente archivos de confianza. SORTH no es un entorno aislado para analizar documentos hostiles.
- Protege tus archivos de entrada, exportaciones y base SQLite de sesión mediante los permisos y copias de seguridad de tu equipo.
- No desactives antivirus, SmartScreen ni otras protecciones para ejecutar un paquete.
- Comprueba el origen del paquete y los hashes publicados. Un hash comprueba integridad, no identidad del editor ni ausencia de vulnerabilidades.
- Conserva datos originales antes de probar una versión nueva o una migración de persistencia.
