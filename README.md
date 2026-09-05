# pu6e Reloaded

A modern, native desktop world editor for *Ultima VI: The False Prophet*,
*Martian Dreams*, and *The Savage Empire*.

pu6e Reloaded is a maintained derivative of **pu6e 0.6.0**, created by
**Jim Ursetto** and released on April 30, 2003. The original project and source
distribution remain available at
[3e8.org/hacks/ultima6](https://3e8.org/hacks/ultima6/). This edition brings
that editor forward to Python 3.14, Qt 6, and current OpenGL tooling while
preserving its original **GNU GPL version 2 or later** license.

![pu6e Reloaded Qt world editor](docs/main.png)

New to the editor? Start with the **[complete illustrated user
manual](docs/MANUAL.md)**, which walks through an unconfigured first launch,
Ultima VI setup, world editing, and safe saving.

## Supported games

| Game                                | Configuration key |
| ----------------------------------- | ----------------- |
| Ultima VI: The False Prophet        | `fp`              |
| Worlds of Ultima: Martian Dreams    | `md`              |
| Worlds of Ultima: The Savage Empire | `se`              |

Original game files and a saved game are required. This repository does not
include or grant permission to redistribute copyrighted game assets.

## What changed from the original

- Ported the original Python 2-era editor to **Python 3.14**.
- Replaced the historical wxWindows/wxPython interface with a native
  **PySide6 / Qt 6** desktop workbench.
- Added a three-game launcher with independent installation profiles,
  actionable validation errors, and per-user configuration.
- Added draggable world navigation, a minimap, zoom indicators, world-level
  shortcuts, icon-based toolbars, and quest browsing.
- Modernized dockable object, tile, chunk, and book inspection tools.
- Batched OpenGL terrain drawing with NumPy-backed vertex arrays for smoother
  zoomed-out rendering.
- Replaced the obsolete SWIG LZW extension with a memory-safe, pure-Python
  decoder.
- Removed obsolete wxPython interfaces, native-extension toolchains, and
  Python 2-era packaging scripts from the maintained source tree.
- Added automated coverage for supported games, game data, launcher behavior,
  editor operations, and configuration migration.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) on the host machine
- A desktop OpenGL implementation that supports a compatibility-profile context
- The original game data for one of the supported games

PySide6 provides official prebuilt Qt 6 wheels. Installing pu6e does not
require compiling the desktop toolkit from source.

## Packaged downloads

