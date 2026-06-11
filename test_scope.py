import ctypes
import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# 1. Cargar DLL
try:
    dwf = ctypes.cdll.dwf
except OSError:
    print("Error: dwf.dll no encontrada.")
    sys.exit()

hdwf = ctypes.c_int()
sts = ctypes.c_byte()

# 2. Conectar al AD3
print("Conectando al AD3...")
dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(hdwf))

if hdwf.value == 0:
    print("Error: No se pudo conectar al AD3.")
    sys.exit()

print("¡AD3 Conectado!")

# 3. Configuración OFICIAL de Digilent (Sin tocar triggers ni estados avanzados)
buffer_size = 8192
print("Configurando Osciloscopio (CH1)...")
dwf.FDwfAnalogInFrequencySet(hdwf, ctypes.c_double(100e6)) # 100 MHz
dwf.FDwfAnalogInBufferSizeSet(hdwf, ctypes.c_int(buffer_size))
dwf.FDwfAnalogInChannelEnableSet(hdwf, ctypes.c_int(0), ctypes.c_int(1)) # CH1 On
dwf.FDwfAnalogInChannelRangeSet(hdwf, ctypes.c_int(0), ctypes.c_double(5.0)) # 5V

# Iniciar la primera captura (fReconfigure=1, fStart=1)
dwf.FDwfAnalogInConfigure(hdwf, ctypes.c_int(1), ctypes.c_int(1))

# 4. Configurar Interfaz Gráfica (PyQtGraph)
app = QApplication(sys.argv)
win = pg.PlotWidget(title="Osciloscopio Simple (Ejemplo Digilent)")
win.setYRange(-3, 3)
win.setLabel('left', 'Voltage', 'V')
win.setLabel('bottom', 'Samples')
win.showGrid(x=True, y=True)

curve = win.plot(pen=pg.mkPen('y', width=2))
win.resize(800, 600)
win.show()

# 5. Función de actualización (No bloqueante)
def update_plot():
    # Preguntar estado a la tarjeta
    dwf.FDwfAnalogInStatus(hdwf, ctypes.c_int(1), ctypes.byref(sts))
    
    if sts.value == 2: # Estado 2 = Done (¡Captura terminada!)
        # Leer los datos de la memoria
        samples = (ctypes.c_double * buffer_size)()
        dwf.FDwfAnalogInStatusData(hdwf, ctypes.c_int(0), samples, ctypes.c_int(buffer_size))
        
        # Graficar
        data = np.array(samples, dtype=np.float64)
        curve.setData(data)
        print(f"Frame graficado. Voltaje Medio: {np.mean(data):.3f} V")
        
        # Volver a pedir otra captura
        dwf.FDwfAnalogInConfigure(hdwf, ctypes.c_int(1), ctypes.c_int(1))
        
    elif sts.value == 3:
        # Solo imprimimos esto si realmente se atasca
        print("AD3 está llenando el buffer (Prefill)...")

# Llamar a update_plot cada 20 milisegundos
timer = QTimer()
timer.timeout.connect(update_plot)
timer.start(20)

# 6. Mantener abierta la ventana y cerrar seguro
try:
    sys.exit(app.exec())
finally:
    print("Cerrando dispositivo AD3...")
    dwf.FDwfDeviceCloseAll()