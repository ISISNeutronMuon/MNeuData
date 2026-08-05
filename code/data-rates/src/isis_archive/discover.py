"""Discover journals and Nexus files on the archive."""

import logging
from collections.abc import Iterator
from pathlib import Path

from .models import DiscoveredJournal

logger = logging.getLogger("isis_archive")


def discover_journals(
    root: Path,
    beamlines: list[str],
    cycle_pattern: str | None = None,
) -> Iterator[DiscoveredJournal]:
    """Yield every journal file under ``root``.

    Optionally, restricting by the provided cycle pattern
    """
    for beamline, beamline_dir in discover_beamline_dirs(root, beamlines):
        logger.info(f"Processing instrument {beamline}")
        for journal_path in discover_journals_for_beamline(beamline_dir, cycle_pattern):
            yield DiscoveredJournal(
                beamline=beamline,
                beamline_dir=beamline_dir,
                path=journal_path,
            )


def discover_beamline_dirs(
    root: Path, beamlines: list[str]
) -> Iterator[tuple[str, Path]]:
    """Yield ``(beamline_name, directory)`` for each requested beamline

    An `Instrument` subdirectory must exist
    """
    for beamline in beamlines:
        beamline_dir = root / f"NDX{beamline}"
        if not (beamline_dir / "Instrument").exists():
            logger.warning(
                f"{(beamline_dir / 'Instrument')} missing. Skipping beamline."
            )
            continue
        beamline = beamline_dir.name[3:]
        logger.debug(f"Found instrument directory {beamline_dir} for {beamline}")
        yield beamline, beamline_dir


def discover_journals_for_beamline(
    beamline_dir: Path,
    cycle_pattern: str | None = None,
):
    """Yield a Path for each beamline journal.

    If cycle_pattern is supplied then only include the matching cycles."""
    journal_dir = beamline_dir / "Instrument" / "logs" / "journal"
    if not journal_dir.is_dir():
        logger.info(f"No journal directory at {journal_dir}")
        return

    pattern = (
        f"journal_{cycle_pattern}.xml"
        if cycle_pattern is not None
        else "journal_??_?.xml"
    )
    journals = sorted(journal_dir.glob(pattern), reverse=True)

    logger.debug(
        f"Found {len(journals)} journal file(s) matching {pattern!r} in {journal_dir}"
    )
    yield from journals
