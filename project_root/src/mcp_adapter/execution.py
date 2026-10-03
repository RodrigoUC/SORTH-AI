"""Bounded subprocess lifecycle; never abandon a running scheduler on cancel."""
import asyncio
import json
import sys

import anyio

from ..application.preview_contract import MAX_INPUT_BYTES, MAX_OUTPUT_BYTES, ContractError

TIMEOUT_SECONDS = 10


class PreviewExecutor:
    def __init__(self, timeout=TIMEOUT_SECONDS):
        self.timeout = timeout
        self._lock = asyncio.Lock()

    async def generate(self, request):
        if self._lock.locked():
            raise ContractError("BUSY", "request", "One preview is already running. Wait or cancel it before retrying.")
        async with self._lock:
            encoded = json.dumps(request, ensure_ascii=True, allow_nan=False).encode()
            if len(encoded) > MAX_INPUT_BYTES:
                raise ContractError("INPUT_LIMIT", "request", "Reduce the request below 128 KiB.")
            spawning = asyncio.create_task(asyncio.create_subprocess_exec(
                sys.executable, "-B", "-m", "src.mcp_adapter.worker",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
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
                    output, _ = await asyncio.wait_for(process.communicate(encoded), self.timeout)
                except TimeoutError:
                    raise ContractError("TIMEOUT", "request", "Preview exceeded 10 seconds; reduce courses, groups or rooms and retry.") from None
                if process.returncode != 0 or len(output) > MAX_OUTPUT_BYTES:
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
