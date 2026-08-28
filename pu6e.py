#!/usr/bin/env python3
"""pu6e application entry point."""

import sys


def main() -> None:
    if sys.argv[1:] == ["--renderer-probe"]:
        from pu6e_qt.renderer_probe import main as probe_renderer

        raise SystemExit(probe_renderer())

    from pu6e_qt.application import main as qt_main

    qt_main()


if __name__ == "__main__":
    main()
