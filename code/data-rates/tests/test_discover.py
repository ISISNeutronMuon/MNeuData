"""Tests for :mod:`isis_archive.discover`.

Uses ``pyfakefs`` so no real filesystem is touched.
"""

from pathlib import Path

import pytest

from isis_archive.discover import (
    discover_beamline_dirs,
    discover_journals,
    discover_journals_for_beamline,
)
from isis_archive.models import DiscoveredJournal


def make_journal_dir(fs, root: Path, beamline: str) -> Path:
    """Create ``NDX{beamline}/Instrument/logs/journal`` and return it."""
    journal_dir = root / f"NDX{beamline}" / "Instrument" / "logs" / "journal"
    fs.create_dir(journal_dir)
    return journal_dir


def make_instrument_only(fs, root: Path, beamline: str) -> Path:
    """Create ``NDX{beamline}/Instrument`` (no journal dir) and return the beamline dir."""
    beamline_dir = root / f"NDX{beamline}"
    fs.create_dir(beamline_dir / "Instrument")
    return beamline_dir


@pytest.fixture
def root() -> Path:
    return Path("/archive")


class TestDiscoverJournals:
    def test_yields_discovered_journal_for_each_file(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")
        fs.create_file(journal_dir / "journal_20_1.xml")

        results = list(discover_journals(root, ["GEM"]))

        assert len(results) == 2
        assert all(isinstance(r, DiscoveredJournal) for r in results)
        assert {r.path.name for r in results} == {
            "journal_19_4.xml",
            "journal_20_1.xml",
        }

    def test_populates_beamline_context(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")

        (result,) = list(discover_journals(root, ["GEM"]))

        assert result.beamline == "GEM"
        assert result.beamline_dir == root / "NDXGEM"
        assert result.path == journal_dir / "journal_19_4.xml"

    def test_results_sorted_reverse(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")
        fs.create_file(journal_dir / "journal_20_1.xml")
        fs.create_file(journal_dir / "journal_18_2.xml")

        names = [r.path.name for r in discover_journals(root, ["GEM"])]

        assert names == [
            "journal_20_1.xml",
            "journal_19_4.xml",
            "journal_18_2.xml",
        ]

    def test_multiple_beamlines_processed_in_order(self, fs, root):
        gem_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(gem_dir / "journal_19_4.xml")
        wish_dir = make_journal_dir(fs, root, "WISH")
        fs.create_file(wish_dir / "journal_20_1.xml")

        results = list(discover_journals(root, ["GEM", "WISH"]))

        assert [r.beamline for r in results] == ["GEM", "WISH"]

    def test_skips_beamline_missing_instrument(self, fs, root):
        # NDXNONE exists but has no Instrument subdir.
        fs.create_dir(root / "NDXNONE")
        gem_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(gem_dir / "journal_19_4.xml")

        results = list(discover_journals(root, ["NONE", "GEM"]))

        assert [r.beamline for r in results] == ["GEM"]

    def test_beamline_dir_completely_absent(self, fs, root):
        fs.create_dir(root)

        results = list(discover_journals(root, ["MISSING"]))

        assert results == []

    def test_instrument_present_but_no_journal_dir(self, fs, root):
        make_instrument_only(fs, root, "GEM")

        results = list(discover_journals(root, ["GEM"]))

        assert results == []

    def test_journal_dir_empty(self, fs, root):
        make_journal_dir(fs, root, "GEM")

        results = list(discover_journals(root, ["GEM"]))

        assert results == []

    def test_empty_beamlines_list(self, fs, root):
        fs.create_dir(root)

        results = list(discover_journals(root, []))

        assert results == []

    def test_non_matching_files_ignored(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")
        fs.create_file(journal_dir / "notes.txt")
        fs.create_file(journal_dir / "journal_main.xml")  # doesn't match ??_?

        names = [r.path.name for r in discover_journals(root, ["GEM"])]

        assert names == ["journal_19_4.xml"]


class TestCyclePattern:
    def test_cycle_pattern_selects_single_cycle(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")
        fs.create_file(journal_dir / "journal_20_1.xml")

        names = [
            r.path.name
            for r in discover_journals(root, ["GEM"], cycle_pattern="19_4")
        ]

        assert names == ["journal_19_4.xml"]

    def test_cycle_pattern_with_wildcard(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")
        fs.create_file(journal_dir / "journal_19_1.xml")
        fs.create_file(journal_dir / "journal_20_1.xml")

        names = [
            r.path.name
            for r in discover_journals(root, ["GEM"], cycle_pattern="19_*")
        ]

        assert names == ["journal_19_4.xml", "journal_19_1.xml"]

    def test_cycle_pattern_no_match(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")

        results = list(
            discover_journals(root, ["GEM"], cycle_pattern="99_9")
        )

        assert results == []


class TestDiscoverBeamlineDirs:
    def test_yields_name_and_dir(self, fs, root):
        make_instrument_only(fs, root, "GEM")

        (result,) = list(discover_beamline_dirs(root, ["GEM"]))

        assert result == ("GEM", root / "NDXGEM")

    def test_skips_missing_instrument(self, fs, root):
        fs.create_dir(root / "NDXGEM")  # no Instrument

        results = list(discover_beamline_dirs(root, ["GEM"]))

        assert results == []


class TestDiscoverJournalsForBeamline:
    def test_returns_paths(self, fs, root):
        journal_dir = make_journal_dir(fs, root, "GEM")
        fs.create_file(journal_dir / "journal_19_4.xml")
        beamline_dir = root / "NDXGEM"

        results = list(discover_journals_for_beamline(beamline_dir))

        assert results == [journal_dir / "journal_19_4.xml"]

    def test_missing_journal_dir_returns_nothing(self, fs, root):
        beamline_dir = make_instrument_only(fs, root, "GEM")

        results = list(discover_journals_for_beamline(beamline_dir))

        assert results == []
