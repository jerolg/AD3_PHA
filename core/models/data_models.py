from dataclasses import dataclass, field
import numpy as np

@dataclass(frozen=True)
class AcquisitionConfig:
    """Configuration passed to the Hardware Abstraction Layer."""
    channel: int = 0
    sample_rate: float = 100e6
    buffer_size: int = 8192
    trigger_threshold: float = 0.8
    trigger_enabled: bool = True

@dataclass
class PulseEvent:
    """Represents a single data buffer captured by the hardware."""
    timestamp: float
    amplitude: float
    baseline: float
    raw_data: np.ndarray = field(repr=False)

@dataclass
class PHAStats:
    """Statistics for the current acquisition session."""
    total_counts: int = 0
    elapsed_time: float = 0.0
    cps: float = 0.0
    peak_amplitude: float = 0.0