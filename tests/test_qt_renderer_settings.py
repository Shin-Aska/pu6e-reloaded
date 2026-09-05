from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from pu6e_qt.game_profiles import GameProfileStore
from pu6e_qt.renderer_settings import (
    RendererMode,
    RendererRuntime,
    VulkanDeviceSelector,
    configure_renderer,
    resolve_renderer,
)
from pu6e_qt.vulkan_devices import VulkanDevice, VulkanDeviceKind


@pytest.fixture(scope="session")
def launcher_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_renderer_defaults_to_vulkan_when_no_preference_exists(tmp_path: Path) -> None:
    # Given: a launcher configuration with no renderer preference.
    store = GameProfileStore(tmp_path / "config.ini")

    # When: the preference is read.
    renderer = store.renderer

    # Then: first-run startup prefers Vulkan with its safe fallback chain.
    assert renderer is RendererMode.VULKAN


@pytest.mark.parametrize("renderer", tuple(RendererMode))
def test_renderer_preference_persists_when_saved(
    tmp_path: Path, renderer: RendererMode
) -> None:
    # Given: a launcher configuration store.
    config_path = tmp_path / "config.ini"
    store = GameProfileStore(config_path)

    # When: a renderer is selected.
    store.set_renderer(renderer)

    # Then: both the file and a new store expose the selected renderer.
    saved = ConfigParser()
    saved.read(config_path)
    assert saved.get("launcher", "renderer") == renderer.value
    assert GameProfileStore(config_path).renderer is renderer


def test_renderer_preference_stays_unchanged_when_save_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a persisted renderer and a configuration file that cannot be updated.
    config_path = tmp_path / "config.ini"
    store = GameProfileStore(config_path)
    store.set_renderer(RendererMode.SOFTWARE)
    monkeypatch.setattr(store, "_write", lambda: (_ for _ in ()).throw(PermissionError()))

    # When: saving a different renderer fails.
    with pytest.raises(PermissionError):
        store.set_renderer(RendererMode.VULKAN)

    # Then: the current store and persisted preference remain on the saved renderer.
    assert store.renderer is RendererMode.SOFTWARE
    assert GameProfileStore(config_path).renderer is RendererMode.SOFTWARE


def test_vulkan_gpu_preference_persists_with_renderer(tmp_path: Path) -> None:
    # Given: a launcher configuration store with no graphics preferences.
    config_path = tmp_path / "config.ini"
    store = GameProfileStore(config_path)

    # When: Vulkan and a particular adapter are selected together.
    store.set_renderer_preferences(
        RendererMode.VULKAN,
        VulkanDeviceSelector("8086:46a6"),
    )

    # Then: both preferences are persisted and restored together.
    saved = ConfigParser()
    saved.read(config_path)
    restored = GameProfileStore(config_path)
    assert saved.get("launcher", "renderer") == RendererMode.VULKAN.value
    assert saved.get("launcher", "vulkan_gpu") == "8086:46a6"
    assert restored.renderer is RendererMode.VULKAN
    assert restored.vulkan_gpu == "8086:46a6"


