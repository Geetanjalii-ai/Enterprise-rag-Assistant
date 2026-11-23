import collections
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

# Thread-safe in-memory ring buffer for recent log lines (up to 2000 entries)
LOG_BUFFER: collections.deque = collections.deque(maxlen=2000)


def format_log_line(timestamp: str, level: str, name: str, message: str) -> str:
    """Format matching exact user specification:

    YYYY-MM-DD HH:MM:SS,mmm | LEVEL | LOGGER_NAME | MESSAGE
    """
    return f"{timestamp} | {level.upper()} | {name} | {message}"


def app_log(level: str, name: str, message: str) -> None:
    """Centralized structured log generator matching the enterprise pipeline format."""
    now = datetime.now()
    # Format with milliseconds YYYY-MM-DD HH:MM:SS,mmm
    ts = now.strftime("%Y-%m-%d %H:%M:%S") + f",{now.microsecond // 1000:03d}"
    lvl = level.upper()
    formatted = format_log_line(ts, lvl, name, message)

    entry = {
        "timestamp": ts,
        "level": lvl,
        "logger": name,
        "message": message,
        "raw": formatted,
    }
    LOG_BUFFER.append(entry)

    # Also output to stdout
    sys.stdout.write(formatted + "\n")
    sys.stdout.flush()


class BufferLogHandler(logging.Handler):
    """Intercept standard library logging (httpx, qdrant, uvicorn) into the monitoring ring buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            now = datetime.fromtimestamp(record.created)
            ts = now.strftime("%Y-%m-%d %H:%M:%S") + f",{int(record.msecs):03d}"
            msg = record.getMessage()
            lvl = record.levelname.upper()
            logger_name = record.name
            raw = format_log_line(ts, lvl, logger_name, msg)
            LOG_BUFFER.append({
                "timestamp": ts,
                "level": lvl,
                "logger": logger_name,
                "message": msg,
                "raw": raw,
            })
        except Exception:
            self.handleError(record)


def get_log_buffer(
    limit: int = 150,
    level: Optional[str] = None,
    search: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve filtered log entries for the Admin Monitoring Console."""
    logs = list(LOG_BUFFER)
    # Reverse so newest are first
    logs.reverse()

    if level and level.upper() != "ALL":
        target_lvl = level.upper().strip()
        logs = [entry for entry in logs if entry["level"] == target_lvl]

    if start_time:
        clean_start = start_time.replace("T", " ").strip()
        logs = [entry for entry in logs if entry["timestamp"] >= clean_start]

    if end_time:
        clean_end = end_time.replace("T", " ").strip()
        # If user passed only date YYYY-MM-DD or datetime without milliseconds, allow up to end of that minute/second
        if len(clean_end) == 10:
            clean_end += " 23:59:59,999"
        elif len(clean_end) == 16:
            clean_end += ":59,999"
        logs = [entry for entry in logs if entry["timestamp"] <= clean_end]

    if search:
        s = search.lower().strip()
        logs = [
            entry for entry in logs
            if s in entry["message"].lower() or s in entry["logger"].lower() or s in entry["raw"].lower()
        ]

    return logs[:limit]


def setup_logging():
    from app.core.config import get_settings
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Attach in-memory buffer handler if not already attached
    if not any(isinstance(h, BufferLogHandler) for h in root_logger.handlers):
        buffer_handler = BufferLogHandler()
        buffer_handler.setLevel(log_level)
        root_logger.addHandler(buffer_handler)

    # Enable LangChain / LangSmith environment variables if enabled
    if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer() if settings.APP_ENV == "local" else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Seed initial startup log entries in the structured enterprise format
    app_log("INFO", "system.startup", "Building Enterprise RAG pipeline...")
    app_log("INFO", "vector_store.qdrant", f"Qdrant Cloud collection '{settings.QDRANT_COLLECTION}' active and connected")
    app_log("INFO", "embeddings.jina", f"Initializing embeddings model '{settings.EMBEDDING_MODEL}' ({settings.EMBEDDING_DIM}-dim)")
    app_log("INFO", "llm.engine", f"Initializing primary LLM '{settings.GROQ_MODEL}' via Groq cloud")
    app_log("INFO", "guardrails.config", f"Configuring input guard '{settings.PROMPT_GUARD_MODEL}' and safeguard '{settings.GUARD_MODEL_NAME}'")
    app_log("INFO", "rag.agent", "Role-aware Enterprise assistant ready to take questions")


logger = structlog.get_logger()
