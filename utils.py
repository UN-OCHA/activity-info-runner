import logging
from typing import Dict, Any


def build_nested_dict(flat: Dict[str, Any]) -> Dict:
    """Converts a flat dictionary with dot-separated keys into a nested dictionary."""
    nested: Dict = {}
    for key, value in flat.items():
        parts = key.split(".")
        d = nested
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return nested


class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        try:
            self.records.append(self.format(record))
        except Exception:
            self.handleError(record)


class CaptureLogs:
    def __init__(self, logger_name=None):
        self.logger_name = logger_name
        self.handler = MemoryLogHandler()
        self.handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
        self.logger = logging.getLogger(self.logger_name)
        self.old_level = logging.NOTSET

    def __enter__(self):
        self.logger.addHandler(self.handler)
        self.old_level = self.logger.level
        self.logger.setLevel(logging.INFO)
        return self.handler

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.old_level)
