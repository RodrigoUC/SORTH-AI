"""Background scheduling adapter; UI state stays in the main thread."""
from copy import deepcopy
from PyQt6.QtCore import QThread, pyqtSignal
from ..application.scheduling_service import SchedulingService
from ..bootstrap.scheduling import create_excel_reader
from ..scheduling.cancellation import SchedulingCancelled, checkpoint

class SchedulerWorker(QThread):
    result_ready = pyqtSignal(object, object)   # assignments, groups
    error    = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, excel_path, courses, classrooms, restrictions, seed, pinned_assignments=None, lab_overrides=(), resources=None, calendar=None):
        super().__init__()
        self._resources = deepcopy(resources)
        self._excel_path   = excel_path
        self._courses      = deepcopy(courses)
        self._classrooms   = deepcopy(classrooms)
        self._restrictions = deepcopy(restrictions)
        self._seed         = seed
        self._calendar = calendar
        self._pinned_assignments = deepcopy(pinned_assignments or {})
        self._lab_overrides = frozenset(lab_overrides)

    def run(self):
        try:
            checkpoint(self.isInterruptionRequested)
            service = SchedulingService(self._excel_path, seed=self._seed,
                                        reader_factory=create_excel_reader)
            assignments, groups = service.run(
                courses=self._courses,
                resources=self._resources,
                classroom_restrictions=self._restrictions or None,
                classrooms=self._classrooms or None,
                pinned_assignments=self._pinned_assignments,
                lab_overrides=self._lab_overrides,
                calendar=self._calendar,
                cancelled=self.isInterruptionRequested,
            )
            # Candidate domains are worker-owned search scratch space, not
            # accepted session data. Retaining them also retains solver rooms
            # and makes later GUI rollback snapshots copy the entire search.
            # Placement suggestions build a fresh domain from accepted inputs.
            for group in groups:
                checkpoint(self.isInterruptionRequested)
                group.domain = []
            checkpoint(self.isInterruptionRequested)
            self.result_ready.emit(assignments, groups)
        except SchedulingCancelled:
            self.cancelled.emit()
        except Exception as e:
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.error.emit(str(e))
