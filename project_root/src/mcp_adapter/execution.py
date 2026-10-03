"""Bounded subprocess lifecycle; never abandon a running scheduler on cancel."""
import asyncio
import json
import sys
from pathlib import Path

import anyio

from ..application.preview_contract import MAX_INPUT_BYTES, MAX_OUTPUT_BYTES, ContractError
from .artifacts import MAX_EXPORT_OUTPUT_BYTES

TIMEOUT_SECONDS = 10


class PreviewExecutor:
    def __init__(self, timeout=TIMEOUT_SECONDS, *, packaged=False):
        self.timeout = timeout
        self.packaged = packaged
        self._lock = asyncio.Lock()

    def worker_command(self):
        if getattr(sys, 'frozen', False):
            if not self.packaged:
                raise ContractError('WORKER_FAILED', 'request', 'Use the verified MCP companion.')
            return [sys.executable, '--worker']
        return [sys.executable, '-B', '-m', 'src.mcp_adapter.worker']

    async def generate(self, request):
        return await self._run(request, export=False)

    async def generate_excel(self, request):
        return await self._run(request, export=True)

    async def _run(self, request, *, export):
        if self._lock.locked():
            raise ContractError("BUSY", "request", "One preview is already running. Wait or cancel it before retrying.")
        async with self._lock:
            payload = {"operation": "excel", "request": request} if export else request
            encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode()
            output_limit = MAX_EXPORT_OUTPUT_BYTES if export else MAX_OUTPUT_BYTES
            if len(encoded) > MAX_INPUT_BYTES:
                raise ContractError("INPUT_LIMIT", "request", "Reduce the request below 128 KiB.")
            spawning = asyncio.create_task(asyncio.create_subprocess_exec(
                *self.worker_command(),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=None if getattr(sys, 'frozen', False) else str(Path(__file__).resolve().parents[2]),
            ))
            try:
                process = await asyncio.shield(spawning)
            except asyncio.CancelledError:
                # Cancellation may arrive while the OS is creating the child.
                # Finish acquiring its handle before reaping it.
                with anyio.CancelScope(shield=True):
                    process = await spawning
                    if process.returncode is None:
                        process.kill()
                    await asyncio.shield(process.wait())
                raise
            try:
                try:
                    output = await asyncio.wait_for(self._communicate(process, encoded, output_limit), self.timeout)
                except TimeoutError:
                    raise ContractError("TIMEOUT", "request", "Preview exceeded 10 seconds; reduce courses, groups or rooms and retry.") from None
                if process.returncode != 0 or len(output) > output_limit:
                    raise ContractError("WORKER_FAILED", "result", "Preview worker failed safely; reduce the request and retry.")
                response = json.loads(output)
                if "error" in response:
                    error = response["error"]
                    raise ContractError(error["code"], error["path"], error["message"])
                return response["result"]
            finally:
                with anyio.CancelScope(shield=True):
                    if process.returncode is None:
                        # A CPU-bound scheduler cannot observe an async token.
                        # The worker owns no persisted state.
                        process.kill()
                    await asyncio.shield(process.wait())

    @staticmethod
    async def _communicate(process, encoded, output_limit):
        process.stdin.write(encoded)
        await process.stdin.drain()
        process.stdin.close()
        chunks, size = [], 0
        while True:
            chunk = await process.stdout.read(min(65536, output_limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > output_limit:
                raise ContractError("OUTPUT_LIMIT", "result", "Worker output exceeded the bounded response size.")
        await process.wait()
        return b"".join(chunks)
