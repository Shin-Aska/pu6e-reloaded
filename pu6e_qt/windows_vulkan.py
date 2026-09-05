from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pu6e_qt.vulkan_devices import VulkanDeviceSelector

_DISPLAY_CLASS: Final = (
    r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
)


def mesa_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "mesa"
    return Path(__file__).resolve().parents[1] / "build" / "mesa" / "runtime"


def vulkan_driver_manifest(selector: VulkanDeviceSelector | None) -> Path | None:
    if sys.platform != "win32" or not selector:
        return None
    import winreg

    vendor, device = (int(value, 16) for value in selector.split(":"))
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _DISPLAY_CLASS) as adapters:
        for index in range(winreg.QueryInfoKey(adapters)[0]):
            name = winreg.EnumKey(adapters, index)
            if not name.isdecimal():
                continue
            try:
                with winreg.OpenKey(adapters, name) as adapter:
                    hardware_id, hardware_type = winreg.QueryValueEx(adapter, "MatchingDeviceId")
                    if hardware_type != winreg.REG_SZ:
                        continue
                    match = re.search(r"VEN_([0-9a-f]+)&DEV_([0-9a-f]+)", hardware_id, re.I)
                    if match is None or (int(match[1], 16), int(match[2], 16)) != (vendor, device):
                        continue
                    filenames, value_type = winreg.QueryValueEx(adapter, "VulkanDriverName")
                    if value_type == winreg.REG_SZ:
                        filenames = [filenames]
                    elif value_type != winreg.REG_MULTI_SZ:
                        continue
                    for filename in filenames:
                        path = Path(filename)
                        if path.is_file():
                            return path
            except (FileNotFoundError, PermissionError):
                continue
    return None
