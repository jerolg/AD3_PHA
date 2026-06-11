from PyQt6.QtCore import QObject, pyqtSignal
import time
from core.models.data_models import PHAStats, PulseEvent

class PHAViewModel(QObject):
    """Calculates live statistics (CPS, Elapsed Time, etc.) for the UI."""
    stats_updated = pyqtSignal(PHAStats)

    def __init__(self):
        super().__init__()
        self.start_time = 0.0
        self.count = 0
        self.max_amp = 0.0

    def reset(self) -> None:
        self.start_time = time.time()
        self.count = 0
        self.max_amp = 0.0
        self._emit_stats()

    def process_new_pulse(self, pulse: PulseEvent) -> None:
        self.count += 1
        if pulse.amplitude > self.max_amp:
            self.max_amp = pulse.amplitude
        self._emit_stats()

    def _emit_stats(self) -> None:
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0.0
        cps = self.count / elapsed if elapsed > 0 else 0.0
        
        stats = PHAStats(
            total_counts=self.count,
            elapsed_time=elapsed,
            cps=cps,
            peak_amplitude=self.max_amp
        )
        self.stats_updated.emit(stats)