"""Tests for the format dispatch in :mod:`isis_archive.nexus`."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from isis_archive.nexus import HDF4_MAGIC, HDF5_MAGIC, summarise_nexus

SENTINEL_SUMMARY = object()


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def _fake_backend(monkeypatch, module_name: str) -> MagicMock:
    """Register a fake ``isis_archive.nexus.<module_name>`` module."""
    reader = MagicMock(return_value=SENTINEL_SUMMARY)
    fake_module = types.ModuleType(f"isis_archive.nexus.{module_name}")
    fake_module.summarise_nexus = reader  # type: ignore
    monkeypatch.setitem(sys.modules, f"isis_archive.nexus.{module_name}", fake_module)
    return reader


def test_hdf5_dispatches_to_hdf5_reader(tmp_path, monkeypatch):
    reader = _fake_backend(monkeypatch, "hdf5")
    path = _write(tmp_path, "run.nxs", HDF5_MAGIC + b"rest of file")

    result = summarise_nexus(path)

    reader.assert_called_once_with(path)
    assert result is SENTINEL_SUMMARY


def test_hdf4_dispatches_to_hdf4_reader(tmp_path, monkeypatch):
    reader = _fake_backend(monkeypatch, "hdf4")
    path = _write(tmp_path, "muon.nxs", HDF4_MAGIC + b"rest of file")

    result = summarise_nexus(path)

    reader.assert_called_once_with(path)
    assert result is SENTINEL_SUMMARY


def test_hdf5_backend_not_imported_for_hdf4_file(tmp_path, monkeypatch):
    hdf5_reader = _fake_backend(monkeypatch, "hdf5")
    hdf4_reader = _fake_backend(monkeypatch, "hdf4")
    path = _write(tmp_path, "muon.nxs", HDF4_MAGIC + b"rest of file")

    summarise_nexus(path)

    hdf4_reader.assert_called_once_with(path)
    hdf5_reader.assert_not_called()


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
