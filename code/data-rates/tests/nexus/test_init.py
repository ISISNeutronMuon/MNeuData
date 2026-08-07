"""Tests for the format dispatch in :mod:`isis_archive.nexus`."""

from pathlib import Path
from unittest.mock import patch

import pytest

from isis_archive import nexus
from isis_archive.nexus import HDF4_MAGIC, HDF5_MAGIC, summarise_nexus

SENTINEL_SUMMARY = object()


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_hdf5_dispatches_to_hdf5_reader(tmp_path):
    path = _write(tmp_path, "run.nxs", HDF5_MAGIC + b"rest of file")

    with patch.object(
        nexus, "summarise_nexus_hdf5", return_value=SENTINEL_SUMMARY
    ) as mock_reader:
        result = summarise_nexus(path)

    mock_reader.assert_called_once_with(path)
    assert result is SENTINEL_SUMMARY


def test_hdf4_raises_not_implemented(tmp_path):
    path = _write(tmp_path, "MUSR.nxs", HDF4_MAGIC + b"rest of file")

    with (
        patch.object(nexus, "summarise_nexus_hdf5") as mock_reader,
        pytest.raises(NotImplementedError, match="HDF4"),
    ):
        summarise_nexus(path)

    mock_reader.assert_not_called()


def test_unrecognised_magic_raises_value_error(tmp_path):
    path = _write(tmp_path, "junk.nxs", b"not a real hdf file")

    with pytest.raises(ValueError, match="magic bytes"):
        summarise_nexus(path)


def test_empty_file_raises_value_error(tmp_path):
    path = _write(tmp_path, "empty.nxs", b"")

    with pytest.raises(ValueError, match="magic bytes"):
        summarise_nexus(path)


def test_missing_file_raises_os_error(tmp_path):
    with pytest.raises(OSError):
        summarise_nexus(tmp_path / "does_not_exist.nxs")
