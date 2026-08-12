from __future__ import annotations

import logging
from dataclasses import fields
from pathlib import Path
from typing import cast

import pyarrow as pa
import pyarrow.parquet as pq

from .models import ICP, JournalEntry, NexusIOError, NexusSummary, RunSummary

logger = logging.getLogger("isis_archive")


def pq_filename(beamline: str, cycle: str) -> str:
    """Build the parquet filename for a beamline/cycle group."""
    return f"{beamline}_{cycle}.parquet"


def write_cycle_files(
    beamline: str, cycle: str, summaries: list[RunSummary], output: Path
):
    """Write summary information as a parquet file and any failed nexus reads separately"""

    output.mkdir(parents=True, exist_ok=True)
    pq_path = output / pq_filename(beamline, cycle)

    records = [_to_record(summary) for summary in summaries]
    pq.write_table(
        pa.Table.from_pylist(records),
        str(output / pq_filename(beamline, cycle)),
    )

    logger.info(f"Wrote {len(records)} run(s) to {pq_path}")
    write_failed_nexus_read_log(beamline, cycle, summaries, output)


def _to_record(summary: RunSummary) -> dict:
    """Serialize a summary as a JSON record"""

    def field_or_none(obj, field: str):
        return getattr(obj, field) if has_nexus else None

    has_nexus = isinstance(summary.nexus, NexusSummary)
    return {
        # primary key
        "beamline": summary.beamline,
        "cycle": summary.cycle,
        # journal fields
        "journal_filename": str(summary.journal_file),
        **{
            field.name: getattr(summary.journal, field.name)
            for field in fields(JournalEntry)
        },
        # nexus fields
        "nexus_filename": (
            str(summary.nexus_file) if summary.nexus_file is not None else None
        ),
        **{
            field.name: field_or_none(summary.nexus, field.name)
            for field in fields(NexusSummary)
        },
        # icp_debug
        **{field.name: field_or_none(summary.icp, field.name) for field in fields(ICP)},
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
