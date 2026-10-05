"""Read-only client instructions. No client files, credentials or network writes."""
import json
from pathlib import Path, PureWindowsPath

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QPlainTextEdit, QVBoxLayout, QWidget, QScrollArea, QFrame, QSizePolicy

from .i18n import msg, language_manager
from .i18n_widgets import (QComboBox, QDialog, QDialogButtonBox, QLabel, QPushButton,
                           KeyboardLinkLabel, ResponsiveActionLabels, ResponsiveDialogButtonBox)


CLIENT_SOURCES = {
    'opencode': 'https://opencode.ai/v2/docs/mcp-servers',
    'claude': 'https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop',
    'chatgpt': 'https://developers.openai.com/plugins/deploy/connect-chatgpt',
    'chatgpt_desktop': 'https://learn.chatgpt.com/docs/extend/mcp',
}
CLAUDE_CONFIG_SOURCE = 'https://modelcontextprotocol.io/docs/develop/connect-local-servers'
TUNNEL_SOURCE = 'https://developers.openai.com/api/docs/guides/secure-mcp-tunnels'


def client_configuration(client, command):
    """Serialize the verified local command as data, never a shell expression."""
    if (not isinstance(command, (list, tuple)) or len(command) != 2
            or not isinstance(command[0], str) or command[1] != '--serve'
            or not (Path(command[0]).is_absolute() or PureWindowsPath(command[0]).is_absolute())):
        raise ValueError('A verified companion command is required')
    if client == 'chatgpt_desktop':
        return str(msg('Nombre: sorth-preview\nTipo: STDIO\nComando para iniciar: {command}\nArgumentos: --serve\nVariables del entorno: ninguna requerida', command=command[0]))
    if client == 'opencode':
        value = {'mcp': {'servers': {'sorth-preview': {
            'type': 'local', 'command': list(command), 'disabled': True,
            'protocol': 'legacy',
        }}}}
    elif client == 'claude':
        value = {'mcpServers': {'sorth-preview': {
            'command': command[0], 'args': command[1:],
        }}}
    else:
        raise ValueError('This client has no direct stdio configuration')
    return json.dumps(value, ensure_ascii=False, indent=2)


