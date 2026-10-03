"""Read-only client instructions. No client files, credentials or network writes."""
import json
from pathlib import Path, PureWindowsPath

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPlainTextEdit, QVBoxLayout, QWidget

from .i18n import msg, language_manager
from .i18n_widgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QPushButton


CLIENT_SOURCES = {
    'opencode': 'https://opencode.ai/v2/docs/mcp-servers',
    'claude': 'https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop',
    'chatgpt': 'https://developers.openai.com/plugins/deploy/connect-chatgpt',
}
CLAUDE_CONFIG_SOURCE = 'https://modelcontextprotocol.io/docs/develop/connect-local-servers'
TUNNEL_SOURCE = 'https://developers.openai.com/api/docs/guides/secure-mcp-tunnels'


def client_configuration(client, command):
    """Serialize the verified local command as data, never a shell expression."""
    if (not isinstance(command, (list, tuple)) or len(command) != 2
            or not isinstance(command[0], str) or command[1] != '--serve'
            or not (Path(command[0]).is_absolute() or PureWindowsPath(command[0]).is_absolute())):
        raise ValueError('A verified companion command is required')
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
    def __init__(self, command, parent=None):
        super().__init__(parent)
        self.command = list(command) if command else None
        self.setWindowTitle(msg('Conectar un cliente MCP'))
        self.resize(660, 560)
        layout = QVBoxLayout(self)
        intro = QLabel(msg('Elige tu cliente. Esta guía no modifica su configuración. Revisa privacidad, permisos y posibles cargos del proveedor antes de conectar datos. No se han probado estos hosts comerciales.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.client = QComboBox()
        self.client.setAccessibleName(msg('Cliente MCP'))
        for title, key in [('OpenCode V2', 'opencode'), ('Claude Desktop', 'claude'), ('ChatGPT', 'chatgpt')]:
            self.client.addItem(title, key)
        layout.addWidget(self.client)
        self.instructions = QLabel()
        self.instructions.setWordWrap(True)
        self.instructions.setTextFormat(Qt.TextFormat.PlainText)
        self.instructions.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.instructions)
        self.configuration = QPlainTextEdit()
        self.configuration.setReadOnly(True)
        self.configuration.setAccessibleName(str(msg('Configuración del cliente para copiar')))
        self.configuration.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.configuration, 1)
        self.copy_button = QPushButton(msg('Copiar configuración'))
        self.copy_button.clicked.connect(self._copy)
        layout.addWidget(self.copy_button)
        self.copy_status = QLabel()
        self.copy_status.setWordWrap(True)
        layout.addWidget(self.copy_status)
        self.empty_space = QWidget()
        layout.addWidget(self.empty_space, 1)
        self.source = QLabel()
        self.source.setWordWrap(True)
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.source.setOpenExternalLinks(True)
        layout.addWidget(self.source)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.client.currentIndexChanged.connect(self._update)
        language_manager().changed.connect(self._language_changed)
        self._update()

    def _language_changed(self):
        self.configuration.setAccessibleName(str(msg('Configuración del cliente para copiar')))

    def _update(self):
        client = self.client.currentData()
        instructions = {
            'opencode': 'Añade esta entrada a mcp.servers en opencode.jsonc sin reemplazar otras entradas. Empieza desconectada (disabled: true). Después de guardar el permiso MCP en SORTH, revisa las herramientas y conecta con /mcps. Usa protocol: legacy.',
            'claude': 'Integra esta entrada en mcpServers de la configuración local de Claude Desktop sin reemplazar otros servidores. Al reiniciar el cliente puede iniciar el proceso; primero guarda el permiso MCP en SORTH. Claude admite extensiones MCPB, pero SORTH no genera un paquete MCPB en este flujo.',
            'chatgpt': 'ChatGPT necesita una conexión HTTPS o Secure MCP Tunnel autorizada por separado; esta ruta local no es una URL. El túnel requiere sus propios permisos y credenciales. SORTH no crea túneles ni claves, no abre puertos y no configura ChatGPT. Consulta las instrucciones oficiales y las reglas de tu organización.',
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
