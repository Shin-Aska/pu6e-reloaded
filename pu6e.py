#!/usr/bin/env python3
"""pu6e application entry point."""


def main() -> None:
    """Start the wxPython map editor."""
    import mapedit_wxgl

    mapedit_wxgl._main()


if __name__ == "__main__":
    main()
