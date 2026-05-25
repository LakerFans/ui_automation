from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from ui_test_platform.config import settings


def get_checkpointer(fallback: MemorySaver):
    if not settings.use_postgres_checkpointer:
        return fallback
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        saver = PostgresSaver.from_conn_string(settings.postgres_uri)
        saver.setup()
        return saver
    except Exception:
        return fallback
