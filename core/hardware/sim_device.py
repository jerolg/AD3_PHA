import numpy as np
import time
from core.interfaces import IDevice
from core.models.data_models import AcquisitionConfig

class SimulatedDevice(IDevice):
    """Generates synthetic biexponential pulses."""

    def __init__(self):
        self._config = AcquisitionConfig()
        self._connected = False
        self._last_trigger_time = time.time()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def configure(self, config: AcquisitionConfig) -> None:
        self._config = config

    def acquire_frame(self) -> np.ndarray:
        # Rate limit to simulate hardware processing time
        time.sleep(0.05) 
        
        size = self._config.buffer_size
        fs = self._config.sample_rate
        
        # Noise floor (Baseline ~1.0V)
        data = np.ones(size) + np.random.normal(0, 0.005, size)
        
        # Simulate trigger rate (e.g., 2 CPS)
        current_time = time.time()
        if self._config.trigger_enabled:
            if current_time - self._last_trigger_time < 0.5:
                return np.array([]) # Return empty if no trigger occurred
                
        self._last_trigger_time = current_time

        # Inject pulse
        amplitude = np.random.choice([0.3, 0.6]) + np.random.normal(0, 0.02)
        
        # Time axis
        t = np.linspace(0, size/fs, size)
        t_start = t[size // 2] # Center of the buffer
        
        tau_rise = 0.1e-6
        tau_fall = 0.5e-6
        
        pulse_mask = t > t_start
        tp = t[pulse_mask] - t_start
        
        pulse_shape = (np.exp(-tp/tau_fall) - np.exp(-tp/tau_rise))
        pulse_shape = pulse_shape / np.max(pulse_shape) * amplitude
        
        data[pulse_mask] -= pulse_shape # Negative going pulse
        
        return data

    def is_connected(self) -> bool:
        return self._connected