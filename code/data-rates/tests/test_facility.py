"""Tests for :mod:`isis_archive.facility`."""

from unittest.mock import patch

import pytest

from isis_archive import facility
from isis_archive.facility import (
    Beamline,
    ZeroPaddingRule,
    _parse_facilities_xml,
    beamlines,
    nexus_filename,
)

FAKE_FACILITIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<facilities>
  <facility name="ISIS" zeropadding="5">
    <instrument name="BEAMLINE1" shortname="BM1"/>
  </facility>
</facilities>
"""


@pytest.fixture
def clear_beamlines_cache():
    """Ensure the ``beamlines`` cache is empty before and after the test."""
    beamlines.cache_clear()
    yield
    beamlines.cache_clear()


class TestBeamline:
    def test_extension_defaults_to_nxs(self):
        beamline = Beamline("BEAMLINE1", (ZeroPaddingRule(0, 5),))
        assert beamline.extension == ".nxs"

    def test_nexus_filename_zero_pads_run_number(self):
        beamline = Beamline("BEAMLINE1", (ZeroPaddingRule(0, 5),))
        assert beamline.nexus_filename(42) == "BEAMLINE100042.nxs"

    def test_nexus_filename_uses_custom_extension(self):
        beamline = Beamline("BEAMLINE1", (ZeroPaddingRule(0, 5),), extension=".raw")
        assert beamline.nexus_filename(42) == "BEAMLINE100042.raw"

    def test_nexus_filename_run_number_longer_than_padding(self):
        beamline = Beamline("BEAMLINE1", (ZeroPaddingRule(0, 5),))
        assert beamline.nexus_filename(123456) == "BEAMLINE1123456.nxs"

    def test_nexus_filename_shortname(self):
        beamline = Beamline("BEAMLINE1", (ZeroPaddingRule(0, 5, "BM1"),))
        assert beamline.nexus_filename(123456) == "BM1123456.nxs"


class TestParseFacilitiesXml:
    def test_returns_expected_beamlines(self):
        result = _parse_facilities_xml(FAKE_FACILITIES_XML, facility_name="ISIS")
        assert "BM1" in result
        assert isinstance(result["BM1"], Beamline)

    # def test_uses_facility_zeropadding(self):
    #     result = _parse_facilities_xml(FAKE_FACILITIES_XML, facility_name="ISIS")
    #     (rule,) = result["HRPD"].padding_rules
    #     assert rule.size == 5

    # def test_selects_correct_facility(self):
    #     result = _parse_facilities_xml(FAKE_FACILITIES_XML, facility_name="SNS")
    #     (rule,) = result["HRPD"].padding_rules
    #     assert rule.size == 6

    def test_unknown_facility_raises(self):
        with pytest.raises(ValueError, match="NOPE"):
            _parse_facilities_xml(FAKE_FACILITIES_XML, facility_name="NOPE")


@pytest.mark.usefixtures("clear_beamlines_cache")
class TestBeamlines:
    def test_parses_downloaded_xml(self):
        with patch.object(
            facility, "_download_facilities_xml", return_value=FAKE_FACILITIES_XML
        ) as mock_download:
            result = beamlines()

        mock_download.assert_called_once_with()
        assert "HRPD" in result

    def test_returns_beamline_instances(self):
        with patch.object(
            facility, "_download_facilities_xml", return_value=FAKE_FACILITIES_XML
        ):
            result = beamlines()

        assert all(isinstance(b, Beamline) for b in result.values())

    def test_result_is_cached_download_called_once(self):
        with patch.object(
            facility, "_download_facilities_xml", return_value=FAKE_FACILITIES_XML
        ) as mock_download:
            first = beamlines()
            second = beamlines()

        assert first is second
        mock_download.assert_called_once_with()


@pytest.mark.usefixtures("clear_beamlines_cache")
class TestNexusFilename:
    def test_builds_filename_for_known_beamline(self):
        with patch.object(
            facility, "_download_facilities_xml", return_value=FAKE_FACILITIES_XML
        ):
            assert nexus_filename("HRPD", 42) == "HRP00042.nxs"
