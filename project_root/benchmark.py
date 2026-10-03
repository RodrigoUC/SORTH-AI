"""Compatibility entrypoint; scheduler benchmarks live in tools/benchmark_scheduler.py."""
from tools.benchmark_scheduler import (
    DEFAULT_INPUT, benchmark_excel, main, run_once, validate_schedule,
)

__all__ = ["DEFAULT_INPUT", "benchmark_excel", "main", "run_once", "validate_schedule"]


if __name__ == "__main__":
    main()
