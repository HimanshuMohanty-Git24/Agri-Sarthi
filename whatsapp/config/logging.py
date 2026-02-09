import logging
import os
from logging.handlers import RotatingFileHandler

logs_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(logs_dir, exist_ok=True)


def setup_logger(name="whatsapp"):
    """Configure and return a logger with file + console handlers."""
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.INFO)

    if not _logger.handlers:
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")

        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, f"{name}.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        _logger.addHandler(file_handler)
        _logger.addHandler(console_handler)

    return _logger


logger = setup_logger()
