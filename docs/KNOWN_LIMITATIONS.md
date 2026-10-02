# Alcance y limitaciones conocidas

- El planificador utiliza heurísticas greedy con reintentos. No garantiza encontrar una asignación completa aunque exista, ni demostrar optimalidad o inviabilidad. Revisa los grupos sin asignar y valida el resultado antes de utilizarlo institucionalmente.
- LAB es obligatorio en generación automática. Una excepción manual en aula regular requiere confirmación y queda registrada; capacidad, conflictos y las demás restricciones siguen vigentes. REGULAR conserva una preferencia de tipo; día/hora sugeridos son preferencias blandas. Consulta el [manual](../project_root/MANUAL_USUARIO.md).
- El tiempo de ejecución depende de grupos, aulas, candidatos y restricciones. No se promete complejidad lineal para el flujo completo.
- El formato de importación requiere las hojas y columnas documentadas; importar un archivo no certifica que sus datos sean correctos. Las mejoras de formato sólo están disponibles una vez integradas en la versión utilizada.
- La referencia de distribución es Windows x64 con CPython 3.12.10. Ejecutar tests en Linux o macOS no certifica el paquete ni la interfaz en esas plataformas.
- Los paquetes de revisión actuales no están firmados y los artefactos de Actions caducan. No omitas advertencias de seguridad para instalarlos.
- La persistencia es local. La base de sesión y los archivos exportados pueden contener datos privados; no se deben adjuntar a reportes públicos.
- Los permisos pendientes sobre recursos de terceros y el canal privado de seguridad deben resolverse antes de anunciar una distribución open source lista para terceros. Consulta [la revisión de licencias](LICENSING_REVIEW.md).

Las notas de cada release deben actualizar estas limitaciones y diferenciar problemas resueltos de cambios aún en revisión.

## Alcance de producto

El resultado necesita revisión humana antes de uso institucional. Sólo se comprueban las restricciones modeladas: no se ofrece un sistema completo de matrícula, disponibilidad de docentes/estudiantes, cumplimiento curricular, gestión multiusuario, sincronización ni garantía de adecuación física de un laboratorio. Una excepción LAB confirmada no acredita equipamiento o condiciones pedagógicas.

El piloto con personas nuevas permanece pospuesto y no hay resultados de usuario que lo den por completado. La validación nativa en Windows sigue siendo necesaria. El [inicio rápido](QUICKSTART.md) enlaza el manual y el [aviso de privacidad](../PRIVACY.md) describe almacenamiento y soporte público.
