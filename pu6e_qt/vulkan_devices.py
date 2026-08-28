from __future__ import annotations

import ctypes
import ctypes.util
import configparser
import struct
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, NewType

VulkanDeviceSelector = NewType("VulkanDeviceSelector", str)

_VK_SUCCESS: Final = 0
_VK_STRUCTURE_TYPE_APPLICATION_INFO: Final = 0
_VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO: Final = 1
_VK_API_VERSION_1_0: Final = 1 << 22
_DEVICE_NAME_OFFSET: Final = 20
_DEVICE_NAME_SIZE: Final = 256
_PROPERTIES_BUFFER_SIZE: Final = 4096


class VulkanDeviceKind(StrEnum):
    OTHER = "Other"
    INTEGRATED = "Integrated"
    DISCRETE = "Discrete"
    VIRTUAL = "Virtual"
    CPU = "CPU"


@dataclass(frozen=True, slots=True)
class VulkanDevice:
    selector: VulkanDeviceSelector
    name: str
    kind: VulkanDeviceKind

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.kind.value})"


class _VkApplicationInfo(ctypes.Structure):
    _fields_ = (
        ("sType", ctypes.c_uint32),
        ("pNext", ctypes.c_void_p),
        ("pApplicationName", ctypes.c_char_p),
        ("applicationVersion", ctypes.c_uint32),
        ("pEngineName", ctypes.c_char_p),
        ("engineVersion", ctypes.c_uint32),
        ("apiVersion", ctypes.c_uint32),
    )


class _VkInstanceCreateInfo(ctypes.Structure):
    _fields_ = (
        ("sType", ctypes.c_uint32),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("pApplicationInfo", ctypes.POINTER(_VkApplicationInfo)),
        ("enabledLayerCount", ctypes.c_uint32),
        ("ppEnabledLayerNames", ctypes.POINTER(ctypes.c_char_p)),
        ("enabledExtensionCount", ctypes.c_uint32),
        ("ppEnabledExtensionNames", ctypes.POINTER(ctypes.c_char_p)),
    )


def parse_vulkan_device_selector(value: str) -> VulkanDeviceSelector | None:
    if value == "auto":
        return None
    try:
        vendor, device = value.split(":")
        vendor_id = int(vendor, 16)
        device_id = int(device, 16)
    except ValueError:
        return None
    return VulkanDeviceSelector(f"{vendor_id:x}:{device_id:x}")


def read_vulkan_gpu(config_path: Path) -> VulkanDeviceSelector | None:
    configuration = configparser.ConfigParser()
    try:
        configuration.read(config_path, encoding="utf-8")
    except configparser.Error:
        return None
    value = configuration.get("launcher", "vulkan_gpu", fallback="auto")
    return parse_vulkan_device_selector(value)


def _device_kind(value: int) -> VulkanDeviceKind:
    match value:
        case 1:
            return VulkanDeviceKind.INTEGRATED
        case 2:
            return VulkanDeviceKind.DISCRETE
        case 3:
            return VulkanDeviceKind.VIRTUAL
        case 4:
            return VulkanDeviceKind.CPU
        case _:
            return VulkanDeviceKind.OTHER


def _library_names() -> tuple[str, ...]:
    discovered = ctypes.util.find_library("vulkan")
    match sys.platform:
        case "win32":
            names = ("vulkan-1.dll", discovered)
        case "darwin":
            names = ("libvulkan.1.dylib", "libvulkan.dylib", discovered)
        case _:
            names = ("libvulkan.so.1", "libvulkan.so", discovered)
    return tuple(name for name in names if name is not None)


def _load_vulkan_library() -> ctypes.CDLL | None:
    for name in _library_names():
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    return None


def list_vulkan_devices() -> tuple[VulkanDevice, ...]:
    library = _load_vulkan_library()
    if library is None:
        return ()

    application_info = _VkApplicationInfo(
        _VK_STRUCTURE_TYPE_APPLICATION_INFO,
        None,
        b"pu6e-reloaded",
        0,
        b"pu6e-reloaded",
        0,
        _VK_API_VERSION_1_0,
    )
    create_info = _VkInstanceCreateInfo(
        _VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        None,
        0,
        ctypes.pointer(application_info),
        0,
        None,
        0,
        None,
    )
    instance = ctypes.c_void_p()
    library.vkCreateInstance.argtypes = (
        ctypes.POINTER(_VkInstanceCreateInfo),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    )
    library.vkCreateInstance.restype = ctypes.c_int32
    result = library.vkCreateInstance(
        ctypes.byref(create_info),
        None,
        ctypes.byref(instance),
    )
    if result != _VK_SUCCESS:
        return ()

    try:
        library.vkEnumeratePhysicalDevices.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p),
        )
        library.vkEnumeratePhysicalDevices.restype = ctypes.c_int32
        device_count = ctypes.c_uint32()
        result = library.vkEnumeratePhysicalDevices(
            instance,
            ctypes.byref(device_count),
            None,
        )
        if result != _VK_SUCCESS or device_count.value == 0:
            return ()
        handles = (ctypes.c_void_p * device_count.value)()
        result = library.vkEnumeratePhysicalDevices(
            instance,
            ctypes.byref(device_count),
            handles,
        )
        if result != _VK_SUCCESS:
            return ()

        library.vkGetPhysicalDeviceProperties.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        library.vkGetPhysicalDeviceProperties.restype = None
        devices: list[VulkanDevice] = []
        selectors: set[VulkanDeviceSelector] = set()
        for handle in handles:
            properties = ctypes.create_string_buffer(_PROPERTIES_BUFFER_SIZE)
            library.vkGetPhysicalDeviceProperties(handle, properties)
            _, _, vendor_id, device_id, device_type = struct.unpack_from(
                "=IIIII",
                properties.raw,
            )
            selector = VulkanDeviceSelector(f"{vendor_id:x}:{device_id:x}")
            if selector in selectors:
                continue
            selectors.add(selector)
            name_bytes = properties.raw[
                _DEVICE_NAME_OFFSET : _DEVICE_NAME_OFFSET + _DEVICE_NAME_SIZE
            ].split(b"\0", 1)[0]
            name = name_bytes.decode("utf-8", errors="replace") or selector
            devices.append(VulkanDevice(selector, name, _device_kind(device_type)))
        return tuple(devices)
    finally:
        library.vkDestroyInstance.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        library.vkDestroyInstance.restype = None
        library.vkDestroyInstance(instance, None)
