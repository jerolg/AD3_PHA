import numpy as np
from typing import Tuple

class PHABuilder:
    """Aggregates pulse amplitudes into an energy spectrum histogram."""

    def __init__(self, channels: int = 1024, max_val: float = 1.2):
        self.channels = channels
        self.max_val = max_val
        # Bins array is length (channels + 1)
        self.bins = np.linspace(0, max_val, channels + 1)
        # Counts array is length (channels)
        self.counts = np.zeros(channels, dtype=np.uint64)

    def add_pulse(self, amplitude: float) -> None:
        """Adds a single amplitude to the correct histogram bin."""
        if 0 <= amplitude < self.max_val:
            idx = int((amplitude / self.max_val) * self.channels)
            if idx < self.channels:
                self.counts[idx] += 1

    def get_histogram_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (edges, counts) safely formatted for pyqtgraph StepMode."""
        return self.bins, self.counts

    def reset(self) -> None:
        """Clears the histogram."""
        self.counts.fill(0)