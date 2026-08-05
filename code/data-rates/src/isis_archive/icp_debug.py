"""Utilities for parsing ICPDebug.txt"""

import logging
from pathlib import Path

logger = logging.getLogger("isis_archive")

# Word marking a failure line in an ``_ICPdebug.txt`` file.
ICP_DEBUG_FAILURE_MARKER = "failed"


def count_icp_debug_failures(debug_path: Path) -> int:
    """Count the number of lines in an ICP debug file that contain a failure.

    A line is counted if it contains the word ``"failed"`` (case-insensitive).

    Raises
    ------
    FileNotFoundError
        If ``debug_path`` does not exist.
    """
    count = 0
    with open(debug_path, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            if ICP_DEBUG_FAILURE_MARKER in line.lower():
                count += 1

    logger.debug(f"Found {count} failure line(s) in {debug_path}")
    return count


def icp_debug_path(nexus_file: Path) -> Path:
    """Return the ``_ICPdebug.txt`` path that sits next to a NeXus file.

    The debug file has the same name as the NeXus file with the ``.nxs``
    extension replaced by ``_ICPdebug.txt`` (e.g. ``MAR28627.nxs`` ->
    ``MAR28627_ICPdebug.txt``).
    """
    return nexus_file.with_name(f"{nexus_file.stem}_ICPdebug.txt")
