"""Disposable, SDK-free subprocess for a single bounded deterministic preview."""
import base64
import json
import sys

from ..application.preview_contract import MAX_INPUT_BYTES, MAX_OUTPUT_BYTES, ContractError
from ..application.schedule_preview import domain_input, generate_preview


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ContractError("INPUT_LIMIT", "request", "Reduce the request size.")
        request = json.loads(raw)
        export = isinstance(request, dict) and request.get('operation') == 'excel'
        if export:
            from .artifacts import MAX_EXPORT_OUTPUT_BYTES, MAX_XLSX_BYTES
            from ..infrastructure.schedule_exporter import ExcelExportLimitError, ScheduleExporter
            from ..scheduling.time_model import TimeModel
            if set(request) != {'operation', 'request'}:
                raise ContractError('UNSUPPORTED_FIELD', 'request', 'Invalid worker operation.')
            preview = generate_preview(request['request'])
            courses, _, _ = domain_input(preview['normalized'])
            groups = [group for course in courses for group in course.generate_groups()]
            assignments = {row['group_id']: (row['classroom'], row['day'], row['start_min'], row['end_min'])
                           for row in preview['assignments']}
            try:
                data = ScheduleExporter(TimeModel.default()).to_excel_bytes(
                    assignments, groups=groups, pending=preview['pending'], status=preview['status'],
                    max_output_bytes=MAX_XLSX_BYTES,
                    notes=[notice["message"] for notice in preview["notices"]])
            except ExcelExportLimitError:
                raise ContractError('OUTPUT_LIMIT', 'result', 'Excel exceeds 512 KiB; reduce the request and retry.') from None
            result = {'result': {'preview': preview, 'xlsx': base64.b64encode(data).decode('ascii')}}
            limit = MAX_EXPORT_OUTPUT_BYTES
        else:
            result = {"result": generate_preview(request)}
            limit = MAX_OUTPUT_BYTES
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode("utf-8")) > limit:
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
