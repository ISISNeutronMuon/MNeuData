# /// script
# requires-python = ">=3.9"
# dependencies = ["h5py"]
# ///
"""Display raw and on-disk sizes of each group in an HDF5 file.

Usage: uv run hdf5_sizes.py FILE.h5
"""

import argparse
import os
from collections import defaultdict

import h5py


def human(n):
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="path to the HDF5 file")
    args = parser.parse_args()

    raw = defaultdict(int)
    disk = defaultdict(int)

    with h5py.File(args.path, "r") as f:

        def visit(name, obj):
            if not isinstance(obj, h5py.Dataset):
                return
            r = obj.size * obj.dtype.itemsize
            d = obj.id.get_storage_size()
            # Add to every ancestor group, including the root
            parts = name.split("/")[:-1]
            for i in range(len(parts) + 1):
                key = "/" + "/".join(parts[:i])
                raw[key] += r
                disk[key] += d

        raw["/"] = 0
        disk["/"] = 0
        f.visititems(visit)

    groups = sorted(raw)
    width = max(len("Group"), *(len(g) for g in groups))
    print(f"{'Group':<{width}}  {'Raw size':>12}  {'On-disk size':>12}")
    print(f"{'-' * width}  {'-' * 12}  {'-' * 12}")
    for g in groups:
        print(f"{g:<{width}}  {human(raw[g]):>12}  {human(disk[g]):>12}")
    print(f"{'-' * width}  {'-' * 12}  {'-' * 12}")
    print(f"{'TOTAL':<{width}}  {human(raw['/']):>12}  {human(disk['/']):>12}")
    print(f"\nFile size on disk (incl. metadata): {human(os.path.getsize(args.path))}")


if __name__ == "__main__":
    main()
