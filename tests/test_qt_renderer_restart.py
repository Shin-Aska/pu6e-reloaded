from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QProcess
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget

from pu6e_qt.game_profiles import GameProfileStore
from pu6e_qt.renderer_settings import RendererMode, RendererRuntime
from pu6e_qt.vulkan_devices import VulkanDeviceSelector


@pytest.fixture(scope="session")
def launcher_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_renderer_change_offers_later_without_restarting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
) -> None:
    # Given: launcher settings will save a renderer different from the current one.
    import pu6e_qt.launcher as launcher_module

    store = GameProfileStore(tmp_path / "config.ini")
    prompts: list[launcher_module.LauncherWindow] = []
    restarts: list[bool] = []

    class StubSettingsDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, settings_store: GameProfileStore, _parent: QWidget) -> None:
            self.store = settings_store

        def exec(self) -> QDialog.DialogCode:
            self.store.set_renderer(RendererMode.SOFTWARE)
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(launcher_module, "LauncherSettingsDialog", StubSettingsDialog)
    monkeypatch.setattr(
        launcher_module,
        "offer_renderer_restart",
        lambda parent: prompts.append(parent) or False,
        raising=False,
    )
    monkeypatch.setattr(
        launcher_module,
        "restart_application",
        lambda: restarts.append(True) or True,
        raising=False,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *_arguments: None)
    launcher = launcher_module.LauncherWindow(
        store,
        RendererRuntime(RendererMode.VULKAN),
    )

    # When: the user saves settings and chooses Later.
    launcher.configure_launcher()

    # Then: the restart choice was offered without terminating this launcher.
    assert prompts == [launcher]
    assert restarts == []
    launcher.close()


def test_renderer_change_restarts_when_restart_now_is_chosen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
) -> None:
    # Given: changed renderer settings and a successful detached relaunch seam.
    import pu6e_qt.launcher as launcher_module

    store = GameProfileStore(tmp_path / "config.ini")
    restarts: list[bool] = []

    class StubSettingsDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, settings_store: GameProfileStore, _parent: QWidget) -> None:
            self.store = settings_store

        def exec(self) -> QDialog.DialogCode:
            self.store.set_renderer(RendererMode.OPENGL)
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(launcher_module, "LauncherSettingsDialog", StubSettingsDialog)
    monkeypatch.setattr(
        launcher_module,
        "offer_renderer_restart",
        lambda _parent: True,
        raising=False,
    )
    monkeypatch.setattr(
        launcher_module,
        "restart_application",
        lambda: restarts.append(True) or True,
        raising=False,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *_arguments: None)
    launcher = launcher_module.LauncherWindow(
        store,
        RendererRuntime(RendererMode.VULKAN),
    )

    # When: the user chooses Restart now.
    launcher.configure_launcher()

    # Then: the detached relaunch path is invoked exactly once.
    assert restarts == [True]
    launcher.close()


def test_vulkan_gpu_change_offers_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
) -> None:
    # Given: Vulkan remains selected while its GPU preference changes.
    import pu6e_qt.launcher as launcher_module

    store = GameProfileStore(tmp_path / "config.ini")
    prompts: list[launcher_module.LauncherWindow] = []

    class StubSettingsDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, settings_store: GameProfileStore, _parent: QWidget) -> None:
            self.store = settings_store

        def exec(self) -> QDialog.DialogCode:
            self.store.set_renderer_preferences(
                RendererMode.VULKAN,
                VulkanDeviceSelector("1002:73bf"),
            )
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(launcher_module, "LauncherSettingsDialog", StubSettingsDialog)
    monkeypatch.setattr(
        launcher_module,
        "offer_renderer_restart",
        lambda parent: prompts.append(parent) or False,
    )
    launcher = launcher_module.LauncherWindow(
        store,
        RendererRuntime(RendererMode.VULKAN),
    )

    # When: the GPU-only change is saved.
    launcher.configure_launcher()

    # Then: applying that Vulkan device selection is offered through restart.
    assert prompts == [launcher]
    launcher.close()


def test_restart_application_quits_only_after_replacement_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the operating system accepts a detached replacement process.
    from pu6e_qt.application_restart import restart_application

    launches: list[tuple[str, tuple[str, ...], str]] = []
    quits: list[bool] = []
    monkeypatch.setattr(
        QProcess,
        "startDetached",
        lambda program, arguments, directory: (
            launches.append((program, tuple(arguments), directory)) or True,
            42,
        ),
    )
    monkeypatch.setattr(
        QCoreApplication,
        "quit",
        lambda: quits.append(True),
    )

    # When: a restart is requested.
    restarted = restart_application()

    # Then: the exact command is detached before the current Qt process quits.
    assert restarted
    assert launches == [(sys.executable, tuple(sys.argv), str(Path.cwd()))]
    assert quits == [True]


def test_restart_application_keeps_current_process_when_relaunch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the operating system rejects the detached replacement process.
    from pu6e_qt.application_restart import restart_application

    quits: list[bool] = []
    monkeypatch.setattr(
        QProcess,
        "startDetached",
        lambda _program, _arguments, _directory: (False, 0),
    )
    monkeypatch.setattr(QCoreApplication, "quit", lambda: quits.append(True))

    # When: a restart is requested.
    restarted = restart_application()

    # Then: the live launcher remains open so the user can recover manually.
    assert not restarted
    assert quits == []


def test_restart_prompt_offers_restart_now_and_later(
    launcher_app: QApplication,
) -> None:
    # Given: a renderer change needs a restart decision.
    from pu6e_qt.application_restart import build_renderer_restart_dialog

    # When: the native restart prompt is created.
    dialog = build_renderer_restart_dialog()

    # Then: its two actions describe the immediate and deferred choices.
    assert dialog.icon() is QMessageBox.Icon.NoIcon
    assert dialog.text() == "Restart required"
    assert [button.text() for button in dialog.buttons()] == ["Restart now", "Later"]
    assert dialog.defaultButton() is dialog.buttons()[0]
    dialog.close()
