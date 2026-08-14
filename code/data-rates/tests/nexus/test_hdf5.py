"""Tests for :mod:`isis_archive.nexus.hdf5`."""

from pathlib import Path

import h5py
import numpy as np
import pytest

from isis_archive.nexus.hdf5 import RAW_DATA_1, summarise_nexus

# Expected values, derived from the data written by the ``nexus_file`` fixture.
EXPECTED_DETECTOR_COUNTS = 3_000_000
EXPECTED_MONITOR_COUNTS = 1_500_000  # 5e5 + 1e6
EXPECTED_SELOG_ENTRIES = 2
EXPECTED_SELOG_TIME_POINTS = 7  # value_log/time lengths: 3 + 4
EXPECTED_FRAMELOG_ENTRIES = 2
EXPECTED_FRAMELOG_TIME_POINTS = 11  # time lengths: 5 + 6


def _add_class_group(
    parent: h5py.Group,
    name: str,
    nx_class: str,
    dataset_name: str,
    values: np.ndarray,
) -> h5py.Group:
    """Create ``name`` under ``parent`` tagged as ``nx_class`` with a dataset."""
    group = parent.create_group(name)
    ascii_type = h5py.string_dtype("ascii", len(nx_class))
    group.attrs["NX_class"] = np.array(nx_class.encode("latin-1"), dtype=ascii_type)
    group.create_dataset(dataset_name, data=values)
    return group


@pytest.fixture
def nexus_file_hdf5(tmp_path: Path) -> Path:
    """Create a minimal ISIS-style ``.nxs`` file and return its path."""
    path = tmp_path / "TEST00001.nxs"

    with h5py.File(str(path), "w") as fp:
        root = fp.create_group(RAW_DATA_1)
        root.attrs["NX_class"] = "NXentry"

        # Histogram data
        _add_class_group(
            root,
            "detector_1",
            "NXdata",
            "counts",
            np.full(5, EXPECTED_DETECTOR_COUNTS / 5, dtype=np.int32),
        )
        # Monitor data
        _add_class_group(
            root,
            "monitor_1",
            "NXmonitor",
            "data",
            np.array([EXPECTED_MONITOR_COUNTS * 0.75], dtype=np.int32),
        )
        _add_class_group(
            root,
            "monitor_2",
            "NXmonitor",
            "data",
            np.array([EXPECTED_MONITOR_COUNTS * 0.25], dtype=np.int32),
        )

        # selog: each block has a value_log/time array.
        selog = root.create_group("selog")
        selog.attrs["NX_class"] = "IXselog"
        for block_name, n_times in (("temperature", 3), ("field", 4)):
            block = selog.create_group(block_name)
            value_log = block.create_group("value_log")
            value_log.create_dataset("time", data=np.arange(n_times, dtype=np.float32))

        # framelog: each block has a time array directly.
        framelog = root.create_group("framelog")
        framelog.attrs["NX_class"] = "NXcollection"
        for block_name, n_times in (("proton_charge", 5), ("period", 6)):
            block = framelog.create_group(block_name)
            block.create_dataset("time", data=np.arange(n_times, dtype=np.float32))

    return path


def test_summarise_nexus(nexus_file_hdf5: Path):
    summary = summarise_nexus(nexus_file_hdf5)

    assert summary.total_detector_mevents == EXPECTED_DETECTOR_COUNTS / 1_000_000
    assert summary.total_monitor_mevents == EXPECTED_MONITOR_COUNTS / 1_000_000
    assert summary.monitor_count == 2
    assert summary.monitor_time_channel_count == 1
    assert summary.selog_entries_count == EXPECTED_SELOG_ENTRIES
    assert summary.framelog_entries_count == EXPECTED_FRAMELOG_ENTRIES
