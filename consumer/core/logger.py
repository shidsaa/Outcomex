import logging
import sys
from pythonjsonlogger import jsonlogger

def configure_logging(log_level=logging.INFO, log_file: str = None):
    log_handler = logging.FileHandler(log_file) if log_file else logging.StreamHandler(sys.stdout)

    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    log_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [log_handler]