class McpClientHelp(QDialog):
    def __init__(self, command, parent=None, *, permission_enabled=None, pending_permission=False):
        super().__init__(parent)
        self.command = list(command) if command else None
        self.setWindowTitle(msg('Guía de conexión MCP'))
        self.resize(660, 560)
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        intro = QLabel(msg('Sigue los pasos en tu cliente. Esta guía solo muestra instrucciones y no modifica otras apps.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.client = QComboBox()
        self.client.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.client.setAccessibleName(msg('Cliente MCP'))
        for title, key in [('OpenCode V2', 'opencode'), ('Claude Desktop', 'claude'), (msg('ChatGPT web (conexión remota)'), 'chatgpt'), (msg('ChatGPT de escritorio (STDIO)'), 'chatgpt_desktop')]:
            self.client.addItem(title, key)
        client_label = QLabel(msg('Cliente MCP'))
        client_label.setBuddy(self.client)
        layout.addWidget(client_label)
        layout.addWidget(self.client)
        self.permission_status = QLabel()
        self.permission_status.setWordWrap(True)
        self.permission_status.setTextFormat(Qt.TextFormat.PlainText)
        self.permission_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.permission_status.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if pending_permission:
            saved_status = (msg('Permiso local guardado: activado.') if permission_enabled is True
                            else msg('Permiso local guardado: desactivado.'))
            self.permission_status.setText(saved_status + ' ' + msg('Hay un cambio de permiso sin guardar. Cierra esta guía, revisa la casilla y pulsa Guardar antes de conectar.'))
        elif permission_enabled is True:
            self.permission_status.setText(msg('Permiso local guardado: activado. Aún debes configurar y autorizar la conexión en el cliente.'))
        elif permission_enabled is False:
            self.permission_status.setText(msg('Permiso local guardado: desactivado.') + ' ' + msg('Antes de conectar, marca Permitir servidor MCP local y pulsa Guardar en Configuración.'))
        else:
            self.permission_status.setText(msg('Antes de conectar, marca Permitir servidor MCP local y pulsa Guardar en Configuración.'))
        layout.addWidget(self.permission_status)
        self.instructions = QLabel()
        self.instructions.setWordWrap(True)
        self.instructions.setTextFormat(Qt.TextFormat.PlainText)
        self.instructions.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.instructions.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.instructions)
        self.configuration = QPlainTextEdit()
        self.configuration.setReadOnly(True)
        self.configuration.setTabChangesFocus(True)
        self.configuration.setMinimumHeight(180)
        self.configuration.setAccessibleName(str(msg('Configuración del cliente para copiar')))
        self.configuration.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.configuration, 1)
        self.copy_button = QPushButton(msg('Copiar configuración'))
        self.copy_button.clicked.connect(self._copy)
        layout.addWidget(self.copy_button)
        self.copy_status = QLabel()
        self.copy_status.setWordWrap(True)
        self.copy_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.copy_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.copy_status)
        self.empty_space = QWidget()
        layout.addWidget(self.empty_space, 1)
        self.source = KeyboardLinkLabel()
        self.source.setWordWrap(True)
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.source.setOpenExternalLinks(True)
        layout.addWidget(self.source)
        privacy = QLabel(msg('Antes de compartir datos, revisa la privacidad, los permisos y los posibles cargos del proveedor. Estas conexiones comerciales aún no se han probado.'))
        privacy.setWordWrap(True)
        privacy.setObjectName('mutedText')
        layout.addWidget(privacy)
        self.buttons = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._responsive_actions = ResponsiveActionLabels(self.scroll, [self.copy_button], self)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_focus)
        self.scroll.viewport().installEventFilter(self)
        content.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        self.setTabOrder(self.client, self.permission_status)
        self.setTabOrder(self.permission_status, self.instructions)
        self.setTabOrder(self.instructions, self.configuration)
        self.setTabOrder(self.configuration, self.copy_button)
        self.setTabOrder(self.copy_button, self.copy_status)
        self.setTabOrder(self.copy_status, self.source)
        self.setTabOrder(self.source, self.buttons.button(QDialogButtonBox.StandardButton.Close))
        self.client.currentIndexChanged.connect(self._update)
        language_manager().changed.connect(self._language_changed)
        self._update()
        self.client.setFocus(Qt.FocusReason.TabFocusReason)

    def _language_changed(self):
        self.configuration.setAccessibleName(str(msg('Configuración del cliente para copiar')))
        if self.client.currentData() == 'chatgpt_desktop' and self.command is not None:
            cursor = self.configuration.textCursor()
            selection = cursor.selectedText()
            old_position = cursor.position()
            content = client_configuration('chatgpt_desktop', self.command)
            self.configuration.setPlainText(content)
            document = self.configuration.document()
            cursor = document.find(selection) if selection else self.configuration.textCursor()
            if not selection or cursor.isNull():
                cursor = self.configuration.textCursor()
                cursor.setPosition(min(old_position, document.characterCount() - 1))
            self.configuration.setTextCursor(cursor)

    def _scroll_to_focus(self, previous, focused):
        if (self.isVisible() and focused is not None
                and self.scroll.widget().isAncestorOf(focused)):
            self._reveal_focus()
            self._focus_reveal_timer.start(0)

    def _reveal_focus(self):
        focused = QApplication.focusWidget()
        if (self.isVisible() and focused is not None and focused.isVisible()
                and self.scroll.widget().isAncestorOf(focused)):
            # Native QLabel link traversal can leave its frame offscreen,
            # especially with Shift+Tab. Reveal the actual focused control;
            # taller selectable instructions remain centered and scrollable.
            center = focused.mapTo(self.scroll.widget(), focused.rect().center())
            self.scroll.ensureVisible(center.x(), center.y(), 0,
                min(self.scroll.viewport().height() // 2, focused.height() // 2 + 12))

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest,
                            QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._focus_reveal_timer.start(0)
        return super().eventFilter(watched, event)

    def _update(self):
        client = self.client.currentData()
        instructions = {
            'opencode': '1. Copia esta configuración y combina sorth-preview en mcp.servers de opencode.jsonc. Conserva las otras entradas.\n2. Empieza desconectada (disabled: true) y usa protocol: legacy.\n3. Tras guardar el permiso en SORTH, revisa las herramientas y conecta con /mcps.',
            'claude': '1. Copia esta configuración y combina sorth-preview en mcpServers de la configuración local de Claude Desktop. Conserva los otros servidores.\n2. Guarda primero el permiso MCP en SORTH. Reiniciar Claude puede iniciar el servidor.\n3. Revisa y autoriza las herramientas en Claude. Este flujo no genera extensiones MCPB.',
            'chatgpt': 'ChatGPT web usa una conexión remota; no puede ejecutar esta ruta local como URL. Requiere HTTPS o Secure MCP Tunnel con autorización independiente.\n\n1. Si tu cliente muestra un formulario STDIO, elige ChatGPT de escritorio en esta guía.\n2. Para la conexión web, consulta las instrucciones oficiales y autoriza sus permisos y credenciales por separado.\n\nSORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT.',
            'chatgpt_desktop': '1. En ChatGPT de escritorio, abre la configuración de servidores MCP y añade un servidor con tipo STDIO. Este flujo requiere un cliente con ejecución local en el mismo equipo que SORTH.\n2. Tras guardar el permiso MCP en SORTH, copia cada valor de abajo en su campo: comando y argumentos van separados. No uses SORTH.exe ni el comando de ejemplo del formulario.\n3. Guarda la configuración y revisa los permisos del cliente antes de iniciar o reiniciar el servidor. La conexión con ChatGPT aún no se ha probado.',
        }
        self.instructions.setText(msg(instructions[client]))
        can_copy = self.command is not None and client != 'chatgpt'
        if can_copy:
            self.configuration.setPlainText(client_configuration(client, self.command))
        elif client != 'chatgpt':
            self.instructions.setText(msg('Prepara y verifica el complemento para obtener su ruta exacta. En desarrollo desde código fuente, consulta MCP_OPTIONAL.md: se usa un entorno Python separado con su directorio de trabajo.'))
            self.configuration.clear()
        else:
            self.configuration.clear()
        self.configuration.setVisible(can_copy)
        self.copy_button.setEnabled(can_copy)
        self.copy_button.setVisible(client != 'chatgpt')
        self.empty_space.setVisible(not can_copy)
        self.copy_status.clear()
        self.copy_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        source = CLIENT_SOURCES[client]
        self.source.setText(msg('<a href="{url}">Instrucciones oficiales del cliente</a>', url=source))
        if client == 'claude':
            self.source.setText(msg('<a href="{url}">Instrucciones oficiales del cliente</a>', url=source)
                                + '<br>' + msg('<a href="{url}">Configuración local de MCP</a>', url=CLAUDE_CONFIG_SOURCE))
        if client == 'chatgpt':
            self.source.setText(msg('<a href="{url}">Instrucciones oficiales del cliente</a>', url=source)
                                + '<br>' + msg('<a href="{url}">Guía oficial de Secure MCP Tunnel</a>', url=TUNNEL_SOURCE))

    def _copy(self):
        if self.copy_button.isEnabled():
            QApplication.clipboard().setText(self.configuration.toPlainText())
            self.copy_status.setText(msg('Configuración copiada. Revisa y combínala con la configuración existente de tu cliente.'))
            self.copy_status.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
