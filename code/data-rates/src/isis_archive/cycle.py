"""Utility code for dealing with cycles"""

import re

CYCLE_ID_RE = re.compile(r"^[\d\?]{2}_[\d\?]$")
