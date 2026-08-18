from __future__ import annotations

import logging
from dataclasses import fields
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .models import ICP, NexusIOError, NexusSummary, RunSummary

logger = logging.getLogger("isis_archive")


def pq_filename(beamline: str, cycle: str, kind: str) -> str:
    """Build the parquet filename for a beamline/cycle group."""
    return f"{beamline}_{cycle}_{kind}.parquet"


def write_cycle_files(
    beamline: str, cycle: str, summaries: list[RunSummary], output: Path
):
    """Write summary information as a parquet files and any failed nexus reads separately

    Journal information and NeXus information gets written separately to different files.
    """

    output.mkdir(parents=True, exist_ok=True)
    journal_records, nexus_records, failed_nexus_reads, icp_records = [], [], [], []
    for summary in summaries:
        journal_records.append(_to_record(summary, summary.journal))
        if isinstance(summary.nexus, NexusSummary):
            nexus_records.append(_to_record(summary, summary.nexus))
        elif isinstance(summary.nexus, NexusIOError):
            failed_nexus_reads.append(_to_record(summary, summary.nexus))
        if isinstance(summary.icp, ICP):
            icp_records.append(_to_record(summary, summary.icp))

    _write_pq(journal_records, output / pq_filename(beamline, cycle, "journal"))

    if len(nexus_records) > 0:
        _write_pq(nexus_records, output / pq_filename(beamline, cycle, "nexus"))

    if len(failed_nexus_reads) > 0:
        _write_pq(
            failed_nexus_reads,
            output / pq_filename(beamline, cycle, "nexus_failed"),
        )

    if len(icp_records) > 0:
        _write_pq(icp_records, output / pq_filename(beamline, cycle, "icp"))


# -----------------------------------------------------------------------------
# Private
# -----------------------------------------------------------------------------


def _to_record(summary: RunSummary, model) -> dict:
    """Serialize a model from the RunSummary as a dict"""

    return {
        # primary key
        "beamline": summary.beamline,
        "cycle": summary.cycle,
        "run_number": summary.run_number,
        # model fields
        **{field.name: getattr(model, field.name) for field in fields(model.__class__)},
    }


def _write_pq(records: list[dict], filepath: Path):
    """Write records to .parquet file."""
    if len(records) > 0:
        pq.write_table(
            pa.Table.from_pylist(records),
            str(filepath),
        )
    logger.info(f"Wrote {len(records)} run(s) to {filepath}")
