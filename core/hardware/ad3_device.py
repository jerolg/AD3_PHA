import ctypes
import numpy as np
import logging
from core.interfaces import IDevice
from core.models.data_models import AcquisitionConfig

class AD3Device(IDevice):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._hdwf = ctypes.c_int(0)
        self._config = AcquisitionConfig()
        try:
            self._dwf = ctypes.cdll.dwf
        except OSError:
            self._logger.error("dwf.dll no encontrada.")
            self._dwf = None

    def connect(self) -> bool:
        if not self._dwf: return False
        self._dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(self._hdwf))
        return self._hdwf.value != 0

    def disconnect(self) -> None:
        if self._hdwf.value != 0:
            self._dwf.FDwfAnalogInReset(self._hdwf)
            self._dwf.FDwfDeviceClose(self._hdwf)
            self._hdwf.value = 0

    def configure(self, config: AcquisitionConfig) -> None:
        self._config = config
        h = self._hdwf
        channel = ctypes.c_int(config.channel)
        
        # 1. Configuración Básica
        self._dwf.FDwfAnalogInFrequencySet(h, ctypes.c_double(config.sample_rate))
        self._dwf.FDwfAnalogInBufferSizeSet(h, ctypes.c_int(config.buffer_size))
        self._dwf.FDwfAnalogInChannelEnableSet(h, channel, ctypes.c_int(1))
        self._dwf.FDwfAnalogInChannelRangeSet(h, channel, ctypes.c_double(5.0))
        
        # ---> EL ERROR ESTABA AQUÍ: El modo Single en C++ es 0, no 1 <---
        self._dwf.FDwfAnalogInAcquisitionModeSet(h, ctypes.c_int(0))
        
        # 2. Centrar el pulso y esperar infinito
        self._dwf.FDwfAnalogInTriggerPositionSet(h, ctypes.c_double(0.0))
        self._dwf.FDwfAnalogInTriggerAutoTimeoutSet(h, ctypes.c_double(0.0))
        
        # 3. Activar Condiciones del Trigger
        if config.trigger_enabled:
            self._dwf.FDwfAnalogInTriggerSourceSet(h, ctypes.c_int(2)) # 2 = AnalogIn
            
            # ---> FALTA ESTO PARA QUE EL TRIGGER NO SE DISPARE CON RUIDO <---
            self._dwf.FDwfAnalogInTriggerTypeSet(h, ctypes.c_int(0)) # 0 = Edge (Cruce de línea)
            
            self._dwf.FDwfAnalogInTriggerChannelSet(h, channel)
            self._dwf.FDwfAnalogInTriggerConditionSet(h, ctypes.c_int(1)) # 1 = Falling Edge
            self._dwf.FDwfAnalogInTriggerLevelSet(h, ctypes.c_double(config.trigger_threshold))
        else:
            self._dwf.FDwfAnalogInTriggerSourceSet(h, ctypes.c_int(0)) # None

        # 4. Iniciar Hardware
        self._dwf.FDwfAnalogInConfigure(h, ctypes.c_int(1), ctypes.c_int(1))
        self._logger.info(f"AD3 Configurado. Threshold: {config.trigger_threshold}V")

    def poll_data(self) -> np.ndarray:
        if self._hdwf.value == 0: return np.array([])
        
        sts = ctypes.c_byte()
        self._dwf.FDwfAnalogInStatus(self._hdwf, ctypes.c_int(1), ctypes.byref(sts))
        
        if sts.value == 2:
            # Extraer datos
            samples = (ctypes.c_double * self._config.buffer_size)()
            self._dwf.FDwfAnalogInStatusData(
                self._hdwf, 
                ctypes.c_int(self._config.channel), 
                samples, 
                ctypes.c_int(self._config.buffer_size)
            )
            
            # Re-armar el trigger SIN borrar la configuración (0, 1 en vez de 1, 1)
            self._dwf.FDwfAnalogInConfigure(self._hdwf, ctypes.c_int(0), ctypes.c_int(1))
            
            return np.array(samples, dtype=np.float64)
            
        return np.array([])

    def is_connected(self) -> bool:
        return self._hdwf.value != 0
    
    def acquire_frame(self) -> np.ndarray:
        return self.poll_data()