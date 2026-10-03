"""Real held-open descendant pipe regression, including Windows job ownership."""
import os
from pathlib import Path
import subprocess
import sys
import time

from src.application.mcp_probe_process import WindowsProbeJob, read_available, stop_owned_process


def test_owned_probe_descendants_do_not_hold_pipe_or_survive_cleanup(tmp_path):
    sentinel = tmp_path / 'descendant-survived'
    child_code = 'import time; from pathlib import Path; time.sleep(1); Path(' + repr(str(sentinel)) + ').write_text("alive"); time.sleep(30)'
    code = ('import subprocess, sys, time\n'
            'time.sleep(0.15)\n'
            'subprocess.Popen([sys.executable, "-c", ' + repr(child_code) + '])\n'
            'print("spawned", flush=True)\n'
            'time.sleep(30)\n')
    job = WindowsProbeJob() if os.name == 'nt' else None
    process = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               start_new_session=os.name != 'nt',
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        if job is not None:
            job.attach(process)
        output = b''
        deadline = time.monotonic() + 5
        while b'spawned' not in output:
            assert time.monotonic() < deadline
            output += read_available(process.stdout, 100)
            time.sleep(0.01)
        started = time.monotonic()
        stop_owned_process(process, job)
        process.stdout.close()
        assert time.monotonic() - started < 2.5
        assert process.returncode is not None
        time.sleep(1.1)
        assert not sentinel.exists()
    finally:
        if process.poll() is None:
            stop_owned_process(process, job)
        if not process.stdout.closed:
            process.stdout.close()
