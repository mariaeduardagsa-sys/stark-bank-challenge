import logging
from pathlib import Path

import starkbank

from app.event_store import list_pending_events
from app.processor import process_event


logger = logging.getLogger(__name__)


def run_pending_events(
    database_path: Path,
    project: starkbank.Project,
) -> list[tuple[str, str]]:
    events = list_pending_events(database_path)
    results = []

    for event_id, content in events:
        try:
            status = process_event(
                database_path,
                event_id,
                content,
                project,
            )
        except Exception:
            logger.exception(
                "Failed to process event %s",
                event_id,
            )
            status = "error"

        results.append((event_id, status))

    return results