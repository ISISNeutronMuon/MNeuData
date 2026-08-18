"""Utility code for parsing ISIS journals."""

import logging
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path
from typing import cast

from .discover import DiscoveredJournal
from .facility import find_nexus_file
from .icp import read_icp_files
from .models import JournalEntry, NexusIOError, RunSummary
from .nexus import summarise_nexus

logger = logging.getLogger("isis_archive")

# NeXus/journal XML namespace used by the journal files.
JOURNAL_NAMESPACE = "http://definition.nexusformat.org/schema/3.0"

# Map a dataclass field's type annotation to a converter callable used on the
# stripped XML element text. Because ``from __future__ import annotations`` is
# active, ``dataclasses.Field.type`` is the annotation *string* (e.g. "int").
_TYPE_CONVERTERS: dict[str, type[int | float | str]] = {
    "int": int,
    "float": float,
    "str": str,
}
_SKIP_FIELDS = ("filename",)
_TIME_REGIMES_FIELD = "number_time_channels"


def parse_journal(journal_path: Path) -> Iterator[JournalEntry]:
    """Parse a single journal XML file into :class:`JournalEntry` objects.

    One :class:`JournalEntry` is yielded per ``NXentry`` element found in the
    file.
    """
    logger.debug(f"Parsing journal file {journal_path}")
    try:
        tree = ET.parse(journal_path)
    except ET.ParseError as exc:
        logger.warning(f"Failed to parse {journal_path}: {exc}")
        return

    root = tree.getroot()
    entry_count = 0
    for entry in root:
        journal_fields = {}
        for field in filter(lambda x: x.name not in _SKIP_FIELDS, fields(JournalEntry)):
            if field.name != _TIME_REGIMES_FIELD:
                journal_fields[field.name] = _field_value_or_error(
                    entry, field.name, cast(str, field.type)
                )
            else:
                time_regimes = entry.findall(f"{{{JOURNAL_NAMESPACE}}}IXtime_regime")
                journal_fields[field.name] = [
                    _field_value_or_error(child, field.name, "int")
                    for child in time_regimes
                ]

        journal_fields["filename"] = journal_path.name
        entry_count += 1
        yield JournalEntry(**journal_fields)

    logger.debug(f"Parsed {entry_count} entries from {journal_path}")


def summarise_journal(
    journal: DiscoveredJournal,
    limit: int | None,
    skip_nexus: bool = False,
) -> list[RunSummary]:
    """Summarise a :class:`RunSummary` for each entry in a single journal file.

    When ``skip_nexus`` is ``True`` the associated NeXus (and ICP debug) files
    are not opened; the NeXus-derived fields are left unpopulated.

    """
    entries = list(parse_journal(journal.path))

    summaries = []
    for journal_entry in entries:
        summaries.append(summarise_run(journal, journal_entry, skip_nexus))
        if limit is not None and len(summaries) == limit:
            break

    return summaries


def summarise_run(
    journal: DiscoveredJournal,
    journal_entry: JournalEntry,
    skip_nexus: bool = False,
) -> RunSummary:
    """Summarise a run based on the given journal entry.

    Unless ``skip_nexus`` is ``True`` this also reads additional information from
    the associated NeXus and ICP debug files. When skipped, ``nexus_file`` and
    ``nexus`` are ``None`` so all NeXus-derived output fields serialise as
    ``null``.
    """
    if skip_nexus:
        return RunSummary(
            journal.beamline,
            journal.cycle_suffix,
            journal_entry.run_number,
            journal_entry,
            None,
            None,
        )

    nexus_file = None
    try:
        nexus_file = find_nexus_file(
            journal.beamline_dir,
            journal.cycle_suffix,
            journal.beamline,
            journal_entry.run_number,
        )
        nexus_summary = summarise_nexus(nexus_file)
    except FileNotFoundError:
        nexus_summary = NexusIOError("NeXus file missing")
    except (KeyError, RuntimeError) as exc:
        logger.exception(f"{nexus_file}")
        nexus_summary = NexusIOError(f"{nexus_file}: {exc}")

    icp = None
    if nexus_file is not None:
        try:
            icp = read_icp_files(nexus_file)
        except FileNotFoundError as exc:
            logger.debug(
                f"No ICP file for {journal.beamline} run "
                f"{journal_entry.run_number}: {exc}"
            )
        except RuntimeError:
            logger.exception(
                f"Failed to read ICP files for {journal.beamline} run "
                f"{journal_entry.run_number}"
            )

    return RunSummary(
        journal.beamline,
        journal.cycle_suffix,
        journal_entry.run_number,
        journal_entry,
        nexus_summary,
        icp,
    )


# -----------------------------------------------------------------------------
# Private
# -----------------------------------------------------------------------------
def _field_value_or_error(xml_element: ET.Element, field_name: str, field_type: str):
    child = xml_element.find(f"{{{JOURNAL_NAMESPACE}}}{field_name}")
    if child is None:
        raise ValueError(f"Missing journal field entry {field_name}.")

    text = child.text
    if text is None:
        raise ValueError(
            f"XML element {xml_element.tag} contains entry {field_name} but has an empty value."
        )

    try:
        return _TYPE_CONVERTERS.get(cast(str, field_type), str)(text)
    except (TypeError, ValueError):
        raise ValueError(f"Could not convert {text} for field {field_name}")
