"""Utility code for parsing ISIS journals."""

import logging
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path
from typing import cast

from .discover import DiscoveredJournal
from .facility import find_nexus_file
from .icp_debug import count_icp_debug_failures, icp_debug_path
from .models import JournalEntry, NexusIOError, RunSummary
from .nexus import summarise_nexus

logger = logging.getLogger("isis_archive")

# NeXus/journal XML namespace used by the journal files.
JOURNAL_NAMESPACE = "http://definition.nexusformat.org/schema/3.0"

# Map a dataclass field's type annotation to a converter callable used on the
# stripped XML element text. Because ``from __future__ import annotations`` is
# active, ``dataclasses.Field.type`` is the annotation *string* (e.g. "int").
_TYPE_CONVERTERS = {
    "int": int,
    "float": float,
    "str": str,
}


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
        if _tag_localname(entry.tag) != "NXentry":
            continue

        children = {_tag_localname(child.tag): child for child in entry}

        journal_fields = {}
        for field in fields(JournalEntry):
            child = children.get(field.name)
            if child is None:
                continue
            text = (child.text or "").strip()
            if not text:
                continue
            convert = _TYPE_CONVERTERS.get(cast(str, field.type), str)
            try:
                value = convert(text)
            except (TypeError, ValueError):
                logger.debug(
                    f"Could not convert {text!r} for field {field.name} in "
                    f"{entry.get('name')}; keeping raw text"
                )
                value = text
            journal_fields[field.name] = value

        entry_count += 1
        yield JournalEntry(**journal_fields)

    logger.debug(f"Parsed {entry_count} entries from {journal_path}")


def summarise_journal(
    root: Path, journal: DiscoveredJournal, limit: int | None
) -> list[RunSummary]:
    """Summarise a :class:`RunSummary` for each entry in a single journal file."""
    summaries = []
    for journal_entry in parse_journal(journal.path):
        summaries.append(summarise_run(root, journal, journal_entry))
        if limit is not None and len(summaries) == limit:
            break

    return summaries


def summarise_run(
    root: Path, journal: DiscoveredJournal, journal_entry: JournalEntry
) -> RunSummary:
    """Summarise a run based on the given journal entry, includes reading additional information from the Nexus file"""
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
        nexus_summary = NexusIOError(
            f"NeXus file missing for {journal.beamline} run number {journal_entry.run_number}"
        )
    except (KeyError, RuntimeError) as exc:
        logger.exception(f"{nexus_file}")
        nexus_summary = NexusIOError(f"{nexus_file}: {exc}")

    # The ICP debug log sits next to the NeXus file; count its failures.
    icp_error_count = None
    if nexus_file is not None:
        try:
            icp_error_count = count_icp_debug_failures(icp_debug_path(nexus_file))
        except FileNotFoundError:
            logger.debug(
                f"No ICP debug file for {journal.beamline} run "
                f"{journal_entry.run_number}"
            )
        except RuntimeError:
            logger.exception(
                f"Failed to read ICP debug file for {journal.beamline} run "
                f"{journal_entry.run_number}"
            )

    return RunSummary(
        journal.beamline,
        journal.cycle_suffix,
        journal.path.relative_to(root),
        nexus_file.relative_to(root) if nexus_file is not None else None,
        journal_entry,
        nexus_summary,
        icp_error_count,
    )


def _tag_localname(tag: str) -> str:
    """Return the local (namespace-stripped) name of an XML tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag
