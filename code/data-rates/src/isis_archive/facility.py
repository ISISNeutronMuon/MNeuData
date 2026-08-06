"""Use Mantid's facilities XML to pull information such as run number padding and filename prefixes"""

import functools
import logging
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import cast

logger = logging.getLogger("isis_archive")

FACILITIES_XML_URL = (
    "https://raw.githubusercontent.com/mantidproject/mantid/"
    "06a9427809cae45050cb6fbc07438f7f83f9186f/instrument/Facilities.xml"
)
ISIS = "ISIS"
NXS = ".nxs"


@dataclass(frozen=True)
class FileNamingRule:
    """Capture a rule defining how to construct a filename"""

    run_number_start: int
    prefix: str
    run_number_width: int


@dataclass(frozen=True)
class Beamline:
    ndx_suffix: str
    file_naming_rules: list[FileNamingRule]

    def nexus_filename(self, run_number: int) -> str:
        """Construct the filename for this beamline and run number"""
        for rule in reversed(self.file_naming_rules):
            if run_number >= rule.run_number_start:
                return f"{rule.prefix}{run_number:0{rule.run_number_width}d}{NXS}"

        raise ValueError(
            f"Logic error: A file naming rule should always match but none could be found for beamline {self.ndx_suffix} run number {run_number}"
            f"File naming rules: {self.file_naming_rules!r}"
        )


@functools.cache
def beamlines() -> dict[str, Beamline]:
    return _parse_facilities_xml(_download_facilities_xml(), facility_name=ISIS)


def find_nexus_file(
    beamline_dir: Path, cycle_suffix: str, ndx_suffix: str, run_number: int
) -> Path:
    """Locate the ``.nxs`` file for a run within its cycle data directory."""
    beamline = beamlines()[ndx_suffix]

    cycle_dir = beamline_dir / "Instrument" / "data" / f"cycle_{cycle_suffix}"

    try:
        filename = beamline.nexus_filename(run_number)
    except KeyError:
        raise FileNotFoundError(
            f"Beamline {ndx_suffix!r} is not defined in facilities.xml; "
            f" cannot determine NeXus filename for run "
            f"{run_number}"
        )
    candidate = cycle_dir / filename
    if candidate.is_file():
        logger.debug(f"Matched run {run_number} to {candidate}")
        return candidate

    raise FileNotFoundError(
        f"No NeXus file found in {cycle_dir} for {ndx_suffix} run {run_number} "
        f"(expected {filename})"
    )


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

    default_facility_padding = int(facility_el.get("zeropadding", "0"))
    return dict(
        _parse_instrument(inst_el, default_facility_padding)
        for inst_el in facility_el.findall("instrument")
    )


def _parse_instrument(
    inst_el: ET.Element,
    default_facility_padding: int,
) -> tuple[str, Beamline]:
    """Parse an instrument tag"""
    name = cast(str, inst_el.get("name"))
    default_file_prefix = inst_el.get("shortname", name)

    padding_rules = _build_file_naming_rules(
        inst_el.findall("zeropadding"),
        cast(str, default_file_prefix),
        default_facility_padding,
    )
    return name, Beamline(name, padding_rules)


def _build_file_naming_rules(
    zero_padding_els: list[ET.Element],
    default_file_prefix: str,
    default_facility_padding: int,
) -> list[FileNamingRule]:
    """Parse an instrument tag"""
    num_elements = len(zero_padding_els)
    rules = []
    for el in zero_padding_els:
        run_number_start = int(el.get("startRunNumber", "0"))
        run_number_width = int(el.get("size", default_facility_padding))
        prefix = el.get("prefix", default_file_prefix)
        rules.append(FileNamingRule(run_number_start, prefix, run_number_width))

    rules = sorted(rules, key=lambda r: r.run_number_start)
    # Ensure there is a rule starting at 0
    if num_elements == 0 or rules[0].run_number_start != 0:
        rules.insert(
            0, FileNamingRule(0, default_file_prefix, default_facility_padding)
        )

    return rules
