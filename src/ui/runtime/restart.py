from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QProcess


def restart_application() -> bool:
    result = QProcess.startDetached(sys.executable, sys.argv, str(Path.cwd()))
    started = result[0]
    if started:
        QCoreApplication.quit()
    return bool(started)
