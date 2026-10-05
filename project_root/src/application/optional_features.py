"""Pure optional-feature catalog shared by desktop and headless configuration."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Feature:
    key: str
    title: str
    description: str


FEATURES = (
    Feature('auto_update_check', 'Avisar de actualizaciones al iniciar',
            'Consulta GitHub al abrir SORTH y muestra un aviso si hay una versión nueva. GitHub recibe la dirección IP y los datos habituales de conexión; no se envían horarios ni datos académicos. No descarga ni instala nada.'),
    Feature('mcp_server', 'Permitir servidor MCP local',
            'Permitir que un cliente inicie el servidor stdio. No inicia procesos, conecta modelos ni instala componentes.'),
    Feature('import_diff_preview', 'Vista previa de cambios del Excel',
            'Revisar cursos, aulas, restricciones y asignaciones antes de reemplazar la sesión.'),
    Feature('placement_suggestions', 'Opciones de ubicación', 'Mostrar ubicaciones válidas para sesiones pendientes sin mover otras sesiones.'),
    Feature('pinned_sessions', 'Herramientas de sesiones fijadas',
            'Mostrar controles para fijar o desfijar. Las fijaciones guardadas siempre se respetan.'),
    Feature('project_scenarios', 'Herramientas de proyectos y escenarios',
            'Mostrar controles para guardar, abrir y comparar copias independientes.'),
    Feature('project_calendar', 'Parámetros avanzados del calendario',
            'Mostrar el editor de días, horas y descansos del proyecto. El calendario guardado siempre se respeta.'),
    Feature('teacher', 'Docentes', 'Asignar docentes por sesión y evitar cruces de horario.'),
    Feature('student_group', 'Grupos de estudiantes', 'Asignar grupos compartidos y evitar cruces de horario.'),
    Feature('student', 'Estudiantes individuales', 'Asignar personas explícitas con alias locales y evitar cruces.'),
    Feature('bulk_operations', 'Edición de cursos en lote',
            'Cambiar campos seleccionados con revisión previa. Requiere activar Deshacer y rehacer.'),
    Feature('undo_redo', 'Deshacer y rehacer',
            'Revertir cambios locales de esta sesión. Máximo 50 cambios o 16 MiB; importar o restaurar reinicia el historial.'),
)

