# Third-party notices

pu6e Reloaded is licensed under `GPL-2.0-or-later`. Its dependencies remain
under their own licenses; installing this project does not relicense those
dependencies.

## Qt for Python: PySide6 and Shiboken6

- Projects: <https://doc.qt.io/qtforpython-6/> and
  <https://doc.qt.io/qt-6/>.
- Installed package families: `PySide6`, `PySide6-Essentials`,
  `PySide6-Addons`, and `shiboken6`.
- The package metadata inspected for version 6.11.2 declares these
  alternatives:
  `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`.
- Qt's general documentation describes the community edition as
  LGPLv3/GPLv3 and notes that licensing varies by module and bundled
  third-party component.
- Relevant upstream guidance:
  [Qt licensing](https://doc.qt.io/qt-6/licensing.html),
  [Qt for Python third-party licenses](https://doc.qt.io/qtforpython-6/licenses.html),
  and [Qt software bills of materials](https://doc.qt.io/qt-6/sbom.html).

The original project's `GPL-2.0-or-later` grant permits GPLv2 distribution
when every included Qt component offers a compatible GPLv2 option. If an
included component instead requires LGPLv3 or GPLv3, distribute the combined
work under GPLv3 using the original license's "or later" permission and comply
with the applicable Qt terms. Verify the actual Qt modules, wheel versions,
bundled components, and redistribution method before shipping a packaged
application; do not assume that every Qt module offers the same choices.

## NumPy

- Project: <https://numpy.org/>.
- Main project license: BSD 3-Clause.
- The installed NumPy 2.5.2 wheel additionally declares bundled permissive
  components under `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.
- Upstream license: <https://numpy.org/doc/stable/license.html>.

Retain applicable copyright and license notices when redistributing NumPy or
its bundled components.

## PyOpenGL

- Project: <https://github.com/mcfletch/pyopengl>.
- License: BSD-style, with additional upstream notices for included code.
- Upstream license and component notices:
  <https://github.com/mcfletch/pyopengl/blob/master/license.txt>.

Retain the applicable upstream notices when redistributing PyOpenGL.

## Mesa Zink and Lavapipe (Windows packages)

- Project: <https://www.mesa3d.org/>.
- Windows binaries: Mesa 26.2.2 from
  <https://github.com/mmozeiko/build-mesa/releases/tag/26.2.2>.
- Zink translates OpenGL to Vulkan; Lavapipe provides software Vulkan rendering.
- Mesa's core uses the MIT license; individual components have their own terms.
  The matching source distribution's `docs/license.rst` and complete `licenses/`
  directory are included under `mesa/licenses/mesa-26.2.2/` in the application
  runtime directory.
- Lavapipe includes LLVM 23.1.0. Its Apache-2.0 license with LLVM exceptions and
  legacy notices are included as `mesa/licenses/llvm-23.1.0/LICENSE.TXT`.
- Matching upstream sources:
  <https://archive.mesa3d.org/mesa-26.2.2.tar.xz> and
  <https://github.com/llvm/llvm-project/tree/llvmorg-23.1.0>.
- The binary builder and its dependency configuration are recorded at
  <https://github.com/mmozeiko/build-mesa/tree/26.2.2>.

The packaging script downloads these pinned binaries and upstream license
resources, verifies their SHA-256 checksums, and includes the license texts
alongside the drivers. In the portable package the runtime directory is
`_internal`; the standalone executable extracts its runtime when launched.

## Vulkan loader (Windows packages)

- Project: <https://github.com/KhronosGroup/Vulkan-Loader>.
- Binary: the x64 `vulkan-1.dll` from LunarG's Vulkan Runtime 1.4.357.0
  [components archive](https://sdk.lunarg.com/sdk/download/1.4.357.0/windows/VulkanRT-X64-1.4.357.0-Components.zip).
- The loader is bundled under `mesa/vulkan-1.dll` so software Vulkan rendering
  does not require a separately installed Vulkan runtime.
- The archive's `VulkanRT-License.txt` contains the upstream copyright and MIT
  notices and Apache-2.0 attribution. It is included with the full Apache-2.0
  license under `mesa/licenses/vulkan-1.4.357.0/` in the application runtime.
- Release and published checksum: <https://vulkan.lunarg.com/sdk/home>.

## Proprietary game assets

The supported games, their artwork, game files, saved games, names, and
trademarks remain subject to their respective owners' terms. No original game
assets are distributed with pu6e Reloaded.
