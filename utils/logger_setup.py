import logging
import sys
from PyQt6.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    """Custom logging handler that emits a Qt signal for UI updates."""
    message_logged = pyqtSignal(str, int)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.message_logged.emit(msg, record.levelno)

def setup_logging(level: int = logging.INFO) -> QtLogHandler:
    """Sets up console, file, and UI logging."""
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File
    file_handler = logging.FileHandler('pha_system.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # UI Handler
    qt_handler = QtLogHandler()
    qt_handler.setFormatter(formatter)
    logger.addHandler(qt_handler)

    return qt_handler