import numpy as np
from typing import Optional
from core.models.data_models import PulseEvent

class DSPEngine:
    @staticmethod
    def process_buffer(data: np.ndarray, sample_rate: float) -> Optional[PulseEvent]:
        if data.size == 0: return None
        
        # Como no forzamos el centrado, el pulso suele estar al principio o donde el hardware decida.
        # Calculamos la línea base basándonos en el promedio general para evitar errores.
        baseline = np.mean(data)
        
        # Como los pulsos son negativos, el pico de amplitud es la diferencia hacia abajo
        min_val = np.min(data)
        amplitude = baseline - min_val
        
        # SIEMPRE retornamos el evento. La UI decidirá si es ruido o un pulso válido.
        return PulseEvent(
            timestamp=0.0,
            amplitude=amplitude,
            baseline=baseline,
            raw_data=data
        )