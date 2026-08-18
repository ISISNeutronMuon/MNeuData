"""Tests for :mod:`isis_archive.nexus.hdf4`.

These build a small synthetic HDF4 file that mimics the structure of an ISIS
muon NeXus file and then read it back with :func:`summarise_nexus`.

They require ``pyhdf`` (and the native HDF4 library). Importing ``pyhdf.HDF``
loads the native C extension, which fails if the HDF4 library is missing or if
pyhdf was built against an incompatible NumPy ABI; ``importorskip`` only catches
``ImportError`` so the wider failure is guarded explicitly and the whole module
is skipped when pyhdf is not usable.
"""

from pathlib import Path

import numpy as np
import pytest

try:
    import pyhdf.HDF
    import pytest
    from pyhdf.HDF import HC, HDF
    from pyhdf.SD import SD, SDC
except ImportError:
    pytest.skip("Error importing pyhdf. Skipping tests", allow_module_level=True)

from isis_archive.models import NexusSummary
from isis_archive.nexus.constants import NXDATA_CLASS, NXENTRY_CLASS, NXLOG_CLASS
from isis_archive.nexus.hdf4 import summarise_nexus

# Synthetic contents. counts is shaped (n_spectra, n_bins).
COUNTS = np.arange(64 * 8, dtype=np.int32).reshape(64, 8)
EXPECTED_TOTAL_COUNTS = int(COUNTS.sum())

# (log_name, number_of_time_points)
NXLOGS = [("Temp_1", 5), ("Field_1", 3), ("Slits", 4)]
EXPECTED_NXLOG_ENTRIES = len(NXLOGS)
EXPECTED_NXLOG_TIME_POINTS = sum(n for _, n in NXLOGS)


def _write_sds(sd: SD, name: str, data: np.ndarray):
    """Create an SDS from ``data`` and return the (dataset, ref)."""
    sds = sd.create(name, SDC.INT32, data.shape)
    sds[:] = data
    ref = sds.ref()
    sds.endaccess()
    return ref


@pytest.fixture
def muon_hdf4_file(tmp_path: Path) -> Path:
    """Write a minimal muon-style HDF4 file and return its path.

    Structure::

        run                        (NXentry)
          histogram_data_1         (NXdata)
            counts                 SDS, shape (64, 8)
          Temp_1                   (NXlog)  time SDS
          Field_1                  (NXlog)  time SDS
          Slits                    (NXlog)  time SDS
    """
    path = tmp_path / "TEST00001.nxs"
    filename = str(path)

    # SDS datasets are created through the SD interface; vgroups then reference
    # them by ref via the V interface.
    sd = SD(filename, SDC.WRITE | SDC.CREATE)
    hdf = HDF(filename, HC.WRITE)
    v = hdf.vgstart()
    try:
        # Datasets ---------------------------------------------------------
        counts_ref = _write_sds(sd, "counts", COUNTS)
        log_time_refs = {
            name: _write_sds(sd, f"{name}_time", np.arange(n, dtype=np.int32))
            for name, n in NXLOGS
        }

        # NXdata group with the counts dataset -----------------------------
        histogram = v.create("histogram_data_1")
        histogram._class = NXDATA_CLASS
        histogram.add(HC.DFTAG_NDG, counts_ref)

        # NXlog groups, each holding its time dataset ----------------------
        log_groups = []
        for name, _n in NXLOGS:
            log = v.create(name)
            log._class = NXLOG_CLASS
            log.add(HC.DFTAG_NDG, log_time_refs[name])
            log_groups.append(log)

        # NXentry "run" holds histogram_data_1 and the NXlog groups ---------
        run = v.create("run")
        run._class = NXENTRY_CLASS
        run.insert(histogram)
        for log in log_groups:
            run.insert(log)

        run.detach()
        histogram.detach()
        for log in log_groups:
            log.detach()
    finally:
        v.end()
        hdf.close()
        sd.end()

    return path


@pytest.fixture
def summary(muon_hdf4_file: Path) -> NexusSummary:
    return summarise_nexus(muon_hdf4_file)


def test_returns_nexus_summary(summary):
    assert isinstance(summary, NexusSummary)


def test_total_detector_mevents(summary):
    assert summary.total_detector_mevents == pytest.approx(
        EXPECTED_TOTAL_COUNTS / 1_000_000
    )


def test_no_monitor_mevents(summary):
    assert summary.total_monitor_mevents == 0.0


def test_nxlog_entries_counted_as_selog(summary):
    assert summary.selog_entries_count == EXPECTED_NXLOG_ENTRIES


def test_nxlog_time_points(summary):
    assert summary.total_selog_time_points == EXPECTED_NXLOG_TIME_POINTS


def test_framelog_fields_zero(summary):
    assert summary.framelog_entries_count == 0
    assert summary.total_framelog_time_points == 0


def test_missing_counts_dataset_raises(tmp_path):
    """An NXdata group without a 'counts' dataset should raise ValueError."""
    filename = str(tmp_path / "no_counts.nxs")
    sd = SD(filename, SDC.WRITE | SDC.CREATE)
    hdf = HDF(filename, HC.WRITE)
    v = hdf.vgstart()
    try:
        other_ref = _write_sds(sd, "not_counts", np.arange(4, dtype=np.int32))
        data = v.create("histogram_data_1")
        data._class = NXDATA_CLASS
        data.add(HC.DFTAG_NDG, other_ref)
        data.detach()
    finally:
        v.end()
        hdf.close()
        sd.end()

    with pytest.raises(ValueError, match="counts"):
        summarise_nexus(tmp_path / "no_counts.nxs")


def test_missing_file_raises():
    with pytest.raises(pyhdf.error.HDF4Error, match="no such file"):
        summarise_nexus(Path("/no/such/dir/does_not_exist.nxs"))
