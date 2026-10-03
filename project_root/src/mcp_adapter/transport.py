"""Local stdio only, with bounded frames and sanitized protocol parse errors."""
from contextlib import asynccontextmanager
import asyncio
import json
import os
import sys
import threading

import anyio
from mcp import types
from mcp.shared.message import SessionMessage

from ..application.preview_contract import MAX_INPUT_BYTES


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


def parse_message(raw):
    # Reject ambiguous duplicate keys, nonfinite numbers, excessive nesting and
    # malformed envelopes before the SDK can include raw data in diagnostics.
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite")))
    if not isinstance(value, dict):
        raise ValueError("Expected an object")
    if "id" in value and (type(value["id"]) not in (int, str)
                          or len(str(value["id"])) > 128):
        raise ValueError("Invalid request identifier")
    if "method" in value and (type(value["method"]) is not str or len(value["method"]) > 128):
        raise ValueError("Invalid method")
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 20:
            raise ValueError("Nesting limit")
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return types.JSONRPCMessage.model_validate(value)


async def _daemon_io(function, *args):
    """Await raw pipe I/O without making peer-owned pipes block cancellation.

    Dedicated daemon threads are intentional: cancelling a stdio wait cannot
    interrupt a blocking OS pipe portably. Unlike executor workers, these do not
    hold up asyncio/interpreter shutdown. Use only raw os.read/os.write here:
    buffered Python stdin/stdout locks held during finalization can deadlock.
    At most one read and one write are awaited; abandoning either ends transport.
    The process owns these stdio descriptors until normal OS process teardown.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def deliver(value, error):
        if not future.done():
            if error is not None:
                future.set_exception(error)
            else:
                future.set_result(value)

    def work():
        try:
            value, error = function(*args), None
        except Exception as exc:
            value, error = None, exc
        try:
            loop.call_soon_threadsafe(deliver, value, error)
        except RuntimeError:
            # Cancellation already closed the loop; no state/result to retain.
            pass

    threading.Thread(target=work, daemon=True, name="sorth-stdio").start()
    return await future


def _write_all(descriptor, encoded):
    view = memoryview(encoded)
    while view:
        written = os.write(descriptor, view)
        if written == 0:
            raise BrokenPipeError("stdio closed")
        view = view[written:]


class _FrameReader:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.buffer = bytearray()

    def readline(self):
        while True:
            newline = self.buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self.buffer[:newline + 1])
                del self.buffer[:newline + 1]
                return line
            if len(self.buffer) > MAX_INPUT_BYTES:
                return bytes(self.buffer)
            chunk = os.read(self.descriptor, min(4096, MAX_INPUT_BYTES + 1 - len(self.buffer)))
            if not chunk:
                line = bytes(self.buffer)
                self.buffer.clear()
                return line
            self.buffer.extend(chunk)


@asynccontextmanager
async def bounded_stdio():
    incoming_send, incoming = anyio.create_memory_object_stream(0)
    outgoing, outgoing_receive = anyio.create_memory_object_stream(0)

    frame_reader = _FrameReader(sys.stdin.fileno())

    async def read():
        async with incoming_send:
            while True:
                raw = await _daemon_io(frame_reader.readline)
                if not raw:
                    break
                if len(raw) > MAX_INPUT_BYTES:
                    print("SORTH MCP: frame exceeds 128 KiB; connection closed.", file=sys.stderr)
                    break
                try:
                    message = parse_message(raw)
                except Exception:
                    await incoming_send.send(ValueError("Invalid JSON-RPC frame; use valid UTF-8 JSON, unique keys and nesting <=20."))
                    continue
                await incoming_send.send(SessionMessage(message))

    async def write():
        async with outgoing_receive:
            async for message in outgoing_receive:
                encoded = (message.message.model_dump_json(by_alias=True, exclude_none=True) + "\n").encode("utf-8")
                await _daemon_io(_write_all, sys.stdout.fileno(), encoded)

    async with anyio.create_task_group() as tasks:
        tasks.start_soon(read)
        tasks.start_soon(write)
        yield incoming, outgoing
