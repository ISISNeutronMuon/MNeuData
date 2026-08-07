from pathlib import Path

from ..models import NexusSummary
from .hdf5 import summarise_nexus as summarise_nexus_hdf5  # noqa: E402

# File-format magic bytes.
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"  # first 8 bytes of any HDF5 file
HDF4_MAGIC = b"\x0e\x03\x13\x01"  # first 4 bytes of any HDF4 file


def _read_magic(nexus_path: Path, size: int = 8) -> bytes:
    """Return the first ``size`` bytes of ``nexus_path``."""
    with open(nexus_path, "rb") as fp:
        return fp.read(size)


def summarise_nexus(nexus_path: Path) -> NexusSummary:
    """Summarise a NeXus file, dispatching on its underlying HDF format.

    ISIS NeXus files may be either HDF5 (neutron) or HDF4 (muon). The format is
    detected from the file's magic bytes.
    """
    magic = _read_magic(nexus_path)

    if magic.startswith(HDF5_MAGIC):
        return summarise_nexus_hdf5(nexus_path)

    if magic.startswith(HDF4_MAGIC):
        raise NotImplementedError(
            f"HDF4 NeXus files are not yet supported: {nexus_path}"
        )

    raise ValueError(f"Unrecognised NeXus file format (bad magic bytes): {nexus_path}")
