"""Windows-only, synthetic no-Python-PATH frozen MCP acceptance harness.

The host interpreter supplies the SDK client only. Every server/worker must run
from the frozen companion, with Python locations removed from the child PATH.
This is CI evidence, not a clean Windows machine certification.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def request():
    return {'courses': [{'code': 'BIO', 'number_of_groups': 2, 'duration_min': 60,
                         'required_room_type': 'REGULAR', 'size': 20}],
            'classrooms': [{'name': 'A1', 'capacity': 30, 'room_type': 'REGULAR'}], 'seed': 42}


def isolated_environment(directory):
    environment = dict(os.environ)
    system = Path(os.environ['SystemRoot'])
    environment['PATH'] = str(system / 'System32') + os.pathsep + str(system)
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    environment.update(LOCALAPPDATA=str(directory / 'Local'), APPDATA=str(directory / 'Roaming'),
                       XDG_CONFIG_HOME=str(directory / 'Config'), XDG_DATA_HOME=str(directory / 'Data'),
                       PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    return environment


async def sdk_contract(executable, preferences, environment, directory):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from src.application.mcp_preferences import set_enabled
    parameters = StdioServerParameters(command=str(executable),
                                       args=['--serve', '--preferences', str(preferences)],
                                       env=environment, cwd=str(directory))
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            require(initialized.serverInfo.name == 'sorth-preview', 'Unexpected MCP server')
            listed = await session.list_tools()
            require({t.name for t in listed.tools} == {'validate_configuration', 'generate_preview'},
                    'Unexpected MCP tool inventory')
            checked = await session.call_tool('validate_configuration', request())
            require(not checked.isError, 'Frozen validation failed')
            generated = await session.call_tool('generate_preview', request())
            require(not generated.isError and generated.structuredContent['status'] == 'complete',
                    'Frozen scheduling worker failed')
            repeated = await session.call_tool('generate_preview', request())
            require(repeated.structuredContent == generated.structuredContent, 'Nondeterministic frozen worker')
            set_enabled(preferences, False)
            disabled = await session.call_tool('generate_preview', request())
            require(disabled.isError and disabled.structuredContent['error']['code'] == 'MCP_DISABLED',
                    'Live disabled permission was ignored')
    return initialized.protocolVersion


async def wire_cancellation(executable, preferences, environment, directory):
    process = await asyncio.create_subprocess_exec(
        str(executable), '--serve', '--preferences', str(preferences),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, env=environment, cwd=directory)

    async def send(message):
        process.stdin.write(json.dumps(message).encode('utf-8') + b'\n')
        await process.stdin.drain()

    async def receive(identifier):
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), 20)
            require(bool(line), 'Frozen server closed before response')
            response = json.loads(line)
            if response.get('id') == identifier:
                return response

    try:
        await send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-06-18', 'capabilities': {},
            'clientInfo': {'name': 'sorth-frozen-test', 'version': '1'}}})
        require('result' in await receive(1), 'Wire initialization failed')
        await send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        await send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {
            'name': 'generate_preview', 'arguments': request()}})
        await send({'jsonrpc': '2.0', 'method': 'notifications/cancelled',
                    'params': {'requestId': 2, 'reason': 'synthetic CI cancellation'}})
        await send({'jsonrpc': '2.0', 'id': 3, 'method': 'ping'})
        require('result' in await receive(3), 'Frozen cancellation broke transport')
        deadline = asyncio.get_running_loop().time() + 20
        identifier = 4
        while True:
            await send({'jsonrpc': '2.0', 'id': identifier, 'method': 'tools/call',
                        'params': {'name': 'generate_preview', 'arguments': request()}})
            result = (await receive(identifier))['result']
            if not result.get('isError'):
                require(result['structuredContent']['status'] == 'complete', 'Post-cancel worker failed')
                break
            require(result['structuredContent']['error']['code'] == 'BUSY', 'Unexpected post-cancel error')
            require(asyncio.get_running_loop().time() < deadline, 'Cancelled frozen worker was not reaped')
            await asyncio.sleep(0.02)
            identifier += 1
    finally:
        process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), 10)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


def prepare_from_gui(app_dir, identity_dir, directory, environment):
    from PyInstaller.archive.readers import CArchiveReader
    from src.application.mcp_component import ComponentContext, ComponentError, prepare_component
    from src.application.mcp_preferences import set_enabled
    from tools.mcp_payload import verify_payload
    app_dir = Path(app_dir).resolve(strict=True)
    bundle_dir = app_dir / '_internal'
    manifest = verify_payload(bundle_dir / 'optional/mcp-component.zip', identity_dir,
                              os.environ['SOURCE_COMMIT'])
    package = CArchiveReader(str(app_dir / 'SORTH.exe'))
    pyz_name = next(name for name, row in package.toc.items() if row[-1] == 'z')
    pyz = package.open_embedded_archive(pyz_name)
    require('_sorth_mcp_bundle' in pyz.toc, 'GUI is missing the compiled payload trust anchor')
    require(not any(n == 'mcp' or n.startswith('mcp.') for n in pyz.toc), 'MCP SDK leaked into GUI')
    frozen_code = pyz.extract('_sorth_mcp_bundle')
    source = (Path(identity_dir) / '_sorth_mcp_bundle.py').read_text(encoding='utf-8')
    expected_code = compile(source, '<generated-anchor>', 'exec')
    require((frozen_code.co_code, frozen_code.co_consts, frozen_code.co_names) ==
            (expected_code.co_code, expected_code.co_consts, expected_code.co_names),
            'Compiled GUI trust anchor differs from verified build input')
    preferences = directory / 'synthetic-preferences.json'
    set_enabled(preferences, False)
    before = preferences.read_bytes()
    context = ComponentContext(manifest, bundle_dir, directory / 'components')
    original_environment = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(environment)
        first = prepare_component(context=context)
        second = prepare_component(context=context)
        require(not first['already_prepared'] and second['already_prepared'], 'Preparation is not idempotent')
        require(preferences.read_bytes() == before, 'Preparation changed consent preferences')
        # A corrupt archive cannot be accepted even when its readable JSON is unchanged.
        bad_root = directory / 'corrupt-bundle'
        (bad_root / 'optional').mkdir(parents=True)
        shutil.copyfile(bundle_dir / 'optional/mcp-component.zip', bad_root / 'optional/mcp-component.zip')
        with (bad_root / 'optional/mcp-component.zip').open('ab') as stream:
            stream.write(b'corrupt-test-only')
        bad_context = ComponentContext(manifest, bad_root, directory / 'corrupt-components')
        try:
            prepare_component(context=bad_context)
        except ComponentError as error:
            require(error.code == 'integrity_error', 'Unexpected corrupt payload rejection')
        else:
            raise ValueError('Corrupt payload was accepted')
    finally:
        os.environ.clear()
        os.environ.update(original_environment)
    return Path(first['command'][0]), context


def run(app_dir, identity_dir, output):
    require(sys.platform == 'win32', 'Frozen Windows acceptance must run on Windows')
    from src.application.mcp_preferences import set_enabled
    from src.application.mcp_component import ComponentError, installed_command
    from tools.build_identity import identity
    expected = identity(os.environ['SOURCE_COMMIT'])
    with tempfile.TemporaryDirectory(prefix='sorth-frozen-mcp-') as temporary:
        directory = Path(temporary)
        environment = isolated_environment(directory)
        executable, context = prepare_from_gui(app_dir, identity_dir, directory, environment)
        preferences = directory / 'synthetic-preferences.json'
        sentinel = directory / 'synthetic-session.db'
        sentinel.write_bytes(b'synthetic-existing-session-must-not-change')
        original = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
        probe = subprocess.run([str(executable), '--probe'], env=environment, cwd=directory,
                               capture_output=True, text=True, timeout=20, check=False)
        require(probe.returncode == 0 and not probe.stderr, 'Frozen probe failed')
        status = json.loads(probe.stdout)
        require(status['status'] == 'available' and status['frozen'] is True
                and status['sdk_version'] == '1.30.0', 'Frozen probe SDK metadata missing')
        require(all(status[k] == expected[k] for k in ('version', 'source_commit', 'build_id')),
                'Frozen companion build identity mismatch')
        require(json.loads(preferences.read_text())['features']['mcp_server'] is False,
                'Probe changed synthetic preferences')
        set_enabled(preferences, True)
        asyncio.run(asyncio.wait_for(wire_cancellation(executable, preferences, environment, directory), 90))
        protocol = asyncio.run(asyncio.wait_for(sdk_contract(executable, preferences, environment, directory), 90))
        rejected = subprocess.run([str(executable), '--serve', '--preferences', str(preferences)],
                                  env=environment, cwd=directory, capture_output=True,
                                  text=True, timeout=20, check=False)
        require(rejected.returncode == 3 and not rejected.stdout, 'Disabled companion startup was accepted')
        require((sentinel.read_bytes(), sentinel.stat().st_mtime_ns) == original, 'Synthetic session was modified')
        executable.unlink()
        try:
            installed_command(context=context)
        except ComponentError:
            pass
        else:
            raise ValueError('Incomplete installed component was accepted')
        report = {'ok': True, 'frozen': True, 'python_free_child_path': environment['PATH'],
                  'source_commit': expected['source_commit'], 'build_id': expected['build_id'],
                  'sdk_version': status['sdk_version'], 'protocol_version': protocol,
                  'checks': ['compiled_gui_anchor', 'sdk_absent_from_gui', 'install', 'idempotent_install',
                             'consent_unchanged', 'corrupt_payload_rejected', 'incomplete_install_rejected',
                             'probe_metadata', 'initialize', 'tools_list', 'tools_call',
                             'frozen_worker', 'determinism', 'cancel_then_call',
                             'live_disable', 'disabled_restart', 'session_unchanged'],
                  'clean_machine_validation': False}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    # Keep a source SDK runner separate from the frozen child. Absolute host
    # interpreter invocation is intentional; no Python is available in child PATH.
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', type=Path, default=ROOT / 'dist/SORTH')
    parser.add_argument('--identity-dir', type=Path, default=ROOT / 'build/identity')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/reports/mcp-frozen-smoke.json')
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.app_dir, arguments.identity_dir, arguments.output), indent=2))
