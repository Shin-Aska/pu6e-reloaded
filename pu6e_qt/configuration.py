from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import shutil

from PySide6.QtCore import QStandardPaths


def user_configuration_path() -> Path:
    directory = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericConfigLocation
    )
    return Path(directory) / "pu6e-reloaded" / "config.ini"


def migrate_legacy_configuration(destination: Path, legacy: Path) -> None:
    if destination.exists() or not legacy.is_file():
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, destination)

    configuration = ConfigParser()
    configuration.read(destination, encoding="utf-8")
    changed = False
    for section in configuration.sections():
        if section != "pu6e" and not section.startswith("game:"):
            continue
        directory = configuration.get(section, "gamedir", fallback="")
        if directory and not Path(directory).expanduser().is_absolute():
            configuration.set(section, "gamedir", str((legacy.parent / directory).resolve()))
            changed = True

    if changed:
        with destination.open("w", encoding="utf-8") as output:
            configuration.write(output)
