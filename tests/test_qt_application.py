from __future__ import annotations

from pathlib import Path

import pytest

from test_core import write_game_fixture


@pytest.mark.parametrize("game", ("fp", "md", "se"))
def test_application_initializes_every_supported_game_fixture(
    tmp_path: Path, game: str
) -> None:
    from pu6e_qt.application import initialize_editor
    from U6 import Config
    import mapedit_gl as renderer

    game_dir = tmp_path / game
    write_game_fixture(game_dir, game, game)
    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {game_dir}\n"
        f"gametype = {game}\n"
        "width = 800\n"
        "height = 600\n"
        "zoom = 1.5\n"
    )

    controller = initialize_editor(config_path)

    assert controller is not None
    assert Config.gamedir == str(game_dir.resolve())
    assert Config.gametype == game
    assert controller.position == (0x134, 0x16C, 0)
    assert renderer.get_centered_coords() == (0x134, 0x16C, 0)
    assert renderer.screen_width == 800
    assert renderer.screen_height == 600
    assert renderer.scale_factor == 1.5


def test_application_rejects_missing_game_directory(tmp_path: Path) -> None:
    from pu6e_qt.application import GameDirectoryError, initialize_editor

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {tmp_path / 'missing'}\n"
        "gametype = fp\n"
        "width = 800\n"
        "height = 600\n"
        "zoom = 1\n"
    )

    with pytest.raises(GameDirectoryError):
        initialize_editor(config_path)


def test_application_rejects_missing_configuration_file(tmp_path: Path) -> None:
    from pu6e_qt.application import ConfigurationFileError, initialize_editor

    with pytest.raises(ConfigurationFileError):
        initialize_editor(tmp_path / "missing.conf")


def test_application_rejects_malformed_configuration_syntax(tmp_path: Path) -> None:
    from pu6e_qt.application import MalformedConfigurationError, read_configuration

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text("[pu6e\nwidth = 800\n")

    with pytest.raises(MalformedConfigurationError) as error:
        read_configuration(config_path)

    assert error.value.path == config_path
    assert error.value.cause
    assert "repair" in str(error.value).lower()


def test_application_rejects_missing_required_configuration_option(tmp_path: Path) -> None:
    from pu6e_qt.application import MalformedConfigurationError, read_configuration

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {tmp_path}\n"
        "gametype = fp\n"
        "height = 600\n"
        "zoom = 1\n"
    )

    with pytest.raises(MalformedConfigurationError) as error:
        read_configuration(config_path)

    assert error.value.path == config_path
    assert "width" in error.value.cause


@pytest.mark.parametrize(
    ("option", "value"),
    (("width", "wide"), ("height", "tall"), ("zoom", "near")),
)
def test_application_rejects_invalid_numeric_configuration(
    tmp_path: Path, option: str, value: str
) -> None:
    from pu6e_qt.application import MalformedConfigurationError, read_configuration

    config_path = tmp_path / "pu6e.conf"
    settings = {"width": "800", "height": "600", "zoom": "1"}
    settings[option] = value
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {tmp_path}\n"
        "gametype = fp\n"
        f"width = {settings['width']}\n"
        f"height = {settings['height']}\n"
        f"zoom = {settings['zoom']}\n"
    )

    with pytest.raises(MalformedConfigurationError) as error:
        read_configuration(config_path)

    assert error.value.path == config_path
    assert error.value.cause


def test_application_rejects_unsupported_game_type(tmp_path: Path) -> None:
    from pu6e_qt.application import GameTypeError, read_configuration

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {tmp_path}\n"
        "gametype = unknown\n"
        "width = 800\n"
        "height = 600\n"
        "zoom = 1\n"
    )

    with pytest.raises(GameTypeError) as error:
        read_configuration(config_path)

    assert error.value.game_type == "unknown"


