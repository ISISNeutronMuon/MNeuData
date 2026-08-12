"""Utilities for parsing ICPDebug.txt"""

import logging
from pathlib import Path

from .models import ICP

logger = logging.getLogger("isis_archive")

ICP_ALARM_SUFFIX = "_ICPalarm.txt"
ICP_DEBUG_SUFFIX = "_ICPdebug.txt"
ICP_EVENT_SUFFIX = "_ICPevent.txt"


def read_icp_files(nexus_file: Path) -> ICP:
    # Mandatory fields: exception gets raised
    icp = ICP(read_icp_debug(nexus_file), read_icp_event(nexus_file))
    try:
        icp.icp_alarm = read_icp_alarm(nexus_file)
    except (FileNotFoundError, RuntimeError) as exc:
        logger.debug(f"Error parsing ICP alarm for {nexus_file}: {exc}")

    return icp


def icp_file_path(nexus_file: Path, suffix: str) -> Path:
    return nexus_file.with_name(f"{nexus_file.stem}{suffix}")


def read_icp_alarm(nexus_path: Path) -> str:
    """Read the ICPalarm.txt file associated with the given NeXus file

    Raises
    ------
    FileNotFoundError
    """
    return _read_all(icp_file_path(nexus_path, ICP_ALARM_SUFFIX))


def read_icp_debug(nexus_path: Path) -> str:
    """Read the ICPdebug.txt file associated with the given NeXus file

    Raises
    ------
    FileNotFoundError
    """
    return _read_all(icp_file_path(nexus_path, ICP_DEBUG_SUFFIX))


def read_icp_event(nexus_path: Path) -> str:
    """Read the ICPevent.txt file associated with the given NeXus file

    Raises
    ------
    FileNotFoundError
    """
    return _read_all(icp_file_path(nexus_path, ICP_EVENT_SUFFIX))


# -----------------------------------------------------------------------------
# Private
# -----------------------------------------------------------------------------
def _read_all(filepath: Path) -> str:
    """Read the contents of the file and return them as is.

    Raises
    ------
    FileNotFoundError
        If ``filepath`` does not exist.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as fp:
        content = fp.read()

    logger.debug(f"Read content from {filepath}")
    return content
