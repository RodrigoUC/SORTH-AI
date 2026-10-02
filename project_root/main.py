"""Generate and export the included synthetic timetable from the command line."""
from pathlib import Path
from src.application.scheduling_service import SchedulingService
from src.infrastructure.schedule_exporter import ScheduleExporter
from src.scheduling.time_model import TimeModel


def main():
    root = Path(__file__).resolve().parent
    assignments, groups = SchedulingService(str(root / 'data/input/Cursos_Ejemplo.xlsx'), seed=42).run()
    if not assignments:
        raise SystemExit('No se pudo generar un horario.')
    output = root / 'data/output'
    output.mkdir(parents=True, exist_ok=True)
    exporter = ScheduleExporter(TimeModel.default())
    exporter.to_excel(assignments, str(output / 'horario_ejemplo.xlsx'), groups)
    exporter.to_csv(assignments, str(output / 'horario_ejemplo.csv'), groups)
    print(f'{len(assignments)}/{len(groups)} sesiones sintéticas exportadas a {output}')


if __name__ == '__main__':
    main()
