import logging
import os

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_configured = False


def _configure_root():
    """Configure logging once for the whole app (console, plus optional file)."""
    global _configured
    if _configured:
        return
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handlers = [logging.StreamHandler()]
    log_file = os.environ.get("LOG_FILE")
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=level, format=_LOG_FORMAT, handlers=handlers)
    _configured = True


def getMyLogger(name):
    _configure_root()
    return logging.getLogger(name)
