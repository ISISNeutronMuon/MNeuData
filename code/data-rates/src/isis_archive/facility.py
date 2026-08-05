"""Use Mantid's facilities XML to pull information such as run number padding and filename prefixes"""

import functools
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

FACILITIES_XML_URL = (
    "https://raw.githubusercontent.com/mantidproject/mantid/"
    "06a9427809cae45050cb6fbc07438f7f83f9186f/instrument/Facilities.xml"
)
ISIS = "ISIS"


@dataclass(frozen=True)
class ZeroPaddingRule:
    """A zero-padding/prefix override effective from ``start_run_number``."""

    start_run_number: int
    size: int
    prefix: str | None = None


@dataclass(frozen=True)
class Beamline:
    ndx_suffix: str
    padding_rules: tuple[ZeroPaddingRule, ...]
    extension: str = ".nxs"

    def nexus_filename(self, run_number) -> str:
        rule = self.padding_rules[0]
        prefix = rule.prefix if rule.prefix is not None else self.ndx_suffix
        size = rule.size
        return f"{prefix}{run_number:0{size}d}{self.extension}"


@functools.cache
def beamlines() -> dict[str, Beamline]:
    return _parse_facilities_xml(_download_facilities_xml(), facility_name=ISIS)


def nexus_filename(ndx_suffix: str, run_number: int) -> str:
    """Construct the nexus filename of the given beamline and run_number"""
    return beamlines()[ndx_suffix].nexus_filename(run_number)


def _download_facilities_xml(url: str = FACILITIES_XML_URL) -> str:
    """Download the ``Facilities.xml`` content from ``url``."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def _parse_facilities_xml(xml_content: str, facility_name) -> dict[str, Beamline]:
    """Parse the XML content and pull out relevant information"""
    root = ET.fromstring(xml_content)
    facility_el = next(
        (f for f in root.findall("facility") if f.get("name") == facility_name),
        None,
    )
    if facility_el is None:
        raise ValueError(f"Facility {facility_name!r} not found in Facilities.xml")

    default_padding = int(facility_el.get("zeropadding", "0"))
    return {"HRPD": Beamline("HRPD", (ZeroPaddingRule(0, default_padding, "HRP"),))}
