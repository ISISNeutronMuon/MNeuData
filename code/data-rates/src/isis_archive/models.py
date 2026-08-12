from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveredJournal:
    """A journal file located during a walk, with its beamline context."""

    beamline: str
    beamline_dir: Path
    path: Path

    @property
    def cycle_suffix(self) -> str:
        stem = self.path.stem  # e.g. "journal_19_4"
        prefix = "journal_"
        if not stem.startswith(prefix):
            raise ValueError(
                f"Invalid journal filename: {self.path}. Filename should start with {prefix}"
            )

        suffix = stem[len(prefix) :]
        if suffix:
            return suffix
        else:
            raise ValueError(
                f"Invalid journal filename: {self.path}. Filename has no suffix."
            )

    @property
    def output_key(self) -> tuple[str, str]:
        return (self.beamline, self.cycle_suffix)


@dataclass
class JournalEntry:
    """Attributes parsed from a journal ``NXentry`` element."""

    # required fields
    experiment_identifier: int
    run_number: int

    start_time: str
    end_time: str
    duration: int
    proton_charge: float
    raw_frames: int
    good_frames: int
    total_mevents: float
    event_mode: float
    number_periods: int

    number_spectra: int
    number_detectors: int

    frame_sync: str

    # optional fields
    title: str = ""


@dataclass
class NexusSummary:
    """Summary information derivied from an ISIS NeXus file."""

    file_size_bytes: int

    total_detector_mevents: float
    total_monitor_mevents: float

    selog_entries_count: int  # the number of IXselog entries
    total_selog_time_points: int  # the total count of the len(block_name/value_log/time) array across all selog entries
    framelog_entries_count: int  # the number of NXcollection entries
    total_framelog_time_points: int  # the total count of the len(block_name/time) array across all framelog entries


@dataclass
class NexusIOError:
    """Summary of an error from a failed read."""

    message: str


@dataclass
class RunSummary:
    """Summary information for a single run.

    The ``journal`` field holds the attributes parsed from an ``NXentry``
    element. The ``nexus`` field is reserved for extra attributes read directly
    from the associated HDF5/HDF4 file.
    """

    # Provenance / linkage
    beamline: str
    cycle: str
    journal_file: Path
    nexus_file: Path | None

    # Journal-derived attributes.
    journal: JournalEntry

    # Extra attributes filled in from the HDF5 file (if it can be read).
    # ``None`` when NeXus parsing was skipped entirely (see ``skip_nexus``).
    nexus: NexusSummary | NexusIOError | None = None

    # Number of lines containing a failure in the ``_ICPdebug.txt`` file that
    # sits next to the NeXus file. ``None`` if the debug file was not found.
    icp_error_count: int | None = None
