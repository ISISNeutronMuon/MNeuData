"""Tests for :mod:`isis_archive.facility`."""

from unittest.mock import patch

import pytest

from isis_archive import facility
from isis_archive.facility import (
    Beamline,
    FileNamingRule,
    beamlines,
)

FAKE_FACILITIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<facilities>
  <facility name="ISIS" zeropadding="5">
    <!-- Default facility zero padding -->
    <instrument name="BEAMLINEA"/>
    <!-- All runs use same padding -->
    <instrument name="BEAMLINEB" shortname="BMB">
    <zeropadding size="8"/>
    </instrument>
    <!--  -->
    <instrument name="BEAMLINEC" shortname="BMC">
      <zeropadding startRunNumber="10" prefix="BEAMLINEC"/>
      <zeropadding startRunNumber="20" size="8" prefix="BEAMLINEC"/>
    </instrument>
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
    def test_nexus_filename_zero_pads_run_number(self):
        beamline = Beamline("BEAMLINEA", [FileNamingRule(0, "BEAMLINEA", 5)])
        assert beamline.nexus_filename(42) == "BEAMLINEA00042.nxs"

    def test_nexus_filename_run_number_longer_than_padding(self):
        beamline = Beamline("BEAMLINEA", [FileNamingRule(0, "BEAMLINEA", 5)])
        assert beamline.nexus_filename(123456) == "BEAMLINEA123456.nxs"

    def test_nexus_filename_shortname(self):
        beamline = Beamline("BEAMLINEA", [FileNamingRule(0, "BMA", 5)])
        assert beamline.nexus_filename(123456) == "BMA123456.nxs"

    def test_nexus_filename_multiple_naming_rules(self):
        beamline = Beamline(
            "BEAMLINEA",
            [FileNamingRule(0, "BMA", 5), FileNamingRule(12345, "BMA", 8)],
        )
        assert beamline.nexus_filename(1) == "BMA00001.nxs"
        assert beamline.nexus_filename(1234) == "BMA01234.nxs"
        assert beamline.nexus_filename(12345) == "BMA00012345.nxs"


@pytest.mark.usefixtures("clear_beamlines_cache")
class TestBeamlines:
    def test_parses_downloaded_xml(self):
        with patch.object(
            facility, "_download_facilities_xml", return_value=FAKE_FACILITIES_XML
        ) as mock_download:
            result = beamlines()

        mock_download.assert_called_once_with()
        assert "BEAMLINEA" in result
        assert len(result["BEAMLINEA"].file_naming_rules) == 1
        assert result["BEAMLINEA"].file_naming_rules[0] == FileNamingRule(
            0, "BEAMLINEA", 5
        )

        assert "BEAMLINEB" in result
        assert len(result["BEAMLINEB"].file_naming_rules) == 1
        assert result["BEAMLINEB"].file_naming_rules[0] == FileNamingRule(0, "BMB", 8)

        assert "BEAMLINEC" in result
        assert len(result["BEAMLINEC"].file_naming_rules) == 3
        assert result["BEAMLINEC"].file_naming_rules[0] == FileNamingRule(0, "BMC", 5)
        assert result["BEAMLINEC"].file_naming_rules[1] == FileNamingRule(
            10, "BEAMLINEC", 5
        )
        assert result["BEAMLINEC"].file_naming_rules[2] == FileNamingRule(
            20, "BEAMLINEC", 8
        )

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
