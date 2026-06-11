from abc import ABC, abstractmethod
import numpy as np
from core.models.data_models import AcquisitionConfig

class IDevice(ABC):
    """Abstract interface for data acquisition hardware."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the hardware."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely closes the connection to the hardware."""
        pass

    @abstractmethod
    def configure(self, config: AcquisitionConfig) -> None:
        """Applies acquisition settings to the hardware."""
        pass

    @abstractmethod
    def acquire_frame(self) -> np.ndarray:
        """Blocks until a frame is acquired, then returns a deep copy of the data."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the hardware handle is valid."""
        pass