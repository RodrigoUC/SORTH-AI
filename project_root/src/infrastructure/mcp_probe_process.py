"""Bounded I/O and owned process cleanup for the fixed companion health probe.

No pipe reader thread holds a buffered-I/O lock during cancellation. Windows
uses a private kill-on-close job; POSIX uses only the probe's new process group.
Windows assignment occurs immediately after creation; descendants created
after assignment inherit its ownership. The verified --probe mode itself never
spawns descendants; this is lifecycle isolation, not a hostile-binary sandbox.
"""
import os
import signal


class WindowsProbeJob:
    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', ctypes.c_uint32), ('minimum_working_set', ctypes.c_size_t),
                        ('maximum_working_set', ctypes.c_size_t), ('active_processes', ctypes.c_uint32),
                        ('affinity', ctypes.c_size_t), ('priority', ctypes.c_uint32),
                        ('scheduling', ctypes.c_uint32)]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [('basic', BasicLimits), ('io_counters', ctypes.c_uint64 * 6),
                        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                        ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]

        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                     ctypes.c_void_p, wintypes.DWORD]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError('Probe job unavailable')
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise OSError('Probe job limits unavailable')

    def attach(self, process):
        # The exact handle belongs to the subprocess we just created. No PID
        # lookup, process-name enumeration, breakaway or unrelated process kill.
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise OSError('Probe process ownership unavailable')

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def read_available(stream, limit):
    """Read immediately available bytes only; b'' also means no data yet."""
    descriptor = stream.fileno()
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.PeekNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                     ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        api.PeekNamedPipe.restype = wintypes.BOOL
        available = wintypes.DWORD()
        if not api.PeekNamedPipe(msvcrt.get_osfhandle(descriptor), None, 0, None,
                                 ctypes.byref(available), None):
            if ctypes.get_last_error() in (109, 232):  # broken/closing pipe
                return b''
            raise OSError('Probe output unavailable')
        if not available.value:
            return b''
        return os.read(descriptor, min(limit, available.value))
    import select
    if select.select([descriptor], [], [], 0)[0]:
        return os.read(descriptor, limit)
    return b''


def stop_owned_process(process, job):
    if job is not None:
        job.close()
    elif os.name != 'nt':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=2)
