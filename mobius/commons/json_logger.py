import json
import logging
from datetime import datetime


log_levels = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.NOTSET: "NOTICE",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
    logging.FATAL: "EMERGENCY",
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()

        # noinspection PyTypeChecker
        raw = {
            "timestamp": str(datetime.utcnow()),
            "severity": log_levels.get(record.levelno),
            "msg": message,
        }

        if record.exc_info:
            raw["trace"] = self.formatException(record.exc_info).splitlines()

        attrs = record.__dict__

        details = getattr(record, "details", None)
        if details is not None:
            # noinspection PyTypeChecker
            raw.update(details)

        raw.update(
            {
                "thread": f"{attrs.get('threadName')}:{attrs.get('thread')}",
                "module": f"{attrs.get('module')}:{attrs.get('funcName')}:{attrs.get('lineno')}",
            }
        )

        return json.dumps(raw)
