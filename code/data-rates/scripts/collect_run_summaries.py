#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.4.2",
#     "isis-archive",
# ]
#
# [tool.uv.sources]
# isis-archive = { path = "../" }
# ///
"""Summarise ISIS instrument journal and NeXus data."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from pathlib import Path

import click

from isis_archive.cycle import CYCLE_ID_RE
from isis_archive.discover import discover_journals
from isis_archive.journal import summarise_journal
from isis_archive.json_writer import json_filename, write_cycle_files
from isis_archive.models import RunSummary

logger = logging.getLogger("collect_run_summaries")

LOGGER_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

CycleCompleteCallback = Callable[[str, str, list[RunSummary]], None]
SkipCycleCallback = Callable[[str, str], bool]


def collect_summaries(
    root: Path,
    beamlines: list[str],
    cycle_pattern: str | None = None,
    on_cycle_complete: CycleCompleteCallback | None = None,
    should_skip_cycle: SkipCycleCallback | None = None,
    max_workers: int | None = None,
    limit_per_worker: int | None = None,
) -> list[RunSummary]:
    """Walk the root directory and build a list of :class:`RunSummary`.

    Each journal file maps to exactly one ``(beamline, cycle)``.
    """
    logger.info(f"Collecting summaries from {root}")
    if cycle_pattern is not None:
        logger.info(f"Restricting to cycle {cycle_pattern}")

    journals = discover_journals(root, beamlines, cycle_pattern)
    if should_skip_cycle is not None:
        journals = list(
            filter(lambda j: should_skip_cycle(j.beamline, j.cycle_suffix), journals)
        )
        logger.debug(f"Using {len(journals)} journal file(s) after applying filters.")

    summaries: list[RunSummary] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_journal = {
            executor.submit(summarise_journal, root, journal, limit_per_worker): journal
            for journal in journals
        }
        logger.info(f"Submitted {len(future_to_journal)} cycle(s) to the pool")
        try:
            for future in as_completed(future_to_journal):
                journal = future_to_journal[future]
                cycle_summaries = future.result()
                summaries.extend(cycle_summaries)
                if on_cycle_complete is not None and cycle_summaries:
                    on_cycle_complete(
                        journal.beamline, journal.cycle_suffix, cycle_summaries
                    )
        except KeyboardInterrupt:
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    logger.info(f"Collected {len(summaries)} summaries")
    return summaries


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _should_skip_cycle(beamline: str, cycle_suffix: str, output_dir: Path) -> bool:
    return not (output_dir / json_filename(beamline, cycle_suffix)).exists()


def _validate_cycle_pattern(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> str | None:
    """Validate a cycle suffix pattern passed on the command line."""
    if value is None:
        return None
    if not CYCLE_ID_RE.match(value):
        raise click.BadParameter(
            f"{value!r} is not a valid cycle pattern (expected YY_N, where '?' is allowed to specify all values)."
        )
    return value


@click.command(
    help=(
        "Parse ISIS journal XML and NeXus HDF5 files to produce run summaries. "
        "Writes results as CSV files (one per instrument and cycle) into OUTPUT_DIR "
        "directory. Files are named {instrument}_{cycle}.csv."
    )
)
@click.argument(
    "root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--beamline",
    "-b",
    type=str,
    required=True,
    help="Select the beamline(s) to process. May be repeated to include several beamlines.",
    multiple=True,
)
@click.option(
    "--cycle",
    "-c",
    type=str,
    default=None,
    callback=_validate_cycle_pattern,
    metavar="YY_N",
    help="Restrict to cycles matching the given pattern matched against the suffix",
)
@click.option(
    "--max-workers",
    "-j",
    type=click.IntRange(min=1),
    default=1,
    help=(
        "Maximum number of worker processes used to summarise cycles "
        "concurrently. Defaults to a single worker."
    ),
)
@click.option(
    "--limit-per-worker",
    "-L",
    type=click.IntRange(min=1),
    default=None,
    help=("Parse up to this number of entries per worker. Mainly used for testing."),
)
@click.option(
    "--log-level",
    "-v",
    type=click.Choice(logging.getLevelNamesMapping().keys(), case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Set the logging verbosity.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help=(
        "Force overwrite if a journal CSV output file already exists in the "
        "output directory."
    ),
)
def main(
    root: Path,
    output_dir: Path,
    beamline: tuple[str, ...],
    cycle: str,
    max_workers: int,
    limit_per_worker: int,
    log_level: str,
    force: bool,
) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format=LOGGER_FORMAT,
    )

    beamlines = [item.upper() for item in beamline]
    output_dir = output_dir.resolve()
    should_skip_cycle_cb = (
        partial(_should_skip_cycle, output_dir=output_dir) if not force else None
    )
    summaries = collect_summaries(
        root,
        beamlines=beamlines,
        cycle_pattern=cycle,
        on_cycle_complete=partial(write_cycle_files, output=output_dir),
        should_skip_cycle=should_skip_cycle_cb,
        max_workers=max_workers,
        limit_per_worker=limit_per_worker,
    )

    click.echo(f"\nParsed {len(summaries)} run(s).", err=True)


if __name__ == "__main__":
    main()
