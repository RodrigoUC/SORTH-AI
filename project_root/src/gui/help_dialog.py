"""Help and user guidance dialog with categorized sections and sidebar navigation."""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QSizePolicy, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget
)

from .i18n import msg
from .i18n_widgets import (
    QDialog, QDialogButtonBox, QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem
)
from .excel_template import TemplateSaveButton, save_import_template
from .app_icons import app_icon


class HelpDialog(QDialog):
    """Categorized help and documentation dialog with sidebar navigation."""

    SECTIONS_METADATA = [
        ('workflow', msg('Flujo de trabajo e inicio rápido'), 'courses',
         msg('Aprende la secuencia recomendada para cargar datos, generar y obtener resultados.')),
        ('excel', msg('Estructura del archivo Excel'), 'upload',
         msg('Requisitos obligatorios y columnas opcionales de las hojas Aulas y Cursos.')),
        ('classrooms', msg('Aulas y restricciones'), 'lock',
         msg('Cómo registrar aulas adicionales y configurar exclusividades por laboratorio o taller.')),
        ('generation', msg('Generación y semillas'), 'sparkles',
         msg('Detalles sobre la reproducibilidad, el azar controlado y la resolución de conflictos.')),
        ('viewer', msg('Visualización y edición'), 'schedule',
         msg('Filtros, inspección en lista o cuadrícula, fijación y colocación manual de sesiones.')),
        ('export', msg('Exportación e informes'), 'export',
         msg('Características de los reportes en formatos Excel (.xlsx), PDF y CSV.')),
        ('shortcuts', msg('Atajos de teclado'), 'settings',
         msg('Accesos rápidos de teclado para operar SORTH con mayor agilidad.')),
    ]

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Ayuda - SORTH-AI'))
        self.setMinimumSize(780, 580)
        self.resize(840, 640)

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

        subtitle = QLabel(msg('Guía interactiva paso a paso para la organización y optimización de horarios académicos'))
        subtitle.setObjectName('settingsSubtitle')
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)
        outer.addWidget(header)

        # Main split: Sidebar list navigation on the left, Scroll content on the right
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        # Sidebar List Widget
        self.nav_list = QListWidget()
        self.nav_list.setObjectName('helpNavList')
        self.nav_list.setAccessibleName(msg('Lista de secciones de ayuda'))
        self.nav_list.setFixedWidth(240)
        self.nav_list.setIconSize(QSize(18, 18))
        self.nav_list.setSpacing(2)

        # Hidden or synchronized combo box for backwards compatibility with tests and accessibility
        self.section_selector = QComboBox()
        self.section_selector.setAccessibleName(msg('Sección de ayuda'))
        self.section_selector.setVisible(False)

        for key, title_text, icon_name, desc_text in self.SECTIONS_METADATA:
            item = QListWidgetItem(app_icon(icon_name), title_text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(desc_text)
            self.nav_list.addItem(item)
            self.section_selector.addItem(title_text, key)

        body_layout.addWidget(self.nav_list)

        # Content area with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName('helpContent')
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(16, 14, 16, 14)
        self.content_layout.setSpacing(12)

        self.sections = {}
        self._build_sections()
        scroll.setWidget(content)
        body_layout.addWidget(scroll, 1)

        outer.addLayout(body_layout, 1)

        # Sync signals between list and combo
        self.nav_list.currentRowChanged.connect(self._on_list_row_changed)
        self.section_selector.currentIndexChanged.connect(self._on_combo_index_changed)

        # Initialize selection to first section
        self.nav_list.setCurrentRow(0)

        # Footer close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        outer.addWidget(buttons)

    def _on_list_row_changed(self, row: int):
        if row < 0 or row >= len(self.SECTIONS_METADATA):
            return
        key = self.SECTIONS_METADATA[row][0]
        if self.section_selector.currentIndex() != row:
            self.section_selector.blockSignals(True)
            self.section_selector.setCurrentIndex(row)
            self.section_selector.blockSignals(False)
        self._show_section(key)

    def _on_combo_index_changed(self, index: int):
        if index < 0 or index >= len(self.SECTIONS_METADATA):
            return
        if self.nav_list.currentRow() != index:
            self.nav_list.blockSignals(True)
            self.nav_list.setCurrentRow(index)
            self.nav_list.blockSignals(False)
        key = self.section_selector.itemData(index)
        self._show_section(key)

    def _show_section(self, active_key: str):
        for key, section_widget in self.sections.items():
            section_widget.setVisible(key == active_key)

    def _create_section_container(self) -> tuple[QWidget, QVBoxLayout]:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        return container, layout

    def _add_heading(self, layout: QVBoxLayout, text: str, subtitle: str = None):
        header_box = QVBoxLayout()
        header_box.setSpacing(3)
        lbl = QLabel(text)
        lbl.setStyleSheet('font-size: 13pt; font-weight: bold; margin-bottom: 2px;')
        header_box.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName('mutedText')
            sub.setWordWrap(True)
            header_box.addWidget(sub)
        layout.addLayout(header_box)

    def _add_paragraph(self, layout: QVBoxLayout, text: str):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

    def _add_step(self, layout: QVBoxLayout, step_num: int, title: str, description: str, hint: str = None):
        box = QFrame()
        box.setObjectName('settingsSection')
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(14, 12, 14, 12)
        box_layout.setSpacing(5)

        header = QLabel(f'{step_num}. {title}')
        header.setStyleSheet('font-weight: bold; font-size: 10.5pt;')
        box_layout.addWidget(header)

        desc = QLabel(description)
        desc.setWordWrap(True)
        box_layout.addWidget(desc)

        if hint:
            hint_lbl = QLabel(f'💡 {hint}')
            hint_lbl.setObjectName('mutedText')
            hint_lbl.setWordWrap(True)
            box_layout.addWidget(hint_lbl)

        layout.addWidget(box)

    def _build_sections(self):
        # 1. Workflow
        s1, l1 = self._create_section_container()
        self._add_heading(
            l1,
            msg('Flujo de trabajo paso a paso'),
            msg('Comprende el recorrido completo desde la importación inicial hasta la publicación de resultados.')
        )
        self._add_paragraph(l1, msg('Sigue esta secuencia para obtener los mejores resultados de planificación:'))
        self._add_step(
            l1, 1, msg('Cargar archivo Excel'),
            msg('Haz clic en el botón "Cargar Excel" (Ctrl + O) para importar el libro con los datos del período lectivo.'),
            msg('El archivo debe tener las hojas obligatorias "Aulas" y "Cursos".')
        )
        self._add_step(
            l1, 2, msg('Revisar cursos y aulas importadas'),
            msg('En la pestaña "Gestión de Cursos" puedes comprobar la lista completa, buscar asignaturas, editar requerimientos o añadir aulas faltantes.'),
            msg('Usa el campo de búsqueda para filtrar rápidamente por código o nombre.')
        )
        self._add_step(
            l1, 3, msg('Configurar restricciones de aulas exclusivas'),
            msg('Si cuentas con laboratorios, talleres de cómputo o espacios que solo pueden usar asignaturas específicas, regístralas en "Restricciones de aulas".'),
            msg('El motor nunca asignará cursos no autorizados en esas aulas reservadas.')
        )
        self._add_step(
            l1, 4, msg('Generar el horario automático'),
            msg('Presiona "Generar horario" (Ctrl + Return). Si ya tenías un horario previo en pantalla, se te solicitará confirmación para proteger tu trabajo.'),
            msg('El motor optimiza capacidades, días preferidos y franjas horarias sin solapamientos.')
        )
        self._add_step(
            l1, 5, msg('Inspeccionar, ajustar y exportar'),
            msg('Al finalizar, pasarás automáticamente a la pestaña "Horario Generado". Podrás ver la lista detallada, la cuadrícula por aula o la vista resumida, y finalmente exportar en Excel, PDF o CSV.'),
            msg('Presiona F6 en cualquier momento para oír o leer un resumen completo de la sesión.')
        )
        l1.addStretch()
        self.sections['workflow'] = s1
        self.content_layout.addWidget(s1)

        # 2. Excel format
        s2, l2 = self._create_section_container()
        self._add_heading(
            l2,
            msg('Estructura del archivo Excel (.xlsx)'),
            msg('Conoce en detalle qué formato espera el sistema para procesar tus horarios sin errores.')
        )
        self._add_paragraph(l2, msg('El libro de cálculo de Microsoft Excel debe contener exactamente dos hojas obligatorias:'))
        self._add_step(
            l2, 1, msg('Hoja "Aulas" (Espacios físicos)'),
            msg('Debe incluir dos columnas principales: "# DE AULA" (nombre único identificador de cada aula) y "CAPACIDAD" (número entero de estudiantes admitidos).'),
            msg('No dejes celdas vacías en la columna del identificador de aula.')
        )
        self._add_step(
            l2, 2, msg('Hoja "Cursos" (Asignaturas y grupos)'),
            msg('Cada fila representa una sesión de clase independiente a programar. La columna obligatoria es "Curso" (código de asignatura, ej: MAT101).'),
            msg('Si una asignatura tiene varios grupos, coloca una fila por cada grupo o sesión.')
        )
        self._add_step(
            l2, 3, msg('Columnas opcionales recomendadas en "Cursos"'),
            msg('• "Nombre de Curso": Título descriptivo para visualización e informes.\n'
                '• "Horas": Franja preferida (ej: 0800-1000).\n'
                '• "Días": Días preferidos (ej: L, M, I, J, V, S o Lunes, Martes...).\n'
                '• "Aula": Aula preferida o sugerida para la asignatura.'),
            msg('Las preferencias ayudan al algoritmo a priorizar la mejor ubicación.')
        )

        btn_template = TemplateSaveButton(msg('Descargar plantilla Excel de ejemplo…'))
        btn_template.setToolTip(msg('Guardar una plantilla .xlsx con instrucciones y ejemplos ficticios para completar e importar. No cambia la sesión actual.'))
        btn_template.clicked.connect(lambda: save_import_template(self.window))
        btn_template.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        l2.addWidget(btn_template)
        l2.addStretch()
        self.sections['excel'] = s2
        self.content_layout.addWidget(s2)

        # 3. Classrooms and restrictions
        s3, l3 = self._create_section_container()
        self._add_heading(
            l3,
            msg('Gestión de aulas y restricciones'),
            msg('Control fino sobre los espacios físicos y la exclusividad académica.')
        )
        self._add_paragraph(l3, msg('Adapta los espacios a las particularidades pedagógicas de cada materia:'))
        self._add_step(
            l3, 1, msg('Agregar aula al vuelo'),
            msg('Permite dar de alta un aula adicional directamente en la sesión activa sin tener que editar ni reimportar el archivo Excel original.'),
            msg('El aula añadida se guardará en la sesión y estará disponible para el generador.')
        )
        self._add_step(
            l3, 2, msg('Restricciones de exclusividad'),
            msg('Configura qué cursos tienen acceso a determinadas aulas especiales (ej. Laboratorio de Química, Sala de Cómputo).'),
            msg('Cuando un aula tiene restricción activa, ninguna otra materia podrá ocupar ese espacio físico, garantizando la reserva.')
        )
        l3.addStretch()
        self.sections['classrooms'] = s3
        self.content_layout.addWidget(s3)

        # 4. Generation parameters
        s4, l4 = self._create_section_container()
        self._add_heading(
            l4,
            msg('Motor de optimización y reproducibilidad'),
            msg('Cómo funciona el generador automático y cómo reproducir o variar los horarios.')
        )
        self._add_paragraph(l4, msg('El motor resuelve un problema de satisfacción de restricciones (CSP) con las siguientes garantías:'))
        self._add_step(
            l4, 1, msg('Semilla fija (Determinismo)'),
            msg('Por defecto, el motor utiliza una semilla fija (ej: 42). Esto garantiza que con el mismo archivo Excel y las mismas restricciones, el horario generado sea exactamente idéntico cada vez.'),
            msg('Ideal para auditorías, revisiones compartidas y estabilidad de resultados.')
        )
        self._add_step(
            l4, 2, msg('Semilla aleatoria (Exploración de alternativas)'),
            msg('Al activar la casilla "Aleatoria", el motor explora caminos alternativos de resolución que cumplan todas las restricciones obligatorias.'),
            msg('Útil cuando deseas evaluar diferentes opciones de distribución sin alterar tus datos.')
        )
        self._add_step(
            l4, 3, msg('Protección ante reemplazo accidental'),
            msg('Si ya has generado un horario y tocas de nuevo el botón de generación, la aplicación te advertirá explícitamente antes de sobrescribir el horario activo.')
        )
        l4.addStretch()
        self.sections['generation'] = s4
        self.content_layout.addWidget(s4)

        # 5. Viewer and edits
        s5, l5 = self._create_section_container()
        self._add_heading(
            l5,
            msg('Visualización y ajustes interactivos'),
            msg('Explora los resultados desde diferentes ángulos y realiza modificaciones manuales con validación de conflictos.')
        )
        self._add_paragraph(l5, msg('La pestaña "Horario Generado" incluye tres modalidades de vista y herramientas de edición:'))
        self._add_step(
            l5, 1, msg('Modalidades de vista'),
            msg('• Lista detallada: Tabla con columnas ordenables y filtros combinados por aula, día y estado.\n'
                '• Cuadrícula por aula: Cronograma semanal visual dividido en bloques horarios de lunes a sábado.\n'
                '• Por aula: Resumen estructurado agrupado por cada espacio físico.')
        )
        self._add_step(
            l5, 2, msg('Asignación manual controlada'),
            msg('Si deseas reubicar una sesión en otro día, hora o aula, selecciónala y pulsa "Asignar manualmente". El sistema verifica instantáneamente que no haya solapamiento de horarios ni de espacio.')
        )
        self._add_step(
            l5, 3, msg('Fijar sesiones asignadas'),
            msg('Puedes marcar sesiones como fijas para que una futura regeneración no las altere, respetando decisiones manuales previas.')
        )
        l5.addStretch()
        self.sections['viewer'] = s5
        self.content_layout.addWidget(s5)

        # 6. Export
        s6, l6 = self._create_section_container()
        self._add_heading(
            l6,
            msg('Formatos de exportación y reportes'),
            msg('Comparte los horarios generados con directores, docentes y estudiantes en formatos estándar.')
        )
        self._add_paragraph(l6, msg('Puedes exportar todas las asignaciones o únicamente las asignaciones que coincidan con tus filtros actuales:'))
        self._add_step(
            l6, 1, msg('Libro Excel profesional (.xlsx)'),
            msg('Genera una cuadrícula visual completa para cada aula cubriendo el horario operativo de 07:00 a 22:00, con formato listo para compartir institucionalmente.')
        )
        self._add_step(
            l6, 2, msg('Documento PDF (.pdf)'),
            msg('Produce un documento formal de alta calidad tipográfica optimizado para impresión directa y carteleras.')
        )
        self._add_step(
            l6, 3, msg('Archivo CSV (.csv)'),
            msg('Exportación estructurada de datos planos para integrar con ERP universitarios o sistemas de gestión de matrícula.')
        )
        l6.addStretch()
        self.sections['export'] = s6
        self.content_layout.addWidget(s6)

        # 7. Keyboard shortcuts
        s7, l7 = self._create_section_container()
        self._add_heading(
            l7,
            msg('Atajos rápidos de teclado'),
            msg('Agiliza las operaciones más frecuentes sin necesidad de usar el ratón.')
        )
        self._add_paragraph(l7, msg('SORTH-AI incluye atajos globales para maximizar la accesibilidad y velocidad:'))

        shortcuts_grid = QFrame()
        shortcuts_grid.setObjectName('settingsSection')
        grid_layout = QGridLayout(shortcuts_grid)
        grid_layout.setContentsMargins(14, 12, 14, 12)
        grid_layout.setHorizontalSpacing(24)
        grid_layout.setVerticalSpacing(10)

        shortcuts = [
            ('F1', msg('Abrir Centro de Ayuda')),
            ('Ctrl + O', msg('Cargar archivo Excel')),
            ('Ctrl + Return', msg('Generar horario académico')),
            ('Ctrl + S', msg('Exportar todas las asignaciones')),
            ('F6', msg('Lectura accesible de estado y resumen de sesión')),
            ('F7', msg('Desplegar menú de herramientas del horario')),
            ('Ctrl + ,', msg('Abrir diálogo de Configuración y temas')),
        ]

        for row, (key, desc) in enumerate(shortcuts):
            key_lbl = QLabel(key)
            key_lbl.setStyleSheet('font-weight: bold; font-family: monospace; font-size: 10pt; color: #2563eb;')
            desc_lbl = QLabel(desc)
            grid_layout.addWidget(key_lbl, row, 0)
            grid_layout.addWidget(desc_lbl, row, 1)

        l7.addWidget(shortcuts_grid)
        l7.addStretch()
        self.sections['shortcuts'] = s7
        self.content_layout.addWidget(s7)
