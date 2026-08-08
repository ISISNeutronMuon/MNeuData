import sys
from pathlib import Path

import click

from . import summarise_nexus


@click.command()
@click.argument("nexus_path", type=Path)
def main(nexus_path: Path):
    print(f"Summary of NeXus file '{nexus_path}'")
    print()
    print(summarise_nexus(nexus_path))


if __name__ == "__main__":
    main()
