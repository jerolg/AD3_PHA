import h5py
import numpy as np
import logging
from typing import List
from core.models.data_models import PulseEvent

class HDF5Manager:
    """Manages secure saving of PHA data to disk."""

    def __init__(self, filename: str):
        self.filename = filename
        self._logger = logging.getLogger(__name__)

    def save_session(self, pulses: List[PulseEvent], spectrum: np.ndarray) -> None:
        try:
            with h5py.File(self.filename, 'w') as f:
                f.attrs['date'] = str(np.datetime64('now'))
                f.attrs['total_pulses'] = len(pulses)
                
                # Save the accumulated PHA spectrum
                f.create_dataset('spectrum_counts', data=spectrum, compression="gzip")
                
                # Save all detected amplitudes
                amplitudes = np.array([p.amplitude for p in pulses])
                f.create_dataset('amplitudes', data=amplitudes, compression="gzip")
                
            self._logger.info(f"Session saved successfully to {self.filename}")
        except Exception as e:
            self._logger.error(f"Failed to save HDF5: {e}")