@pytest.mark.parametrize(
    ("renderer", "software_vulkan"),
    (
        (RendererMode.SOFTWARE, False),
        (RendererMode.OPENGL, False),
        (RendererMode.VULKAN, False),
        (RendererMode.VULKAN, True),
    ),
)
def test_linux_renderer_configures_graphics_environment_before_qt_startup(
    monkeypatch: pytest.MonkeyPatch,
    renderer: RendererMode,
    software_vulkan: bool,
) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    # Given: graphics overrides inherited from another renderer mode.
    for name in (
        "QT_OPENGL",
        "LIBGL_ALWAYS_SOFTWARE",
        "GALLIUM_DRIVER",
        "MESA_LOADER_DRIVER_OVERRIDE",
        "QSG_RHI_BACKEND",
    ):
        monkeypatch.setenv(name, "stale")

    # When: the selected renderer is configured.
    configure_renderer(renderer, software_vulkan)

    # Then: Qt and Mesa receive one coherent backend configuration.
    import os

    expected = {
        (RendererMode.SOFTWARE, False): ("software", "1", "llvmpipe"),
        (RendererMode.OPENGL, False): ("desktop", None, None),
        (RendererMode.VULKAN, False): ("desktop", None, "zink"),
        (RendererMode.VULKAN, True): ("desktop", "1", "zink"),
    }
    qt_opengl, software, gallium = expected[(renderer, software_vulkan)]
    assert os.environ["QT_OPENGL"] == qt_opengl
    assert os.environ.get("LIBGL_ALWAYS_SOFTWARE") == software
    assert os.environ.get("GALLIUM_DRIVER") == gallium
    assert os.environ.get("MESA_LOADER_DRIVER_OVERRIDE") == (
        "zink" if renderer is RendererMode.VULKAN else None
    )
    assert os.environ.get("LIBGL_KOPPER_DRI2") == (
        "1" if renderer is RendererMode.VULKAN else None
    )
    assert os.environ.get("QSG_RHI_BACKEND") == (
        "vulkan" if renderer is RendererMode.VULKAN else None
    )


def test_vulkan_gpu_selection_is_forced_before_qt_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: Vulkan is configured with a selected discrete adapter.
    monkeypatch.delenv("MESA_VK_DEVICE_SELECT", raising=False)

    # When: the graphics environment is prepared before Qt starts.
    configure_renderer(
        RendererMode.VULKAN,
        False,
        VulkanDeviceSelector("1002:73bf"),
    )

    # Then: Mesa exposes only that adapter to Zink.
    import os

    assert os.environ["MESA_VK_DEVICE_SELECT"] == "1002:73bf!"


def test_vulkan_uses_cpu_backend_when_hardware_probe_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: unavailable hardware Vulkan and an available software Vulkan device.
    results = iter((False, True))
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings._probe_vulkan_environment",
        lambda _software, _gpu: next(results),
    )

    # When: the Vulkan runtime is resolved.
    runtime = resolve_renderer(RendererMode.VULKAN)

    # Then: Vulkan remains active through its CPU fallback with a visible notice.
    assert runtime.renderer is RendererMode.VULKAN
    assert runtime.software_vulkan
    assert runtime.notice is not None
    assert "CPU" in runtime.notice


def test_vulkan_falls_back_to_opengl_when_no_vulkan_backend_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: neither hardware nor software Vulkan can create a context.
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings._probe_vulkan_environment",
        lambda _software, _gpu: False,
    )

    # When: the Vulkan runtime is resolved.
    runtime = resolve_renderer(RendererMode.VULKAN)

    # Then: startup stays safe on OpenGL and explains the fallback.
    assert runtime.renderer is RendererMode.OPENGL
    assert not runtime.software_vulkan
    assert runtime.notice is not None
    assert "OpenGL" in runtime.notice


@pytest.mark.parametrize(
    ("runtime", "display_name"),
    (
        (RendererRuntime(RendererMode.SOFTWARE), "Software"),
        (RendererRuntime(RendererMode.OPENGL), "OpenGL"),
        (RendererRuntime(RendererMode.VULKAN), "Vulkan"),
        (RendererRuntime(RendererMode.VULKAN, software_vulkan=True), "Vulkan (CPU)"),
    ),
)
def test_resolved_renderer_has_an_unambiguous_display_name(
    runtime: RendererRuntime, display_name: str
) -> None:
    # Given: a renderer runtime that already reflects any startup fallback.
    # When: its end-user display name is requested.
    actual = runtime.display_name

    # Then: the name identifies the backend that is truly active.
    assert actual == display_name


