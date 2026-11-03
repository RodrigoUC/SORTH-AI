"""Help and user guidance dialog with categorized sections."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QSizePolicy, QVBoxLayout, QHBoxLayout, QStackedWidget
)

from .i18n import msg
from .i18n_widgets import (
    QDialog, QDialogButtonBox, QLabel, QPushButton, QComboBox, QScrollArea, QWidget
)
from .excel_template import TemplateSaveButton, save_import_template
from .app_icons import app_icon


class HelpDialog(QDialog):
    """Categorized help and documentation dialog for SORTH-AI."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Ayuda - SORTH-AI'))
        self.setMinimumSize(660, 560)
        self.resize(720, 620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Header
        header = QFrame()
        header.setObjectName('settingsHeader')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(4)

        title = QLabel(msg('Centro de Ayuda'))
        title.setObjectName('settingsTitle')
        header_layout.addWidget(title)

        subtitle = QLabel(msg('Guía y documentación para la organización y optimización de horarios'))
        subtitle.setObjectName('settingsSubtitle')
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)
        outer.addWidget(header)

        # Section Selector
        self.section_selector = QComboBox()
        self.section_selector.setAccessibleName(msg('Sección de ayuda'))
        self.section_selector.addItem(msg('Flujo de trabajo e inicio rápido'), 'workflow')
        self.section_selector.addItem(msg('Estructura del archivo Excel'), 'excel')
        self.section_selector.addItem(msg('Aulas y restricciones'), 'classrooms')
        self.section_selector.addItem(msg('Generación y semillas'), 'generation')
        self.section_selector.addItem(msg('Visualización y edición'), 'viewer')
        self.section_selector.addItem(msg('Exportación e informes'), 'export')
        self.section_selector.addItem(msg('Atajos de teclado'), 'shortcuts')
        outer.addWidget(self.section_selector)

        # Scroll area containing the stacked sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.stack = QStackedWidget()
        self._build_sections()
        scroll.setWidget(self.stack)
        outer.addWidget(scroll, 1)

        self.section_selector.currentIndexChanged.connect(self.stack.setCurrentIndex)

        # Footer close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        outer.addWidget(buttons)

    def _create_section_container(self) -> tuple[QWidget, QVBoxLayout]:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        return container, layout

    def _add_heading(self, layout: QVBoxLayout, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet('font-size: 13pt; font-weight: bold; margin-bottom: 4px;')
        layout.addWidget(lbl)

    def _add_paragraph(self, layout: QVBoxLayout, text: str):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

    def _add_step(self, layout: QVBoxLayout, step_num: int, title: str, description: str):
        box = QFrame()
        box.setObjectName('settingsSection')
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(12, 10, 12, 10)
        box_layout.setSpacing(4)

        header = QLabel(f'{step_num}. {title}')
        header.setStyleSheet('font-weight: bold; font-size: 10.5pt;')
        box_layout.addWidget(header)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setObjectName('mutedText')
        box_layout.addWidget(desc)

        layout.addWidget(box)

    def _build_sections(self):
        # 1. Workflow
        s1, l1 = self._create_section_container()
        self._add_heading(l1, msg('Flujo de trabajo paso a paso'))
        self._add_paragraph(l1, msg('Sigue estos pasos para generar un horario académico óptimo:'))
        self._add_step(l1, 1, msg('Cargar archivo Excel'),
                       msg('Presiona "Cargar Excel" para importar tu archivo con las hojas "Aulas" y "Cursos".'))
        self._add_step(l1, 2, msg('Revisar cursos y aulas'),
                       msg('En la pestaña "Gestión de Cursos" puedes revisar los cursos importados, editar requisitos o agregar nuevas aulas.'))
        self._add_step(l1, 3, msg('Configurar restricciones de aulas'),
                       msg('Si tienes laboratorios o talleres reservados para cursos específicos, configúralos en "Restricciones de aulas".'))
        self._add_step(l1, 4, msg('Generar el horario'),
                       msg('Presiona "Generar horario". El motor calculará la mejor distribución respetando capacidades y evitando solapamientos.'))
        self._add_step(l1, 5, msg('Inspeccionar y exportar'),
                       msg('Se activará la pestaña "Horario Generado" para examinar el horario en lista o cuadrícula y exportarlo en Excel, PDF o CSV.'))
        l1.addStretch()
        self.stack.addWidget(s1)

        # 2. Excel format
        s2, l2 = self._create_section_container()
        self._add_heading(l2, msg('Estructura requerida del libro Excel'))
        self._add_paragraph(l2, msg('El archivo Excel (.xlsx) debe incluir dos hojas con nombres exactos:'))
        self._add_step(l2, 1, msg('Hoja "Aulas"'),
                       msg('Columnas requeridas: "# DE AULA" (nombre único del aula) y "CAPACIDAD" (número entero mayor o igual a 0).'))
        self._add_step(l2, 2, msg('Hoja "Cursos"'),
                       msg('Columna requerida: "Curso" (código de asignatura). Cada fila representa una sesión o grupo.'))
        self._add_step(l2, 3, msg('Columnas opcionales en "Cursos"'),
                       msg('Puedes incluir "Nombre de Curso", "Horas" (ej: 0800-1055), "Aula" (aula sugerida) y "Días" (ej: L, M, I, J, V, S).'))

        btn_template = TemplateSaveButton(msg('Descargar plantilla Excel de ejemplo…'))
        btn_template.setToolTip(msg('Guardar una plantilla .xlsx con instrucciones y ejemplos ficticios para completar e importar. No cambia la sesión actual.'))
        btn_template.clicked.connect(lambda: save_import_template(self.window))
        btn_template.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        l2.addWidget(btn_template)
        l2.addStretch()
        self.stack.addWidget(s2)

        # 3. Classrooms and restrictions
        s3, l3 = self._create_section_container()
        self._add_heading(l3, msg('Gestión de aulas y restricciones'))
        self._add_paragraph(l3, msg('Configura tus recursos para que el algoritmo respete la exclusividad requerida:'))
        self._add_step(l3, 1, msg('Agregar aula'),
                       msg('Permite añadir aulas adicionales a la sesión sin modificar el archivo Excel original. Útil si faltaba un espacio.'))
        self._add_step(l3, 2, msg('Restricciones de exclusividad'),
                       msg('Permite reservar ciertas aulas únicamente para cursos seleccionados. Los cursos restringidos solo podrán asignarse a su aula designada.'))
        l3.addStretch()
        self.stack.addWidget(s3)

        # 4. Generation parameters
        s4, l4 = self._create_section_container()
        self._add_heading(l4, msg('Parámetros de generación y reproducibilidad'))
        self._add_paragraph(l4, msg('El generador ofrece control total sobre la reproducibilidad de los resultados:'))
        self._add_step(l4, 1, msg('Semilla fija'),
                       msg('Desempata opciones con la misma prioridad de forma determinista. Con los mismos datos y la misma semilla, el horario generado es idéntico.'))
        self._add_step(l4, 2, msg('Semilla aleatoria'),
                       msg('Explora variantes alternativas válidas sin alterar las restricciones ni los requisitos pedagógicos.'))
        l4.addStretch()
        self.stack.addWidget(s4)

        # 5. Viewer and edits
        s5, l5 = self._create_section_container()
        self._add_heading(l5, msg('Visualización y edición de horarios'))
        self._add_paragraph(l5, msg('Una vez generado el horario, dispones de múltiples herramientas para inspeccionar y ajustar:'))
        self._add_step(l5, 1, msg('Vistas disponibles'),
                       msg('Lista detallada con filtros por aula, día o estado; cuadrícula semanal por aula; y vista resumida por aula.'))
        self._add_step(l5, 2, msg('Fijar sesiones'),
                       msg('Puedes fijar una sesión asignada para conservarla intacta ante regeneraciones posteriores del horario.'))
        self._add_step(l5, 3, msg('Asignación manual'),
                       msg('Permite colocar manualmente una sesión en un aula y franja horaria específicas garantizando ausencia de conflictos.'))
        l5.addStretch()
        self.stack.addWidget(s5)

        # 6. Export
        s6, l6 = self._create_section_container()
        self._add_heading(l6, msg('Formatos de exportación'))
        self._add_paragraph(l6, msg('Exporta el resultado final en el formato que mejor se adapte a tus necesidades:'))
        self._add_step(l6, 1, msg('Libro Excel (.xlsx)'),
                       msg('Genera una cuadrícula visual completa para cada aula cubriendo el horario operativo (07:00 a 22:00) y hojas de asignaciones.'))
        self._add_step(l6, 2, msg('Documento PDF'),
                       msg('Genera un archivo PDF con formato limpio listo para imprimir o publicar en tablones informativos.'))
        self._add_step(l6, 3, msg('Archivo CSV'),
                       msg('Exporta datos planos separados por comas para su importación directa en sistemas de gestión académica.'))
        l6.addStretch()
        self.stack.addWidget(s6)

        # 7. Keyboard shortcuts
        s7, l7 = self._create_section_container()
        self._add_heading(l7, msg('Atajos de teclado'))
        self._add_paragraph(l7, msg('Optimiza tu flujo de trabajo con los siguientes atajos:'))

        shortcuts_grid = QFrame()
        shortcuts_grid.setObjectName('settingsSection')
        grid_layout = QGridLayout(shortcuts_grid)
        grid_layout.setContentsMargins(14, 12, 14, 12)
        grid_layout.setHorizontalSpacing(24)
        grid_layout.setVerticalSpacing(10)

        shortcuts = [
            ('F1', msg('Ayuda interactiva')),
            ('Ctrl + O', msg('Cargar archivo Excel')),
            ('Ctrl + Return', msg('Generar horario')),
            ('Ctrl + S', msg('Exportar todas las asignaciones')),
            ('F6', msg('Leer resumen y estado accesible')),
            ('F7', msg('Herramientas del horario')),
        ]

        for row, (key, desc) in enumerate(shortcuts):
            key_lbl = QLabel(key)
            key_lbl.setStyleSheet('font-weight: bold; font-family: monospace; font-size: 10pt;')
            desc_lbl = QLabel(desc)
            grid_layout.addWidget(key_lbl, row, 0)
            grid_layout.addWidget(desc_lbl, row, 1)

        l7.addWidget(shortcuts_grid)
        l7.addStretch()
        self.stack.addWidget(s7)
