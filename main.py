import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.views.main_window import MainWindow
from utils.logger_setup import setup_logging

def global_exception_hook(exctype, value, traceback):
    """Catches unhandled Python crashes and logs them properly."""
    logging.critical("CRITICAL UNHANDLED EXCEPTION", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)

def main():
    # 1. Initialize logging system
    qt_log_handler = setup_logging()
    
    # 2. Install crash hook
    sys.excepthook = global_exception_hook
    
    # 3. Prevent DPI scaling issues on Windows 11 high-res screens
    import os
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # 4. Boot Application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow(qt_log_handler)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()