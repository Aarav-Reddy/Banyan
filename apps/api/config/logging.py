"""Operational JSON logs deliberately exclude raw messages, URLs, prompts and tracebacks."""

import json
import logging


class MetadataFormatter(logging.Formatter):
    def format(self, record):
        result = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.msg
            if isinstance(record.msg, str)
            and record.msg in {"request_completed", "job_completed", "job_failed"}
            else "operational_event",
        }
        for key in ("request_id", "job_id", "workspace_id", "status", "error_code", "method"):
            if hasattr(record, key):
                result[key] = str(getattr(record, key))[:100]
        return json.dumps(result, sort_keys=True)