def test_launcher_applies_saved_renderer_before_creating_qapplication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a saved software renderer preference and observable startup seams.
    from PySide6 import QtWidgets
    import pu6e_qt.application as application_module
    import pu6e_qt.canvas as canvas_module
    import pu6e_qt.launcher as launcher_module
    import pu6e_qt.renderer_settings as renderer_settings_module
    import pu6e_qt.theme as theme_module

    class StubApplication:
        def exec(self) -> int:
            return 0

    class StubLauncher:
        def __init__(
            self,
            _store: GameProfileStore,
            _runtime: RendererRuntime,
        ) -> None:
            pass

        def show(self) -> None:
            pass

    config_path = tmp_path / "config.ini"
    config_path.write_text("[launcher]\nrenderer = software\n")
    events: list[str] = []
    monkeypatch.setattr(application_module, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(
        renderer_settings_module,
        "configure_renderer",
        lambda renderer, _software, _gpu: events.append(f"renderer:{renderer.value}"),
    )
    monkeypatch.setattr(
        QtWidgets,
        "QApplication",
        lambda _arguments: events.append("application") or StubApplication(),
    )
    monkeypatch.setattr(canvas_module, "configure_opengl_format", lambda: None)
    monkeypatch.setattr(theme_module, "apply_theme", lambda _application: None)
    monkeypatch.setattr(launcher_module, "LauncherWindow", StubLauncher)

    # When: the launcher starts.
    application_module.main()

    # Then: the renderer is applied before Qt creates the application.
    assert events == ["renderer:software", "application"]


def test_launcher_settings_lists_and_saves_every_renderer(
    tmp_path: Path, launcher_app: QApplication
) -> None:
    # Given: the global launcher settings dialog.
    from pu6e_qt.launcher_settings import LauncherSettingsDialog

    store = GameProfileStore(tmp_path / "config.ini")
    dialog = LauncherSettingsDialog(store)

    # When: the renderer choices are inspected and Vulkan is saved.
    labels = tuple(dialog.renderer_combo.itemText(index) for index in range(3))
    dialog.renderer_combo.setCurrentIndex(2)
    dialog.save_button.click()

    # Then: all requested modes are available and Vulkan is persisted.
    assert labels == ("Software", "OpenGL", "Vulkan")
    assert store.renderer is RendererMode.VULKAN
    assert dialog.result() == dialog.DialogCode.Accepted


def test_launcher_settings_reveals_gpu_picker_only_for_vulkan(
    tmp_path: Path, launcher_app: QApplication
) -> None:
    # Given: launcher settings begin on a saved OpenGL renderer.
    from pu6e_qt.launcher_settings import LauncherSettingsDialog

    store = GameProfileStore(tmp_path / "config.ini")
    store.set_renderer(RendererMode.OPENGL)
    dialog = LauncherSettingsDialog(
        store,
        vulkan_devices=(),
    )

    # When: Vulkan is selected.
    assert dialog.gpu_combo.isHidden()
    dialog.renderer_combo.setCurrentIndex(2)

    # Then: the Vulkan-specific GPU picker becomes available.
    assert not dialog.gpu_combo.isHidden()


def test_launcher_settings_lists_and_saves_detected_vulkan_gpus(
    tmp_path: Path, launcher_app: QApplication
) -> None:
    # Given: Vulkan exposes an integrated and a discrete GPU.
    from pu6e_qt.launcher_settings import LauncherSettingsDialog

    devices = (
        VulkanDevice(
            VulkanDeviceSelector("8086:46a6"),
            "Intel Arc Graphics",
            VulkanDeviceKind.INTEGRATED,
        ),
        VulkanDevice(
            VulkanDeviceSelector("1002:73bf"),
            "AMD Radeon RX 6800",
            VulkanDeviceKind.DISCRETE,
        ),
    )
    store = GameProfileStore(tmp_path / "config.ini")
    dialog = LauncherSettingsDialog(store, vulkan_devices=devices)

    # When: the discrete adapter is selected and saved with Vulkan.
    dialog.renderer_combo.setCurrentIndex(2)
    labels = tuple(
        dialog.gpu_combo.itemText(index)
        for index in range(dialog.gpu_combo.count())
    )
    dialog.gpu_combo.setCurrentIndex(2)
    dialog.save_button.click()

    # Then: Automatic and both typed adapters are offered and the GPU is persisted.
    assert labels == (
        "Automatic (recommended)",
        "Intel Arc Graphics (Integrated)",
        "AMD Radeon RX 6800 (Discrete)",
    )
    assert store.renderer is RendererMode.VULKAN
    assert store.vulkan_gpu == VulkanDeviceSelector("1002:73bf")


def test_missing_saved_vulkan_gpu_falls_back_to_automatic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the saved discrete GPU has disappeared but another adapter remains.
    available = VulkanDevice(
        VulkanDeviceSelector("8086:46a6"),
        "Intel Arc Graphics",
        VulkanDeviceKind.INTEGRATED,
    )
    calls: list[tuple[bool, VulkanDeviceSelector | None]] = []
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings.list_vulkan_devices",
        lambda: (available,),
    )
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings._probe_vulkan_environment",
        lambda software, gpu: calls.append((software, gpu)) or True,
    )

    # When: Vulkan resolves the unavailable saved selection.
    runtime = resolve_renderer(
        RendererMode.VULKAN,
        VulkanDeviceSelector("1002:73bf"),
    )

    # Then: startup probes Automatic once and tells the user about the fallback.
    assert calls == [(False, None)]
    assert runtime.renderer is RendererMode.VULKAN
    assert runtime.vulkan_gpu is None
    assert runtime.notice is not None
    assert "no longer available" in runtime.notice


