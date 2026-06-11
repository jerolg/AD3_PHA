import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QLabel, QDoubleSpinBox, 
                             QGroupBox, QFileDialog, QMessageBox, QTextEdit)
from PyQt6.QtCore import pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QTextCursor
import pyqtgraph as pg
import numpy as np

from core.hardware.ad3_device import AD3Device
from core.hardware.sim_device import SimulatedDevice
from core.models.data_models import AcquisitionConfig
from core.processing.dsp_engine import DSPEngine
from core.processing.pha_builder import PHABuilder
from core.storage.hdf5_manager import HDF5Manager
from ui.viewmodels.pha_viewmodel import PHAViewModel

class MainWindow(QMainWindow):
    def __init__(self, qt_log_handler):
        super().__init__()
        self.setWindowTitle("Nuclear PHA - Analog Discovery 3")
        self.resize(1300, 900)

        self.qt_log_handler = qt_log_handler
        self.device = None
        
        # --- HERE IS THE MAGIC: THE TIMER ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_hardware)
        
        self.pha_builder = PHABuilder()
        self.view_model = PHAViewModel()
        self.pulses_history = []
        self.sample_rate = 100e6

        self._init_ui()
        self._connect_signals()
        
        self.qt_log_handler.message_logged.connect(self.append_log)
        logging.info("Application started. Worker removed, using QTimer.")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        ctrl_layout = QVBoxLayout()
        main_layout.addLayout(ctrl_layout, 1)

        cfg_group = QGroupBox("Hardware Configuration")
        cfg_form = QVBoxLayout()
        
        self.chan_combo = QComboBox()
        self.chan_combo.addItems(["Channel 1", "Channel 2"])
        cfg_form.addWidget(QLabel("Channel:"))
        cfg_form.addWidget(self.chan_combo)

        self.thresh_spin = QDoubleSpinBox()
        self.thresh_spin.setRange(0, 4.0)
        self.thresh_spin.setValue(0.8)
        self.thresh_spin.setSingleStep(0.05)
        self.thresh_spin.setSuffix(" V")
        cfg_form.addWidget(QLabel("Trigger Threshold (Falling):"))
        cfg_form.addWidget(self.thresh_spin)

        self.sim_btn = QPushButton("Use Simulated Hardware")
        self.sim_btn.setCheckable(True)
        cfg_form.addWidget(self.sim_btn)

        self.cont_mode_check = QPushButton("Continuous Mode (No Trigger)")
        self.cont_mode_check.setCheckable(True)
        cfg_form.addWidget(self.cont_mode_check)
        
        cfg_group.setLayout(cfg_form)
        ctrl_layout.addWidget(cfg_group)

        stats_group = QGroupBox("PHA Statistics")
        stats_layout = QVBoxLayout()
        self.lbl_counts = QLabel("Counts: 0")
        self.lbl_cps = QLabel("Rate: 0.00 CPS")
        self.lbl_time = QLabel("Time: 0.0 s")
        for lbl in (self.lbl_counts, self.lbl_cps, self.lbl_time):
            lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
            stats_layout.addWidget(lbl)
        stats_group.setLayout(stats_layout)
        ctrl_layout.addWidget(stats_group)

        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setMinimumHeight(45)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")

        self.btn_reset = QPushButton("Clear Spectrum")
        self.btn_save = QPushButton("Save HDF5")
        
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addWidget(self.btn_reset)
        ctrl_layout.addWidget(self.btn_save)
        ctrl_layout.addStretch()

        display_layout = QVBoxLayout()
        main_layout.addLayout(display_layout, 4)

        # OSCILLOSCOPE
        self.wave_plot = pg.PlotWidget(title="Oscilloscope (Live Signal)")
        self.wave_plot.setLabel('left', 'Voltage', 'V')
        self.wave_plot.setLabel('bottom', 'Samples') 
        self.wave_plot.showGrid(x=True, y=True)
        self.wave_curve = self.wave_plot.plot(pen=pg.mkPen('y', width=2))
        display_layout.addWidget(self.wave_plot, 2)

        # PHA HISTOGRAM
        self.pha_plot = pg.PlotWidget(title="PHA Spectrum")
        self.pha_plot.setLabel('left', 'Counts')
        self.pha_plot.setLabel('bottom', 'Amplitude', 'V')
        self.pha_curve = self.pha_plot.plot(stepMode=True, fillLevel=0, fillOutline=True, brush=(52, 152, 219, 150))
        display_layout.addWidget(self.pha_plot, 2)

        # LOGS
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(130)
        self.log_viewer.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        display_layout.addWidget(self.log_viewer, 1)

    def _connect_signals(self):
        self.btn_start.clicked.connect(self.start_acquisition)
        self.btn_stop.clicked.connect(self.stop_acquisition)
        self.btn_reset.clicked.connect(self.reset_data)
        self.btn_save.clicked.connect(self.save_data)
        self.view_model.stats_updated.connect(self.update_stats_ui)

    @pyqtSlot()
    def start_acquisition(self):
        if self.sim_btn.isChecked():
            self.device = SimulatedDevice()
        else:
            self.device = AD3Device()

        if not self.device.connect():
            QMessageBox.critical(self, "Error", "Hardware not connected.")
            return

        config = AcquisitionConfig(
            channel=self.chan_combo.currentIndex(),
            trigger_threshold=self.thresh_spin.value(),
            trigger_enabled=not self.cont_mode_check.isChecked()
        )
        self.sample_rate = config.sample_rate
        
        # Configure Hardware (Starts automatically)
        self.device.configure(config)
        
        # Start QTimer (Poll every 20 ms)
        self.timer.start(20)
        self.view_model.reset()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.sim_btn.setEnabled(False)
        self.cont_mode_check.setEnabled(False)

    @pyqtSlot()
    def stop_acquisition(self):
        self.timer.stop() # Stop polling
        
        if self.device:
            self.device.disconnect()
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.sim_btn.setEnabled(True)
        self.cont_mode_check.setEnabled(True)
        logging.info("Acquisition stopped.")

    @pyqtSlot()
    def poll_hardware(self):
        """Called by QTimer every 20ms to check for data."""
        if not self.device: return
        
        # poll_data() returns [] if the card is still waiting for a pulse
        raw_data = self.device.poll_data()
        
        if raw_data.size > 0:
            # Process the signal
            pulse = DSPEngine.process_buffer(raw_data, self.sample_rate)
            if pulse:
                self.handle_pulse(pulse)

    def handle_pulse(self, pulse):
        # 1. PLOT WAVEFORM ALWAYS
        x_axis = np.arange(len(pulse.raw_data))
        self.wave_curve.setData(x_axis, pulse.raw_data)

        # Auto-center Y if in Continuous Mode
        if self.cont_mode_check.isChecked():
            self.wave_plot.enableAutoRange(axis='y')

        # 2. UPDATE PHA (Only pulses > 50mV)
        if pulse.amplitude > 0.05:
            self.pha_builder.add_pulse(pulse.amplitude)
            self.view_model.process_new_pulse(pulse)
            self.pulses_history.append(pulse)

            edges, counts = self.pha_builder.get_histogram_data()
            self.pha_curve.setData(edges, counts)

    @pyqtSlot(object)
    def update_stats_ui(self, stats):
        self.lbl_counts.setText(f"Counts: {stats.total_counts}")
        self.lbl_cps.setText(f"Rate: {stats.cps:.2f} CPS")
        self.lbl_time.setText(f"Time: {stats.elapsed_time:.1f} s")

    @pyqtSlot()
    def reset_data(self):
        self.pha_builder.reset()
        self.pulses_history.clear()
        self.view_model.reset()
        self.pha_curve.setData([], [])
        self.wave_curve.setData([], [])

    @pyqtSlot()
    def save_data(self):
        if not self.pulses_history: return
        path, _ = QFileDialog.getSaveFileName(self, "Save", "", "HDF5 Files (*.h5)")
        if path:
            _, counts = self.pha_builder.get_histogram_data()
            manager = HDF5Manager(path)
            manager.save_session(self.pulses_history, counts)

    @pyqtSlot(str, int)
    def append_log(self, message: str, level: int):
        color = "#ffffff"
        if level >= logging.ERROR: color = "#ff5555"
        elif level >= logging.WARNING: color = "#ffb86c"
        elif level >= logging.INFO: color = "#50fa7b"
        self.log_viewer.moveCursor(QTextCursor.MoveOperation.End)
        self.log_viewer.append(f'<span style="color:{color};">{message}</span>')
        self.log_viewer.moveCursor(QTextCursor.MoveOperation.End)