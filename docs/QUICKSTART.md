# Inicio rápido

Prueba primero con datos ficticios. La distribución actual es de revisión; consulta las [limitaciones](KNOWN_LIMITATIONS.md) y usa el [manual completo](user/MANUAL_USUARIO.md) para los detalles.

1. Extrae toda la carpeta Windows y abre `SORTH.exe`. Si Windows bloquea el archivo, detente y conserva el mensaje: no desactives protecciones. Para ejecutar desde código, sigue [instalación](../project_root/README.md).
2. En **Cargar Excel**, elige `Cursos_Ejemplo.xlsx` de la carpeta de datos incluida. Debe mostrar 8 aulas y 12 cursos. En el árbol fuente está en `project_root/data/input/`. Sólo usa copias de archivos de confianza.
3. Revisa cursos y aulas. Para repetir el ejemplo, desactiva semilla aleatoria y usa **42**. Pulsa **Generar horario** y espera: el ejemplo produce 42 sesiones, porque algunos de sus 36 grupos se dividen.
4. En **Horario generado**, busca y filtra por aula, día o estado. Revisa todas las sesiones **Sin asignar**; el motivo es una pista, no una prueba matemática de imposibilidad. **Asignar manualmente** permite elegir un hueco válido. Los LAB exigen laboratorio en generación automática; una excepción manual en aula regular necesita confirmación y queda registrada. Revisa su idoneidad antes de usarla.
5. **Exportar todas las asignaciones** incluye todas las sesiones asignadas. **Exportar filtrado (N)** incluye sólo las que cumplen los filtros compartidos. Ninguna exporta pendientes como sesiones asignadas. Guarda Excel y CSV con nombres diferentes del archivo de entrada y comprueba su contenido.
6. Antes de cerrar, confirma **Sin cambios pendientes**. Si hay error, usa **Reintentar**; no confundas exportar con respaldar toda la sesión. Al abrir de nuevo, acepta restaurar. La base está en `%LOCALAPPDATA%/SORTH` en Windows, fuera de la carpeta del programa. [Recuperación y copias](user/SESSION_RECOVERY.md).
7. El encabezado permite **Idioma / Language** (ES/EN) y **Reducir animaciones**. Ambas preferencias son locales. El formato de entrada/exportación conserva nombres en español; no traduzcas las hojas `Aulas` y `Cursos`.

No hay cuenta, sincronización colaborativa ni envío automático de diagnósticos en el flujo revisado. Lee [privacidad](../PRIVACY.md). El soporte general es por [GitHub Issues](https://github.com/RodrigoUC/SORTH-AI/issues), con datos sintéticos y sin plazo garantizado; consulta [seguridad](../SECURITY.md) antes de reportar una vulnerabilidad.
