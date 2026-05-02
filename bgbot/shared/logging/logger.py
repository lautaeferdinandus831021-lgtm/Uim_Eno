import logging
import sys
from datetime import datetime
from pathlib import Path


class PlainFormatter(logging.Formatter):
    def format(self, record):
        ts = datetime.now().strftime("%H:%M:%S")
        svc = getattr(record, "service", "app")
        return f"{ts} [{record.levelname}] [{svc}] {record.getMessage()}"


def setup_logging(service_name="bgbot", level=logging.INFO):
    Path("logs").mkdir(exist_ok=True)
    fmt = PlainFormatter()
    fh = logging.FileHandler(f"logs/{service_name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(ch)


def get_logger(name, service="bgbot"):
    return logging.getLogger(name)
