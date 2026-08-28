from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QProcess
from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

from pu6e_qt.launcher_style import launcher_stylesheet


def build_renderer_restart_dialog(parent: QWidget | None = None) -> QMessageBox:
    dialog = QMessageBox(parent)
    dialog.setObjectName("renderer-restart-dialog")
    dialog.setIcon(QMessageBox.Icon.NoIcon)
    dialog.setWindowTitle("Restart required")
    dialog.setText("Restart required")
    dialog.setInformativeText(
        "Your new graphics settings are saved. Restart now to apply the new "
        "renderer, or choose Later to keep working with the current renderer."
    )
    restart_button = dialog.addButton(
        "Restart now",
        QMessageBox.ButtonRole.AcceptRole,
    )
    later_button = dialog.addButton("Later", QMessageBox.ButtonRole.RejectRole)
    assert isinstance(restart_button, QPushButton)
    assert isinstance(later_button, QPushButton)
    restart_button.setProperty("launcherRole", "launchButton")
    later_button.setProperty("launcherRole", "secondaryButton")
    dialog.setDefaultButton(restart_button)
    dialog.setEscapeButton(later_button)
    dialog.setStyleSheet(launcher_stylesheet())
    return dialog


def offer_renderer_restart(parent: QWidget | None = None) -> bool:
    dialog = build_renderer_restart_dialog(parent)
    restart_button = dialog.defaultButton()
    dialog.exec()
    return dialog.clickedButton() is restart_button


def restart_application() -> bool:
    result = QProcess.startDetached(sys.executable, sys.argv, str(Path.cwd()))
    started = result[0] if isinstance(result, tuple) else result
    if started:
        QCoreApplication.quit()
    return bool(started)
