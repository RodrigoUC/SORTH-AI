# Apariencia / Appearance

## Elegir un tema

1. Abre **Configuración → General → Apariencia…**.
2. Elige **Original claro**, **Nocturno** o **Alto contraste claro**.
3. Prueba los campos, botones, filas seleccionadas y bloques de curso de la vista
   previa. Los avisos y errores que aparecen dentro de la muestra son ejemplos.
4. Pulsa **Aplicar** para guardar el tema en este equipo y usarlo en toda la
   aplicación. **Cancelar**, Escape y cerrar la ventana descartan la vista previa.

**Restaurar original** selecciona Original claro en la muestra. También necesita
**Aplicar** para guardarse. Está disponible en el pie de la ventana, incluso
cuando el contenido debe desplazarse.

El tema tiene su propia operación de guardado. Aplicarlo no guarda las casillas
pendientes de Configuración. Guardar o Cancelar en Configuración no revierte un
tema que ya se aplicó. La explicación se muestra junto a la entrada de Apariencia.

## Importar un tema propio o creado con IA

**Importar tema JSON…** abre el selector de archivos del sistema. El archivo debe
cumplir el contrato SORTH v1: JSON UTF-8, hasta 16 KiB, nombre y descripción de
texto plano y los 30 colores semánticos completos. No admite estilos QSS, código,
HTML, rutas de recursos ni fuentes externas. No se suben archivos a ningún sitio.

Se rechazan archivos incompletos, claves duplicadas, versiones desconocidas,
colores inválidos y combinaciones que no pasan las comprobaciones de contraste.
El error y sus detalles son seleccionables y copiables. El tema activo permanece
intacto; corrige el archivo y vuelve a importarlo. Los detalles técnicos conservan
los nombres exactos de los campos y pueden estar en inglés.

Un archivo válido solo cambia la vista previa. **Aplicar** guarda una copia
normalizada en las preferencias de SORTH; después puedes mover o eliminar el
archivo que importaste. Su nombre y descripción se muestran literalmente, sin
traducirlos al cambiar el idioma de la interfaz.

El repositorio incluye la habilidad
[**sorth-theme-designer**](../../.agents/skills/sorth-theme-designer/SKILL.md) para
crear temas con un asistente compatible. La habilidad valida el mismo contrato
que usa la aplicación. SORTH no activa proveedores de IA, envía el horario ni
realiza llamadas de pago para importar o aplicar un tema.

## Si no se puede guardar o recuperar un tema

Si falla el guardado, el diálogo permanece abierto, explica el error y permite
volver a intentarlo. El tema anterior sigue activo. No se muestra una confirmación
de aplicación cuando el guardado falla. Si el archivo sí se guardó pero algún
control abierto no pudo actualizarse, el aviso lo distingue y recomienda
reiniciar SORTH para completar la aplicación del tema.

Si las preferencias guardadas son inválidas, SORTH usa Original claro y conserva
el archivo original. Si el archivo cambia fuera de SORTH, volver a abrir Apariencia lee
la nueva copia y la presenta para revisar; Cancelar sigue sin cambiar el tema
activo. En Apariencia aparece una casilla desmarcada para **conservar
el archivo inválido y reemplazarlo al aplicar**. Marca esa opción solo cuando
quieras recuperar las preferencias; el archivo original se copia a una copia de
seguridad antes del reemplazo. Cancelar no modifica los archivos.

## Alcance y accesibilidad

- El tema afecta a las superficies propiedad de SORTH. Los bordes de las ventanas
  y selectores de archivos nativos siguen al sistema operativo.
- Los horarios, colores e identidades de los cursos, exportaciones, permisos MCP,
  herramientas opcionales, idioma y preferencia de animaciones no cambian.
- Usa Tab y Mayús+Tab para recorrer los controles. El contenido desplazable revela
  automáticamente el control con foco. Aplicar, Cancelar y Restaurar original
  permanecen fuera del desplazamiento; pueden apilarse en ventanas estrechas.
- La validación del contraste de los colores no es una certificación completa de
  accesibilidad. Las capturas y pruebas Qt de desarrollo en Linux no sustituyen
  la comprobación de Windows empaquetado ni la revisión con lector de pantalla.

## English quick guide

Open **Settings → General → Appearance…**. Choose **Original light**, **Night**,
or **High contrast light**, and try the native sample controls. Only **Apply**
saves and changes the app. **Cancel**, Escape, or closing the window discards the
preview. **Restore original** stages Original light and still requires Apply.

**Import JSON theme…** reads a local SORTH v1 file, up to 16 KiB. It accepts only
complete, validated color data and plain-text metadata. It never executes code or
uploads the file. A valid import is a preview until Apply saves an owned copy.
Moving or deleting the source file afterward does not affect the saved theme.

Applying a theme is separate from saving optional Settings preferences. A failed
save keeps the previous theme and the dialog open. Invalid saved preferences fall
back to Original light without replacing their bytes; recovery requires explicitly
checking the preserve-and-replace option, which creates a backup first.

Themes preserve timetable data, course colors, exports, MCP permissions, optional
tools, language and motion settings. Native file pickers and window borders follow
the operating system. Contrast validation and Linux Qt previews do not certify
complete accessibility or packaged Windows behavior.
