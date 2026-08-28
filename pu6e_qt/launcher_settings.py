from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from pu6e_qt.game_profiles import GameProfileStore
from pu6e_qt.launcher_style import launcher_gpu_list_stylesheet, launcher_stylesheet
from pu6e_qt.renderer_settings import RENDERER_MODES, RendererMode
from pu6e_qt.theme import THEME
from pu6e_qt.vulkan_devices import VulkanDevice, list_vulkan_devices


class _GpuItemDelegate(QStyledItemDelegate):
    def __init__(self, combo: QComboBox) -> None:
        super().__init__(combo)
        self.combo = combo

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        styled_option = QStyleOptionViewItem(option)
        if index.row() == self.combo.currentIndex():
            styled_option.state |= QStyle.StateFlag.State_Selected
            for group in (
                QPalette.ColorGroup.Active,
                QPalette.ColorGroup.Inactive,
                QPalette.ColorGroup.Disabled,
            ):
                styled_option.palette.setColor(
                    group,
                    QPalette.ColorRole.Highlight,
                    QColor(THEME.accent_wash),
                )
                styled_option.palette.setColor(
                    group,
                    QPalette.ColorRole.HighlightedText,
                    QColor(THEME.text_primary),
                )
        super().paint(painter, styled_option, index)


class LauncherSettingsDialog(QDialog):
    def __init__(
        self,
        store: GameProfileStore,
        parent: QWidget | None = None,
        *,
        vulkan_devices: Sequence[VulkanDevice] | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.vulkan_devices = tuple(
            list_vulkan_devices() if vulkan_devices is None else vulkan_devices
        )
        self.setObjectName("launcher-settings")
        self.setWindowTitle("Launcher settings")
        self.setMinimumWidth(500)
        self.setStyleSheet(launcher_stylesheet())

        title = QLabel("Renderer", self)
        title.setProperty("launcherRole", "gameTitle")
        intro = QLabel(
            "Choose how pu6e Reloaded presents the world map on this computer.",
            self,
        )
        intro.setWordWrap(True)

        renderer_label = QLabel("RENDERER", self)
        renderer_label.setProperty("launcherRole", "gameSetting")
        self.renderer_combo = QComboBox(self)
        self.renderer_combo.setAccessibleName("World map renderer")
        for renderer in RENDERER_MODES:
            self.renderer_combo.addItem(renderer.label)
        self.renderer_combo.setCurrentIndex(RENDERER_MODES.index(store.renderer))

        self.description_label = QLabel(self)
        self.description_label.setObjectName("configuration-status")
        self.description_label.setWordWrap(True)

        self.gpu_label = QLabel("VULKAN GPU", self)
        self.gpu_label.setProperty("launcherRole", "gameSetting")
        self.gpu_combo = QComboBox(self)
        self.gpu_combo.setAccessibleName("Vulkan graphics processor")
        self.gpu_combo.addItem("Automatic (recommended)")
        for device in self.vulkan_devices:
            self.gpu_combo.addItem(device.display_name)
        self.gpu_combo.view().setStyleSheet(launcher_gpu_list_stylesheet())
        self.gpu_combo.setItemDelegate(_GpuItemDelegate(self.gpu_combo))
        selected_gpu_index = next(
            (
                index
                for index, device in enumerate(self.vulkan_devices, start=1)
                if device.selector == store.vulkan_gpu
            ),
            0,
        )
        self.gpu_combo.setCurrentIndex(selected_gpu_index)
        self.gpu_guidance = QLabel(self)
        self.gpu_guidance.setObjectName("configuration-guidance")
        self.gpu_guidance.setWordWrap(True)
        if self.vulkan_devices:
            self.gpu_guidance.setText(
                "Automatic works for most systems. Choose a GPU to force Mesa Zink "
                "to use that adapter."
            )
        else:
            self.gpu_guidance.setText(
                "No Vulkan devices were detected. Vulkan will be checked again at startup."
            )
        restart = QLabel(
            "Saving a graphics change lets you restart now or continue until later.",
            self,
        )
        restart.setObjectName("configuration-guidance")
        restart.setWordWrap(True)

        cancel = QPushButton("Cancel", self)
        cancel.setProperty("launcherRole", "secondaryButton")
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Save settings", self)
        self.save_button.setProperty("launcherRole", "launchButton")
        self.save_button.clicked.connect(self._save)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_6,
            THEME.space_6,
            THEME.space_6,
            THEME.space_6,
        )
        layout.setSpacing(THEME.space_3)
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addSpacing(THEME.space_2)
        layout.addWidget(renderer_label)
        layout.addWidget(self.renderer_combo)
        layout.addWidget(self.description_label)
        layout.addWidget(self.gpu_label)
        layout.addWidget(self.gpu_combo)
        layout.addWidget(self.gpu_guidance)
        layout.addWidget(restart)
        layout.addSpacing(THEME.space_2)
        layout.addLayout(buttons)

        self.renderer_combo.currentIndexChanged.connect(self._show_description)
        self._show_description(self.renderer_combo.currentIndex())

    def _show_description(self, index: int) -> None:
        renderer = RENDERER_MODES[index]
        self.description_label.setText(renderer.description)
        show_gpu = renderer is RendererMode.VULKAN
        self.gpu_label.setVisible(show_gpu)
        self.gpu_combo.setVisible(show_gpu)
        self.gpu_guidance.setVisible(show_gpu)

    def _save(self) -> None:
        gpu_index = self.gpu_combo.currentIndex()
        vulkan_gpu = (
            None
            if gpu_index == 0
            else self.vulkan_devices[gpu_index - 1].selector
        )
        try:
            self.store.set_renderer_preferences(
                RENDERER_MODES[self.renderer_combo.currentIndex()],
                vulkan_gpu,
            )
        except OSError as error:
            detail = str(error) or error.__class__.__name__
            self.description_label.setText(
                f"Unable to save settings to {self.store.config_path}: {detail}. "
                "Check that the configuration file and its parent directory allow write access."
            )
            return
        self.accept()
