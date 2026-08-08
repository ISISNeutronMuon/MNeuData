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
        return NexusSummary(
            total_detector_mevents=_read_total_counts(
                root_entry, NXDATA_CLASS, NXDATA_DATASET
            )
            / 1_000_000,
            total_monitor_mevents=_read_total_counts(
                root_entry, NXMONITOR_CLASS, NXMONITOR_DATASET
            )
            / 1_000_000,
            **dict(
                zip(
                    (
                        "selog_entries_count",
                        "total_selog_time_points",
                        "framelog_entries_count",
                        "total_framelog_time_points",
                    ),
                    _summarise_logs(root_entry, "selog")
                    + _summarise_logs(root_entry, "framelog"),
                )
            ),
        )


# ----------------------------------------------------------
# private
# ----------------------------------------------------------


def _read_total_counts(entry: h5py.Group, nx_class: str, dataset_name: str) -> int:
    """Read and sum the array given by the groups with the given NXClass and dataset name.

    Parameters
    ----------
    entry:
        A group that is the parent of entries of ``nx_class``.
    """
    class_groups = filter(
        lambda x: x.attrs.get("NX_class") == nx_class.encode(), entry.values()
    )
    return int(sum([np.array(grp[dataset_name]).sum() for grp in class_groups]))


def _summarise_logs(parent: h5py.Group, group_name: str) -> tuple[int, int]:
    """Inspect the selog group and return summary statistics

    Parameters
    ----------
    entry:
        A group that is the parent of entries of NXClass
    group_name:
        Name of the log group

    Returns
    -------
    tuple(entries_count, total_time_points)
    """
    group = parent[group_name]
    total_time_points = 0
    for block in group.values():  # type: ignore
        if group_name == "selog":
            value_log = block["value_log"]
        else:
            value_log = block
        total_time_points += len(value_log["time"])

    return len(group), total_time_points  # type: ignore
