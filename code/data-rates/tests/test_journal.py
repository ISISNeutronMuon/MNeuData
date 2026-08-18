"""Tests for :func:`isis_archive.journal.parse_journal`."""

from pathlib import Path

import pytest

from isis_archive.journal import JOURNAL_NAMESPACE, parse_journal
from isis_archive.models import JournalEntry

NS = JOURNAL_NAMESPACE

# Scalar journal fields (name -> text value) that must appear in every NXentry.
# ``number_time_channels`` is handled separately via IXtime_regime blocks and
# ``filename`` is set from the file path, so neither appears here.
_SCALAR_FIELDS: dict[str, str] = {
    "experiment_identifier": "12345",
    "run_number": "62260",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-01T01:00:00",
    "duration": "3600",
    "proton_charge": "1234.5",
    "raw_frames": "1000",
    "good_frames": "999",
    "total_mevents": "42.0",
    "event_mode": "1.0",
    "number_periods": "1",
    "number_time_regimes": "1",
    "number_spectra": "100",
    "number_detectors": "50",
    "frame_sync": "smp",
    "title": "A test run",
}


def _entry_xml(fields: dict[str, str], time_channels: list[str]) -> str:
    """Build a single ``NXentry`` block with the given scalar fields."""
    lines = ["<NXentry>"]
    for name, value in fields.items():
        lines.append(f"<{name}>{value}</{name}>")
    for channels in time_channels:
        lines.append(
            "<IXtime_regime>"
            f"<number_time_channels>{channels}</number_time_channels>"
            "</IXtime_regime>"
        )
    lines.append("</NXentry>")
    return "\n".join(lines)


def _write_journal(
    path: Path,
    entries: list[tuple[dict[str, str], list[str]]],
) -> Path:
    """Write a journal XML file containing the given entries; return the path."""
    body = "\n".join(_entry_xml(fields, channels) for fields, channels in entries)
    xml = f'<NXroot xmlns="{NS}">\n{body}\n</NXroot>\n'
    path.write_text(xml)
    return path


def _default_entries(
    n: int = 1,
) -> list[tuple[dict[str, str], list[str]]]:
    return [(dict(_SCALAR_FIELDS), ["2000"]) for _ in range(n)]


def test_scalar_fields_converted_to_correct_types(tmp_path: Path):
    journal = _write_journal(tmp_path / "journal_24_1.xml", _default_entries(1))

    entries = list(parse_journal(journal))
    (entry,) = entries

    assert len(entries) == 1
    assert isinstance(entries[0], JournalEntry)
    assert entry.experiment_identifier == 12345
    assert entry.run_number == 62260
    assert entry.duration == 3600
    assert entry.proton_charge == pytest.approx(1234.5)
    assert entry.total_mevents == pytest.approx(42.0)
    assert entry.start_time == "2024-01-01T00:00:00"
    assert entry.frame_sync == "smp"
    assert entry.title == "A test run"


def test_filename_is_set_from_path(tmp_path: Path):
    journal = _write_journal(tmp_path / "journal_24_1.xml", _default_entries(1))

    (entry,) = parse_journal(journal)

    assert entry.filename == "journal_24_1.xml"


def test_number_time_channels_collected_as_list(tmp_path: Path):
    entries = [(dict(_SCALAR_FIELDS), ["2000", "4000", "8000"])]
    journal = _write_journal(tmp_path / "journal_24_1.xml", entries)

    (entry,) = parse_journal(journal)

    assert entry.number_time_channels == [2000, 4000, 8000]


def test_no_time_regimes_gives_empty_list(tmp_path: Path):
    entries = [(dict(_SCALAR_FIELDS), [])]
    journal = _write_journal(tmp_path / "journal_24_1.xml", entries)

    (entry,) = parse_journal(journal)

    assert entry.number_time_channels == []


def test_parses_multiple_entries(tmp_path: Path):
    first = dict(_SCALAR_FIELDS, run_number="1")
    second = dict(_SCALAR_FIELDS, run_number="2")
    journal = _write_journal(
        tmp_path / "journal_24_1.xml",
        [(first, ["2000"]), (second, ["2000"])],
    )

    entries = list(parse_journal(journal))

    assert [e.run_number for e in entries] == [1, 2]


def test_returns_iterator_lazily(tmp_path: Path):
    journal = _write_journal(tmp_path / "journal_24_1.xml", _default_entries(2))

    result = parse_journal(journal)

    # It is a generator, not a materialised list.
    assert next(result).run_number == 62260


def test_empty_root_yields_nothing(tmp_path: Path):
    path = tmp_path / "journal_24_1.xml"
    path.write_text(f'<NXroot xmlns="{NS}"></NXroot>\n')

    assert list(parse_journal(path)) == []


def test_malformed_xml_yields_nothing(tmp_path: Path):
    path = tmp_path / "journal_24_1.xml"
    path.write_text("<NXroot><NXentry></oops>")

    assert list(parse_journal(path)) == []


def test_missing_field_raises_value_error(tmp_path: Path):
    fields = dict(_SCALAR_FIELDS)
    del fields["run_number"]
    journal = _write_journal(tmp_path / "journal_24_1.xml", [(fields, ["2000"])])

    with pytest.raises(ValueError, match="Missing journal field entry run_number"):
        list(parse_journal(journal))


def test_empty_field_value_raises_value_error(tmp_path: Path):
    fields = dict(_SCALAR_FIELDS, run_number="")
    # An empty element (<run_number></run_number>) has text ``None``.
    journal = _write_journal(tmp_path / "journal_24_1.xml", [(fields, ["2000"])])

    with pytest.raises(ValueError, match="empty value"):
        list(parse_journal(journal))


def test_non_numeric_value_raises_value_error(tmp_path: Path):
    fields = dict(_SCALAR_FIELDS, run_number="not-an-int")
    journal = _write_journal(tmp_path / "journal_24_1.xml", [(fields, ["2000"])])

    with pytest.raises(ValueError, match="Could not convert"):
        list(parse_journal(journal))
