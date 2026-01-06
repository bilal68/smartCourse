import logging
import sys
from typing import Optional

import structlog


def configure_logging(level: int = logging.INFO) -> None:
    """Configure stdlib logging and structlog to emit JSON to stdout.

    Call this early in each process (FastAPI, Celery worker, consumer) so
    all logs (stdlib and structlog) are formatted consistently.
    """

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    processor_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[timestamper, structlog.stdlib.add_log_level],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(processor_formatter)

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(handler)
    root.setLevel(level)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None):
    """Return a structlog logger for the given name.

    Use this in modules: `logger = get_logger(__name__)`.
    """
    return structlog.get_logger(name)