def test_selected_cpu_vulkan_device_uses_software_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the user explicitly selected a CPU Vulkan adapter.
    selector = VulkanDeviceSelector("10005:0")
    cpu_device = VulkanDevice(
        selector,
        "llvmpipe",
        VulkanDeviceKind.CPU,
    )
    calls: list[tuple[bool, VulkanDeviceSelector | None]] = []
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings.list_vulkan_devices",
        lambda: (cpu_device,),
    )
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings._probe_vulkan_environment",
        lambda software, gpu: calls.append((software, gpu)) or True,
    )

    # When: startup resolves that Vulkan selection.
    runtime = resolve_renderer(RendererMode.VULKAN, selector)

    # Then: it probes the requested CPU adapter in software mode without substitution.
    assert calls == [(True, selector)]
    assert runtime.software_vulkan
    assert runtime.vulkan_gpu == selector


def test_saved_vulkan_gpu_falls_back_when_enumeration_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: no Vulkan devices remain after a GPU selector was saved.
    calls: list[tuple[bool, VulkanDeviceSelector | None]] = []
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings.list_vulkan_devices",
        lambda: (),
    )
    monkeypatch.setattr(
        "pu6e_qt.renderer_settings._probe_vulkan_environment",
        lambda software, gpu: calls.append((software, gpu)) or True,
    )

    # When: startup resolves the stale selection.
    runtime = resolve_renderer(
        RendererMode.VULKAN,
        VulkanDeviceSelector("1002:73bf"),
    )

    # Then: Automatic is probed and the missing selection is explained.
    assert calls == [(False, None)]
    assert runtime.vulkan_gpu is None
    assert runtime.notice is not None
    assert "no longer available" in runtime.notice


def test_atlas_launcher_exposes_global_renderer_settings(
    tmp_path: Path, launcher_app: QApplication
) -> None:
    # Given: the Atlas launcher.
    from pu6e_qt.launcher import LauncherWindow

    launcher = LauncherWindow(
        GameProfileStore(tmp_path / "config.ini"),
        RendererRuntime(RendererMode.OPENGL),
    )

    # When: its global settings affordance is inspected.
    button = launcher.settings_button

    # Then: it is independently reachable and identifies renderer settings.
    assert button.isEnabled()
    assert "renderer" in button.accessibleName().lower()
    assert "settings" in button.toolTip().lower()
    launcher.close()


def test_launcher_title_identifies_the_active_renderer(
    tmp_path: Path, launcher_app: QApplication
) -> None:
    # Given: the launcher is running on the CPU Vulkan fallback.
    from pu6e_qt.launcher import LauncherWindow

    runtime = RendererRuntime(RendererMode.VULKAN, software_vulkan=True)

    # When: the native launcher window is created.
    launcher = LauncherWindow(GameProfileStore(tmp_path / "config.ini"), runtime)

    # Then: its title identifies the resolved backend without opening settings.
    assert launcher.windowTitle().endswith("[Renderer: Vulkan (CPU)]")
    launcher.close()