@pytest.mark.parametrize(
    ("width", "height", "zoom"),
    (("0", "600", "1"), ("800", "-1", "1"), ("800", "600", "0")),
)
def test_application_rejects_nonpositive_display_configuration(
    tmp_path: Path, width: str, height: str, zoom: str
) -> None:
    from pu6e_qt.application import DisplayConfigurationError, read_configuration

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {tmp_path}\n"
        "gametype = fp\n"
        f"width = {width}\n"
        f"height = {height}\n"
        f"zoom = {zoom}\n"
    )

    with pytest.raises(DisplayConfigurationError):
        read_configuration(config_path)


def test_launcher_startup_surfaces_malformed_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets
    import pu6e_qt.application as application_module
    import pu6e_qt.canvas as canvas_module
    import pu6e_qt.theme as theme_module

    class StubApplication:
        def __init__(self, arguments: list[str]) -> None:
            self.arguments = arguments
            self.event_loop_entered = False

        def exec(self) -> int:
            self.event_loop_entered = True
            return 0

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text("[pu6e\n")
    applications: list[StubApplication] = []
    errors: list[tuple[None, str, str]] = []
    monkeypatch.setattr(application_module, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        QtWidgets,
        "QApplication",
        lambda arguments: applications.append(StubApplication(arguments)) or applications[-1],
    )
    monkeypatch.setattr(canvas_module, "configure_opengl_format", lambda: None)
    monkeypatch.setattr(theme_module, "apply_theme", lambda application: None)
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "critical",
        lambda parent, title, message: errors.append((parent, title, message)),
    )

    application_module.main()

    assert len(applications) == 1
    assert not applications[0].event_loop_entered
    assert len(errors) == 1
    assert errors[0][0] is None
    assert str(config_path) in errors[0][2]
    assert "repair" in errors[0][2].lower()
    assert config_path.read_text() == "[pu6e\n"


def test_launcher_startup_allows_missing_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets
    from pu6e_qt.game_profiles import GameProfileStore
    import pu6e_qt.application as application_module
    import pu6e_qt.canvas as canvas_module
    import pu6e_qt.launcher as launcher_module
    import pu6e_qt.theme as theme_module

    class StubApplication:
        def __init__(self, arguments: list[str]) -> None:
            self.arguments = arguments
            self.event_loop_entered = False

        def exec(self) -> int:
            self.event_loop_entered = True
            return 0

    class StubLauncher:
        def __init__(self, store: GameProfileStore) -> None:
            self.store = store
            self.shown = False

        def show(self) -> None:
            self.shown = True

    config_path = tmp_path / "missing.conf"
    applications: list[StubApplication] = []
    launchers: list[StubLauncher] = []
    errors: list[tuple[None, str, str]] = []
    monkeypatch.setattr(application_module, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        application_module.renderer_settings,
        "resolve_renderer",
        lambda renderer, _gpu: application_module.renderer_settings.RendererRuntime(
            renderer
        ),
    )
    monkeypatch.setattr(
        application_module.renderer_settings,
        "configure_renderer",
        lambda *_arguments: None,
    )
    monkeypatch.setattr(
        QtWidgets,
        "QApplication",
        lambda arguments: applications.append(StubApplication(arguments)) or applications[-1],
    )
    monkeypatch.setattr(canvas_module, "configure_opengl_format", lambda: None)
    monkeypatch.setattr(theme_module, "apply_theme", lambda application: None)
    monkeypatch.setattr(
        launcher_module,
        "LauncherWindow",
        lambda store, _runtime: launchers.append(StubLauncher(store)) or launchers[-1],
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "critical",
        lambda parent, title, message: errors.append((parent, title, message)),
    )

    application_module.main()

    assert len(applications) == 1
    assert applications[0].event_loop_entered
    assert len(launchers) == 1
    assert launchers[0].shown
    assert all(not launchers[0].store.profile(game).ready for game in ("fp", "md", "se"))
    assert errors == []
    assert not config_path.exists()


def test_application_package_import_is_wx_free() -> None:
    import importlib
    import sys

    importlib.import_module("pu6e")
    importlib.import_module("pu6e_qt.application")

    assert "wx" not in sys.modules
    assert "mapedit_wxgl" not in sys.modules
