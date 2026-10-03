"""Excel composition shared by the GUI, CLI and historical path-based API."""
from ..application.scheduling_ports import SchedulingInputReader


def create_excel_reader(excel_path: str | None) -> SchedulingInputReader:
    # Importing a composition root must not load Excel libraries. The caller
    # chooses this adapter only when generation really needs missing input.
    from ..infrastructure.excel_reader import ExcelReader

    return ExcelReader(excel_path)
