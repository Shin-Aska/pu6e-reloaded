#!/usr/bin/env python3
"""pu6e application entry point."""


def main() -> None:
    from pu6e_qt.application import main as qt_main

    qt_main()


if __name__ == "__main__":
    main()
