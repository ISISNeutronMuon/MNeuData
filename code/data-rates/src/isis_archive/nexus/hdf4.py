from __future__ import annotations

import logging
from pathlib import Path

import numpy  # noqa: F401
import pyhdf.HDF
import pyhdf.SD
import pyhdf.V  # noqa: F401
from pyhdf.error import HDF4Error
from pyhdf.VS import HC

from ..models import NexusSummary
from .constants import NXDATA_CLASS

logger = logging.getLogger("hdf4")

COUNTS = "counts"


def summarise_nexus(nexus_path: Path) -> NexusSummary:
    """Summary information from a Muon NeXus (HDF4) file.

    Parameters
    ----------
    nexus_path:
        Path to the ``.nxs`` HDF4 file for a given run.

    Returns
    -------
    NeXusSummary summarising content from the file.
    """
    filename = str(nexus_path)
    hdf = pyhdf.HDF.HDF(filename)
    sd_handle = pyhdf.SD.SD(filename)
    vg_handle = hdf.vgstart()
    try:
        return NexusSummary(
            _read_total_detector_counts(vg_handle, sd_handle) / 1_000_000,
            0.0,
            0,
            0,
            0,
            0,
        )
    finally:
        vg_handle.end()
        hdf.close()


# ----------------------------------------------------------
# private
# ----------------------------------------------------------


def _read_total_detector_counts(vg_handle: pyhdf.V.V, sd_handle: pyhdf.SD.SD) -> int:
    nxdata_ref = _top_level_vgroup(vg_handle, NXDATA_CLASS)
    ref_handle = vg_handle.attach(nxdata_ref)
    try:
        tag_refs = ref_handle.tagrefs()
        for tag, ref in tag_refs:
            if tag == HC.DFTAG_NDG:
                sds = sd_handle.select(sd_handle.reftoindex(ref))
                if sds.info()[0] == COUNTS:
                    total_counts = sds.get().sum()
                    sds.endaccess()
                    return total_counts
    finally:
        ref_handle.detach()


def _top_level_vgroup(vg_handle: pyhdf.V.V, nx_class: str) -> int:
    """Return the reference of the top-level vgroup with `nx_class`.

    Raises
    ------
    KeyError
        If no top-level vgroup with that name exists.
    """
    ref = -1
    while True:
        try:
            ref = vg_handle.getid(ref)
        except HDF4Error:
            break
        vg = vg_handle.attach(ref)
        try:
            if vg._class == nx_class:
                return ref
        finally:
            vg.detach()

    raise KeyError(f"No top-level vgroup with NX class {nx_class!r} in file.")
