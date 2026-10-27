# Decisión 0001: dominio, casos de uso y adaptadores

Estado: aplicada. Actualizada el 27 de octubre de 2026.

## Contexto

La aplicación necesita conservar un único modelo de horarios y reutilizar sus
reglas desde escritorio, CLI y MCP. Las dependencias de Qt, archivos, red y procesos
no deben formar parte de los casos de uso.

## Decisión

Conservar el monolito modular con las capas descritas en
[Arquitectura y responsabilidades](../ARCHITECTURE.md). Inyectar los lectores en
`SchedulingService`; ubicar operaciones de sistema en infraestructura y composición
en `bootstrap`. Separar la coordinación de importación, exportación y recuperación
de la ventana principal mediante controladores.

Mantener exclusivamente los contratos vigentes: esquema de sesión 5, catálogo 2,
metadatos de escenario 2 y encabezados Excel documentados. Rechazar otros formatos
sin mutarlos. No mantener interfaces alternativas, scripts de reenvío ni conversión
implícita de preferencias o datos antiguos.

## Consecuencias

Los consumidores componen sus adaptadores explícitamente. Los cambios de formato
son deliberadamente incompatibles y deben documentarse. Los datos anteriores quedan
intactos; no se migran ni se reemplazan para forzar el inicio.

El guard AST impide dependencias inversas y las pruebas comprueban persistencia,
rechazo sin mutación, cancelación y rollback. No se introducen un contenedor global,
un ORM ni un sistema de eventos para resolver dependencias locales.
