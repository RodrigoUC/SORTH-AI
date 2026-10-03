"""Background scheduling adapter; UI state stays in the main thread."""
from copy import deepcopy
from PyQt6.QtCore import QThread, pyqtSignal
from ..application.scheduling_service import SchedulingService

class SchedulerWorker(QThread):
    result_ready = pyqtSignal(object, object)   # assignments, groups
    error    = pyqtSignal(str)

    def __init__(self, excel_path, courses, classrooms, restrictions, seed, pinned_assignments=None, lab_overrides=()):
        super().__init__()
        self._excel_path   = excel_path
        self._courses      = deepcopy(courses)
        self._classrooms   = deepcopy(classrooms)
        self._restrictions = deepcopy(restrictions)
        self._seed         = seed
        self._pinned_assignments = deepcopy(pinned_assignments or {})
        self._lab_overrides = frozenset(lab_overrides)

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            service = SchedulingService(self._excel_path, seed=self._seed)
            assignments, groups = service.run(
                courses=self._courses,
                classroom_restrictions=self._restrictions or None,
                classrooms=self._classrooms or None,
                pinned_assignments=self._pinned_assignments,
                lab_overrides=self._lab_overrides,
            )
            if not self.isInterruptionRequested():
                self.result_ready.emit(assignments, groups)
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))
