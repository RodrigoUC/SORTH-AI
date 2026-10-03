"""Disposable, SDK-free subprocess for a single bounded deterministic preview."""
import json
import sys

from ..application.preview_contract import MAX_INPUT_BYTES, MAX_OUTPUT_BYTES, ContractError
from ..application.schedule_preview import generate_preview


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ContractError("INPUT_LIMIT", "request", "Reduce the request size.")
        result = {"result": generate_preview(json.loads(raw))}
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ContractError("OUTPUT_LIMIT", "result", "Reduce courses or groups; the full response is too large.")
    except ContractError as exc:
        encoded = json.dumps({"error": exc.as_dict()})
    except Exception:
        # No data, stack traces, filesystem locations or exception text on wire.
        encoded = json.dumps({"error": {"code": "GENERATION_FAILED", "path": "result",
                                      "message": "Preview failed safely; no state was saved."}})
    sys.stdout.write(encoded)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
