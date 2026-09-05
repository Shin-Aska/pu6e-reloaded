#!/usr/bin/env python3
"""pu6e application entry point."""

import sys
from pathlib import Path


def main() -> None:
    if sys.argv[1:2] == ["--renderer-probe"] and len(sys.argv) in (2, 3):
        from pu6e_qt.renderer_probe import main as probe_renderer

        raise SystemExit(probe_renderer(Path(sys.argv[2]) if len(sys.argv) == 3 else None))

    from pu6e_qt.application import main as qt_main

    qt_main()


if __name__ == "__main__":
    main()
