"""
Performance Measurement Helpers

Utilities for measuring and validating performance in E2E tests.
"""

import time
from contextlib import contextmanager


class PerformanceMonitor:
    """Monitor and validate performance metrics."""

    def __init__(self):
        self.measurements = {}

    @contextmanager
    def measure(self, operation_name: str):
        """
        Context manager to measure operation duration.

        Usage:
            with performance_monitor.measure("checkout"):
                # perform checkout operation
                pass
            duration_ms = performance_monitor.get_duration("checkout")
        """
        start_time = time.time()
        yield
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        self.measurements[operation_name] = duration_ms

    def get_duration(self, operation_name: str) -> float:
        """Get duration in milliseconds for an operation."""
        return self.measurements.get(operation_name, 0.0)

    def assert_faster_than(self, operation_name: str, max_ms: float):
        """
        Assert that an operation completed within threshold.

        Args:
            operation_name: Name of the measured operation
            max_ms: Maximum allowed duration in milliseconds

        Raises:
            AssertionError: If operation exceeded threshold
        """
        duration = self.get_duration(operation_name)
        assert duration <= max_ms, \
            f"{operation_name} took {duration:.2f}ms, expected <{max_ms}ms"

    def print_summary(self):
        """Print summary of all measurements."""
        print("\n⏱️  Performance Summary:")
        for operation, duration in self.measurements.items():
            print(f"  {operation}: {duration:.2f}ms")