Tagged [GitHub Releases](https://github.com/Shin-Aska/pu6e-reloaded/releases)
provide self-contained builds that do not require installing Python or `uv`:

- Linux x86-64 AppImage: `pu6e-reloaded-VERSION-linux-x86_64.AppImage`.
- Linux x86-64 portable ZIP: `pu6e-reloaded-VERSION-linux-x86_64.zip`.
- Windows x86-64 standalone executable: `pu6e-reloaded-VERSION-windows-x86_64.exe`.
- Windows x86-64 portable ZIP: `pu6e-reloaded-VERSION-windows-x86_64.zip`.

On Linux, mark the AppImage executable before opening it:

```console
chmod +x pu6e-reloaded-*-linux-x86_64.AppImage
./pu6e-reloaded-*-linux-x86_64.AppImage
```

The ZIP distributions contain an executable `pu6e-reloaded` application folder.
Linux builds still need a compatible desktop OpenGL implementation; all builds
require separately obtained original game files and a saved game.

Windows downloads include Mesa Zink, the Vulkan loader, and a CPU Vulkan
fallback. No separate Mesa installation or Vulkan SDK is needed. Automatic
GPU selection prefers a discrete GPU when Windows exposes one. Native OpenGL
remains available in Settings.

## Install

On Ubuntu 24.04 or Linux Mint 22.x, install the required system packages for
Git, Qt's X11/XCB platform integration, and desktop OpenGL:

```console
sudo apt update
sudo apt install \
  git curl ca-certificates \
  libgl1 libegl1 libgl1-mesa-dri \
  libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-glx0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
  libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
```

Install `uv` if it is not already available, then reopen your terminal:

```console
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

Clone the repository, install Python 3.14, create the virtual environment,
and install the locked Python packages:

```console
git clone https://gitlab.com/ShinAska/pu6e-reloaded.git
cd pu6e-reloaded
uv python install 3.14
uv venv --python 3.14
uv sync --locked
```

`uv sync --locked` installs **NumPy**, **PyOpenGL**, **PySide6/Qt 6**,
PySide6's required support packages, and the development dependency
**pytest**. Use `uv sync --locked --no-dev` to omit development packages.
Inspect the installation with `uv tree --depth 2` and `uv pip check`.

Start the native game launcher:

```console
.venv/bin/pu6e
```

![Unconfigured pu6e Reloaded game launcher](docs/images/manual/01-first-launch-unconfigured.png)

Use the cog beside Ultima VI, Martian Dreams, or The Savage Empire to choose
that game's working directory. The launcher checks the original game files and
saved-world data before enabling its **Launch editor** button, and remembers
each game independently in your user configuration directory
(`~/.config/pu6e-reloaded/config.ini` on Linux). Existing repository-local
`pu6e.conf` configurations are migrated automatically. Game assets are
copyrighted and are not included.

For a screenshot-by-screenshot walkthrough from the unconfigured launcher
through Ultima VI setup, navigation, object and terrain editing, quest
browsing, safe saving, keyboard shortcuts, and troubleshooting, see the
**[complete illustrated user manual](docs/MANUAL.md)**. The complete
[documentation index](docs/README.md) also includes original manuals and
Ultima VI file-format research.

## Development

Sync the development environment with host `uv`, then run the test suite from
the virtual environment:

```console
uv sync
.venv/bin/pytest
```

Install the optional packaging tools and build the Linux distributions with:

```console
uv sync --locked --group packaging
bash packaging/build-linux.sh
```

On a Windows machine, use `./packaging/build-windows.ps1` instead. GitHub Actions
tests both operating systems, uploads all four distributions for every build,
and publishes them with SHA-256 checksums whenever a `v*` tag is pushed.

The Windows build downloads checksum-pinned graphics
runtimes into `build/mesa`. To enable the same Vulkan runtime when running
from source, run `./packaging/prepare-windows-mesa.ps1` once. Release checks
render and read back pixels through the bundled CPU Vulkan driver in both
Windows formats; `./packaging/smoke-windows-vulkan.ps1 -Executable PATH -Hardware`
also checks hardware Vulkan on a machine with a compatible GPU driver.

The original documentation and technical references are retained for historical
reference.
The original 2003 README, installation instructions, and copyright notice are
preserved verbatim under [`docs/history/`](docs/history/). Original game-data
research and technical references are preserved under
[`docs/reference/`](docs/reference/).

## Credits and provenance

- **Original author:** Jim Ursetto, creator of pu6e 0.6.0.
- **Original release:** April 30, 2003.
- **Original project:** [3e8.org/hacks/ultima6](https://3e8.org/hacks/ultima6/).
- **Modernization and maintenance:** Richard Louie Orilla and pu6e Reloaded
  contributors.

Full attribution and original copyright information are documented in
[`NOTICE.md`](NOTICE.md).

## License

pu6e Reloaded is licensed under the **GNU General Public License, version 2 or
(at your option) any later version**. SPDX identifier: `GPL-2.0-or-later`.

The complete GPLv2 text is provided in [`LICENSE`](LICENSE). Jim Ursetto's
original copyright and license notice is preserved in
[`docs/history/NOTICE-0.6.0.txt`](docs/history/NOTICE-0.6.0.txt).

Qt/PySide6, NumPy, PyOpenGL, and their bundled components retain their own
licenses. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for
dependency terms and Qt distribution considerations.
