from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast

from .models import NexusIOError, NexusSummary, RunSummary

logger = logging.getLogger("isis_archive")

# Output field ordering
JOURNAL_FIELD_ORDER = [
    "run_number",
    "experiment_identifier",
    "title",
    "start_time",
    "end_time",
    "duration",
    "proton_charge",
    "raw_frames",
    "good_frames",
    "number_periods",
    "total_mevents",
    "event_mode",
    "number_spectra",
    "number_detectors",
    "frame_sync",
]
NEXUS_FIELD_ORDER = [
    "file_size_bytes",
    "total_detector_mevents",
    "total_monitor_mevents",
    "selog_entries_count",
    "total_selog_time_points",
    "framelog_entries_count",
    "total_framelog_time_points",
]
ICP_FIELD_ORDER = ["icp_debug_text"]


def json_filename(beamline: str, cycle: str) -> str:
    """Build the CSV filename for a beamline/cycle group."""
    return f"{beamline}_{cycle}.json"


def write_cycle_files(
    beamline: str, cycle: str, summaries: list[RunSummary], output: Path
):
    """Write summary information as JSON records and any failed nexus reads"""
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / json_filename(beamline, cycle)

    records = [_to_record(summary) for summary in summaries]
    with open(json_path, "w") as fp:
        json.dump(records, fp)

    logger.info(f"Wrote {len(records)} run(s) to {json_path}")
    write_failed_nexus_read_log(beamline, cycle, summaries, output)


def _to_record(summary: RunSummary) -> dict:
    """Serialize a summary as a JSON record"""

    def nexus_field_or_none(field: str):
        return getattr(nexus, field) if has_nexus else None

    journal, nexus = summary.journal, summary.nexus
    has_nexus = isinstance(summary.nexus, NexusSummary)
    return {
        # primary key
        "beamline": summary.beamline,
        "cycle": summary.cycle,
        # journal fields
        "journal_filename": str(summary.journal_file),
        **{column: getattr(journal, column) for column in JOURNAL_FIELD_ORDER},
        # nexus fields
        "nexus_filename": (
            str(summary.nexus_file) if summary.nexus_file is not None else None
        ),
        **{column: nexus_field_or_none(column) for column in NEXUS_FIELD_ORDER},
        # icp_debug
        **{column: getattr(summary, column) for column in ICP_FIELD_ORDER},
    }


def failed_nexus_log_filename(beamline: str, cycle: str) -> str:
    return f"{beamline}_{cycle}_failed_nexus_reads.txt"


def write_failed_nexus_read_log(
    beamline: str, cycle: str, summaries: list[RunSummary], output: Path
) -> None:
    """Dump the paths of any failed NeXus reads for a single cycle to a file."""
    failures = [s for s in summaries if isinstance(s.nexus, NexusIOError)]
    if not failures:
        return

    output_file = output / failed_nexus_log_filename(beamline, cycle)
    with open(output_file, "w") as fp:
        fp.write("\n".join(cast(NexusIOError, s.nexus).message for s in failures))

    logger.info(f"Wrote {len(failures)} failed NeXus read(s) to {output_file}")
