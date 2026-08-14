from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

from ..models import NexusSummary
from .constants import NXDATA_CLASS, NXMONITOR_CLASS

logger = logging.getLogger("summarise")

NXDATA_DATASET = "counts"
NXMONITOR_DATASET = "data"
RAW_DATA_1 = "raw_data_1"


def summarise_nexus(nexus_path: Path) -> NexusSummary:
    """Summary information from a NeXus (HDF5) file.

    Parameters
    ----------
    nexus_path:
        Path to the ``.nxs`` HDF5 file for a given run.

    Returns
    -------
    NeXusSummary summarising content from the file.
    """
    with h5py.File(str(nexus_path), "r") as fp:
        root_entry: h5py.Group = fp[RAW_DATA_1]  # type: ignore

        number_monitors, total_monitor_events, number_monitor_time_channels = (
            _summarise_monitors(root_entry)
        )
        return NexusSummary(
            file_size_bytes=nexus_path.stat().st_size,
            total_detector_mcounts=_read_total_counts(
                _groups_with_class(root_entry, NXDATA_CLASS), NXDATA_DATASET
            )
            / 1_000_000,
            total_monitor_mcounts=total_monitor_events / 1_000_000,
            number_monitors=number_monitors,
            number_monitor_time_channels=number_monitor_time_channels,
            number_selog_entries=_count_blocks_with_name(root_entry, "selog"),
            number_framelog_entries=_count_blocks_with_name(root_entry, "framelog"),
        )


# ----------------------------------------------------------
# private
# ----------------------------------------------------------
def _summarise_monitors(parent: h5py.Group) -> tuple[int, int, int]:
    """Return summary information on the monitors"""
    monitors = list(_groups_with_class(parent, NXMONITOR_CLASS))
    if (number_monitors := len(monitors)) > 0:
        # Assume all monitors have the same number of time channels
        return (
            number_monitors,
            _read_total_counts(monitors, NXMONITOR_DATASET),
            np.array(monitors[0][NXMONITOR_DATASET]).size,
        )
    else:
        return 0, 0, 0


def _groups_with_class(parent: h5py.Group, nx_class: str) -> list[h5py.Group]:
    return list(
        filter(lambda x: x.attrs.get("NX_class") == nx_class.encode(), parent.values())
    )


def _read_total_counts(groups: list[h5py.Group], dataset_name: str) -> int:
    """Read and sum the array given by the groups with the given NXClass and dataset name.

    Parameters
    ----------
    entry:
        A group that is the parent of entries of ``nx_class``.
    """
    return int(sum([np.array(grp[dataset_name]).sum() for grp in groups]))


def _count_blocks_with_name(parent: h5py.Group, group_name: str) -> int:
    """Counts numbers of child entries within the named group"""
    return len(parent[group_name])
