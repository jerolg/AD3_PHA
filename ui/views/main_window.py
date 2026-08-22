import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QLabel, QDoubleSpinBox, 
                             QGroupBox, QFileDialog, QMessageBox, QTextEdit,
                             QScrollArea)
from PyQt6.QtCore import pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QTextCursor, QPixmap
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
        self.setMinimumSize(900, 600) 

        self.qt_log_handler = qt_log_handler
        self.device = None
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_hardware)
        
        self.pha_builder = PHABuilder()
        self.view_model = PHAViewModel()
        self.pulses_history = []
        self.sample_rate = 100e6

        self._init_ui()
        self._connect_signals()
        
        self.qt_log_handler.message_logged.connect(self.append_log)
        logging.info("Application started. Ready.")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- CONTENEDOR SCROLL PARA EL PANEL IZQUIERDO ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        left_panel_widget = QWidget()
        ctrl_layout = QVBoxLayout(left_panel_widget)
        
        scroll_area.setWidget(left_panel_widget)
        main_layout.addWidget(scroll_area, 1)

        # ==========================================
        # FLAG / BADGE INDICADOR DE ESTADO
        # ==========================================
        self.lbl_status = QLabel()
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status_idle() # Llama al estado "Ready for Measuring"
        ctrl_layout.addWidget(self.lbl_status)
        # ==========================================

        cfg_group = QGroupBox("Hardware Configuration")
        cfg_form = QVBoxLayout()
        
        self.chan_combo = QComboBox()
        self.chan_combo.addItems(["Channel 1", "Channel 2"])
        cfg_form.addWidget(QLabel("Channel:"))
        cfg_form.addWidget(self.chan_combo)

        # TRIGGER THRESHOLD 
        self.thresh_spin = QDoubleSpinBox()
        self.thresh_spin.setRange(-5.0, 5.0) 
        self.thresh_spin.setValue(0.8)
        self.thresh_spin.setSingleStep(0.05)
        self.thresh_spin.setSuffix(" V")
        cfg_form.addWidget(QLabel("Trigger Threshold (Falling):"))
        cfg_form.addWidget(self.thresh_spin)

        # CONTROL DE AMPLITUD MÁXIMA PHA
        self.pha_max_spin = QDoubleSpinBox()
        self.pha_max_spin.setRange(0.5, 10.0) 
        self.pha_max_spin.setValue(5.0)       
        self.pha_max_spin.setSingleStep(0.5)
        self.pha_max_spin.setSuffix(" V")
        cfg_form.addWidget(QLabel("PHA Max Amplitude:"))
        cfg_form.addWidget(self.pha_max_spin)

        # BOTONES DE MODO (Con el color #27ae60 cuando están activos)
        check_btn_style = """
            QPushButton:checked {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
            }
        """

        self.sim_btn = QPushButton("Use Simulated Hardware")
        self.sim_btn.setCheckable(True)
        self.sim_btn.setStyleSheet(check_btn_style)
        cfg_form.addWidget(self.sim_btn)

        self.cont_mode_check = QPushButton("Continuous Mode (No Trigger)")
        self.cont_mode_check.setCheckable(True)
        self.cont_mode_check.setStyleSheet(check_btn_style)
        cfg_form.addWidget(self.cont_mode_check)
        
        cfg_group.setLayout(cfg_form)
        ctrl_layout.addWidget(cfg_group)

        stats_group = QGroupBox("PHA Statistics")
        stats_layout = QVBoxLayout()
        self.lbl_counts = QLabel("Counts: 0")
        self.lbl_cps = QLabel("Rate: 0.00 CPS")
        self.lbl_time = QLabel("Time: 0.0 s")
        for lbl in (self.lbl_counts, self.lbl_cps, self.lbl_time):
            lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #85A8D0;")
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

        # ==========================================
        # BRANDING: GICM - Universidad de Antioquia
        # ==========================================
        branding_layout = QVBoxLayout()
        
        self.logo_label = QLabel()
        pixmap = QPixmap("assets/logo_gicm.png") 
        
        if not pixmap.isNull():
            pixmap = pixmap.scaled(180, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("[Logo GICM No Encontrado]")
            
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        creditos_html = (
            "<div style='text-align: center; font-size: 12px; color: #555; margin-top: 10px;'>"
            "<b>Scientific Instrumentation and Microelectronics Group (GICM)</b><br>"
            "Universidad de Antioquia<br><br>"
            "<i>Developed by: Jerónimo López</i>"
            "</div>"
        )
        self.lbl_credits = QLabel(creditos_html)
        self.lbl_credits.setWordWrap(True)
        self.lbl_credits.setAlignment(Qt.AlignmentFlag.AlignCenter)

        branding_layout.addWidget(self.logo_label)
        branding_layout.addWidget(self.lbl_credits)
        ctrl_layout.addLayout(branding_layout)
        # ==========================================

        display_layout = QVBoxLayout()
        main_layout.addLayout(display_layout, 4)

        # OSCILLOSCOPE
        self.wave_plot = pg.PlotWidget(title="Oscilloscope (Live Signal)")
        self.wave_plot.setLabel('left', 'Voltage', 'V')
        self.wave_plot.setLabel('bottom', 'Time', 'µs') 
        self.wave_plot.showGrid(x=True, y=True)
        self.wave_curve = self.wave_plot.plot(pen=pg.mkPen('y', width=2))
        display_layout.addWidget(self.wave_plot, 2)

        # PHA HISTOGRAM
        self.pha_plot = pg.PlotWidget(title="PHA Spectrum")
        self.pha_plot.setLabel('left', 'Counts')
        self.pha_plot.setLabel('bottom', 'Channel') 
        self.pha_curve = self.pha_plot.plot(stepMode=True, fillLevel=0, fillOutline=True, brush=(52, 152, 219, 150))
        
        self.pha_plot.setXRange(0, self.pha_builder.channels, padding=0)
        self.pha_plot.setMouseEnabled(x=False, y=True)
        
        display_layout.addWidget(self.pha_plot, 2)

        # LOGS
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(130)
        self.log_viewer.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        display_layout.addWidget(self.log_viewer, 1)

    # ==========================================
    # MÉTODOS DE LA FLAG/BADGE
    # ==========================================
    def set_status_idle(self):
        self.lbl_status.setText("Ready for Measuring")
        self.lbl_status.setStyleSheet("""
            background-color:  #27ae60; color: white; font-weight: bold; 
            font-size: 14px; padding: 8px; border-radius: 5px;
        """)

    def set_status_measuring(self):
        self.lbl_status.setText("Measuring in Progress")
        self.lbl_status.setStyleSheet("""
            background-color: #c0392b; color: white; font-weight: bold; 
            font-size: 14px; padding: 8px; border-radius: 5px;
        """)

    def _connect_signals(self):
        self.btn_start.clicked.connect(self.start_acquisition)
        self.btn_stop.clicked.connect(self.stop_acquisition)
        self.btn_reset.clicked.connect(self.reset_data)
        self.btn_save.clicked.connect(self.save_data)
        self.view_model.stats_updated.connect(self.update_stats_ui)
        self.pha_max_spin.valueChanged.connect(self.update_pha_range)
        
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
        
        self.device.configure(config)
        self.timer.start(20)
        self.view_model.reset()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.sim_btn.setEnabled(False)
        self.cont_mode_check.setEnabled(False)
        self.pha_max_spin.setEnabled(False)
        
        # Cambiar el flag a modo medición
        self.set_status_measuring()

    @pyqtSlot()
    def stop_acquisition(self):
        self.timer.stop() 
        
        if self.device:
            self.device.disconnect()
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.sim_btn.setEnabled(True)
        self.cont_mode_check.setEnabled(True)
        self.pha_max_spin.setEnabled(True)
        
        # Volver el flag a estado inicial
        self.set_status_idle()
        logging.info("Acquisition stopped.")

    @pyqtSlot()
    def poll_hardware(self):
        if not self.device: return
        
        raw_data = self.device.poll_data()
        
        if raw_data.size > 0:
            pulse = DSPEngine.process_buffer(raw_data, self.sample_rate)
            if pulse:
                self.handle_pulse(pulse)

    def handle_pulse(self, pulse):
        n = len(pulse.raw_data)
        if n == 0: return

        # 1. GRAPH WAVEFORM IN MICROSECONDS
        fs = self.sample_rate
        total_time_us = (n / fs) * 1e6
        time_axis = np.linspace(-total_time_us/2, total_time_us/2, n)

        self.wave_curve.setData(time_axis, pulse.raw_data)

        if self.cont_mode_check.isChecked():
            self.wave_plot.enableAutoRange(axis='y')

        # 2. UPDATE PHA 
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
        
    @pyqtSlot(float)
    def update_pha_range(self, new_max: float):
        self.pha_builder.set_max_amplitude(new_max)
        self.pulses_history.clear()
        self.view_model.reset()
        
        edges, counts = self.pha_builder.get_histogram_data()
        self.pha_curve.setData(edges, counts)
        self.pha_plot.setXRange(0, self.pha_builder.channels, padding=0)
        logging.info(f"PHA Range set to: {new_max} V. Spectrum cleared.")

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