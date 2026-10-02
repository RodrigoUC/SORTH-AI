# Alcance y limitaciones conocidas

- El planificador utiliza heurísticas greedy con reintentos. No garantiza encontrar una asignación completa aunque exista, ni demostrar que una solución es óptima. Revisa los grupos sin asignar y valida el resultado antes de utilizarlo institucionalmente.
- El tipo de sala y las preferencias de día/hora no son siempre restricciones duras. Consulta las reglas del [README técnico](../project_root/README.md) y verifica requisitos específicos de laboratorios y cursos.
- El tiempo de ejecución depende de grupos, aulas, candidatos y restricciones. No se promete complejidad lineal para el flujo completo.
- El formato de importación requiere las hojas y columnas documentadas; importar un archivo no certifica que sus datos sean correctos. Las mejoras de formato sólo están disponibles una vez integradas en la versión utilizada.
- La referencia de distribución es Windows x64 con CPython 3.12.10. Ejecutar tests en Linux o macOS no certifica el paquete ni la interfaz en esas plataformas.
- Los paquetes de revisión actuales no están firmados y los artefactos de Actions caducan. No omitas advertencias de seguridad para instalarlos.
- La persistencia es local. La base de sesión y los archivos exportados pueden contener datos privados; no se deben adjuntar a reportes públicos.
- Los permisos pendientes sobre recursos de terceros y el canal privado de seguridad deben resolverse antes de anunciar una distribución open source lista para terceros. Consulta [la revisión de licencias](LICENSING_REVIEW.md).

Las notas de cada release deben actualizar estas limitaciones y diferenciar problemas resueltos de cambios aún en revisión.
