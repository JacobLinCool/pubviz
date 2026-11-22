"""Command line: inspect a theme or a layout.

    pubviz roles amber            # every derived color, with its grey
    pubviz roles "#1A73D5" --mode gray
    pubviz layout paper/main.pubviz.json
"""

from __future__ import annotations

import argparse

from .layout import PRESETS, resolve
from .theme import Theme, describe


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="pubviz")
    sub = parser.add_subparsers(dest="command", required=True)
    roles = sub.add_parser("roles", help="print the colors derived from an accent")
    roles.add_argument("accent", nargs="?", default="amber", help="preset name or hex")
    roles.add_argument("--mode", default="color", choices=["color", "gray", "plain"])
    layout = sub.add_parser("layout", help="print a layout preset or a .pubviz.json file")
    layout.add_argument("source", help=f"preset ({', '.join(PRESETS)}) or file")
    args = parser.parse_args(argv)
    if args.command == "roles":
        theme = Theme(args.accent, args.mode)
        print(describe(theme))
        print()
        print("LaTeX:", theme.latex())
    else:
        lay, record = resolve(args.source)
        print(lay)
        if record:
            print("theme:", {k: record[k] for k in ("accent", "mode", "pos", "neg") if k in record})


if __name__ == "__main__":
    main()
