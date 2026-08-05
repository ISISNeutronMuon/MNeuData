"""CSV output for ISIS run summaries."""

from __future__ import annotations

import csv
import logging
from dataclasses import fields
from pathlib import Path
from typing import Any, cast

from .models import NexusIOError, NexusSummary, RunSummary

logger = logging.getLogger("isis_archive")

# The journal and nexus data are written to separate CSV tables. Both tables
# share a set of key columns (``beamline``, ``cycle``, ``run_number``) so the
# two can be joined back together if required.
_KEY_COLUMNS = ["beamline", "cycle", "run_number"]

# Column order for the journal table: shared keys, journal-derived attributes
# and journal provenance.
JOURNAL_CSV_COLUMNS = _KEY_COLUMNS + [
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
    "journal_file",
]

# Column order for the nexus table: shared keys, nexus-derived attributes and
# nexus provenance.
NEXUS_CSV_COLUMNS = _KEY_COLUMNS + [
    "total_detector_mevents",
    "total_monitor_mevents",
    "selog_entries_count",
    "total_selog_time_points",
    "framelog_entries_count",
    "total_framelog_time_points",
    "nexus_file",
]

# Column order for the ICP debug table.
ICP_DEBUG_CSV_COLUMNS = _KEY_COLUMNS + ["icp_error_count"]


def _key_row(summary: RunSummary) -> dict[str, Any]:
    """Return the shared key columns for a summary."""
    return {
        "beamline": summary.beamline,
        "cycle": summary.cycle,
        "run_number": summary.journal.run_number,
    }


def _journal_row(summary: RunSummary) -> dict[str, Any]:
    """Flatten the journal data of a summary into a row for the journal table."""
    return {
        **_key_row(summary),
        **{
            field.name: getattr(summary.journal, field.name)
            for field in fields(summary.journal)
        },
        "journal_file": summary.journal_file,
    }


def _nexus_row(summary: RunSummary) -> dict[str, Any]:
    """Flatten the nexus data of a summary into a row for the nexus table."""
    return (
        {
            **_key_row(summary),
            **{
                field.name: getattr(summary.nexus, field.name)
                for field in fields(summary.nexus)
            },
            "nexus_file": summary.nexus_file,
        }
        if summary.nexus is not None
        else {}
    )


def _icp_debug_row(summary: RunSummary) -> dict[str, Any]:
    """Build a row for the ICP debug table."""
    return {
        **_key_row(summary),
        "icp_error_count": summary.icp_error_count,
    }


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    """Write ``rows`` to ``path`` using ``columns`` as the header order."""
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def csv_filename(beamline: str, cycle: str, kind: str) -> str:
    """Build the CSV filename for a beamline/cycle group and table kind."""
    return f"{beamline}_{cycle}_{kind}.csv"


def write_cycle_files(
    beamline: str, cycle: str, summaries: list[RunSummary], output: Path
) -> None:
    """Write the CSV tables and failed-read log for a single instrument/cycle.

    Four files are written into ``output`` for the group:

    * ``{instrument}_{cycle}_journal.csv`` holding the journal-derived data for
      every run,
    * ``{instrument}_{cycle}_nexus.csv`` holding the NeXus-derived data for the
      runs that were paired with a readable NeXus file,
    * ``{instrument}_{cycle}_icp_debug.csv`` holding the count of failure lines
      in each run's ``_ICPdebug.txt`` file, and
    * ``{instrument}_{cycle}_failed_nexus_reads.txt`` listing any NeXus read
      failures (only written when there are failures).

    The CSV tables share the ``beamline``, ``cycle`` and ``run_number`` key
    columns so they can be joined back together.
    """
    output.mkdir(parents=True, exist_ok=True)

    journal_path = output / csv_filename(beamline, cycle, "journal")
    _write_csv(
        journal_path,
        JOURNAL_CSV_COLUMNS,
        [_journal_row(summary) for summary in summaries],
    )
    logger.info(f"Wrote {len(summaries)} journal run(s) to {journal_path}")

    nexus_group = [s for s in summaries if isinstance(s.nexus, NexusSummary)]
    nexus_path = output / csv_filename(beamline, cycle, "nexus")
    _write_csv(
        nexus_path,
        NEXUS_CSV_COLUMNS,
        [_nexus_row(summary) for summary in nexus_group],
    )
    logger.info(f"Wrote {len(nexus_group)} nexus run(s) to {nexus_path}")

    icp_debug_group = [s for s in summaries if s.icp_error_count is not None]
    icp_debug_path = output / csv_filename(beamline, cycle, "icp_debug")
    _write_csv(
        icp_debug_path,
        ICP_DEBUG_CSV_COLUMNS,
        [_icp_debug_row(summary) for summary in icp_debug_group],
    )
    logger.info(f"Wrote {len(icp_debug_group)} ICP debug row(s) to {icp_debug_path}")

    _write_failed_nexus_read_log(beamline, cycle, summaries, output)


def _failed_nexus_log_filename(instrument: str, cycle: str) -> str:
    return f"{instrument}_{cycle}_failed_nexus_reads.txt"


def _write_failed_nexus_read_log(
    beamline: str, cycle: str, summaries: list[RunSummary], output: Path
) -> None:
    """Dump the paths of any failed NeXus reads for a single cycle to a file."""
    failures = [s for s in summaries if isinstance(s.nexus, NexusIOError)]
    if not failures:
        return

    output_file = output / _failed_nexus_log_filename(beamline, cycle)
    with open(output_file, "w") as fp:
        fp.write("\n".join(cast(NexusIOError, s.nexus).message for s in failures))
    logger.info(f"Wrote {len(failures)} failed NeXus read(s) to {output_file}")
