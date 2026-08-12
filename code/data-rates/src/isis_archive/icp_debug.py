"""Utilities for parsing ICPDebug.txt"""

import logging
from pathlib import Path

logger = logging.getLogger("isis_archive")


def read_icp_debug(nexus_path: Path) -> str:
    """Read the ICPdebug.txt file associated with the given NeXus file

    Raises
    ------
    FileNotFoundError
        If ``debug_path`` does not exist.
    """
    path = icp_debug_path(nexus_path)
    with open(path, "r", encoding="utf-8", errors="replace") as fp:
        content = fp.read()

    logger.debug(f"Read ICPdebug content from {path}")
    return content


def icp_debug_path(nexus_file: Path) -> Path:
    """Return the ``_ICPdebug.txt`` path that sits next to a NeXus file.

    The debug file has the same name as the NeXus file with the ``.nxs``
    extension replaced by ``_ICPdebug.txt`` (e.g. ``MAR28627.nxs`` ->
    ``MAR28627_ICPdebug.txt``).
    """
    return nexus_file.with_name(f"{nexus_file.stem}_ICPdebug.txt")
