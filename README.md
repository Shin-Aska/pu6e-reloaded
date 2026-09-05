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

Clone or download the repository, then run its setup script. Python and `uv`
do not need to be installed beforehand. If you use Git:

```console
git clone https://gitlab.com/ShinAska/pu6e-reloaded.git
cd pu6e-reloaded
```

**Windows x86-64**, in the built-in Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
.\.venv\Scripts\python.exe .\pu6e.py
```

**Linux or macOS**, in a terminal:

```sh
bash setup.sh
.venv/bin/python pu6e.py
```

Both scripts create `.venv` with Python 3.14 and install the locked application,
test, and packaging dependencies, including NumPy, PySide6/Qt, PyOpenGL, pytest,
and PyInstaller. Missing Python versions are downloaded automatically. They
reuse `uv` when available, otherwise install a pinned copy in `build/tools`
without editing your shell profile or global PATH. You can rerun setup safely.

Windows setup also downloads and prepares the bundled Vulkan runtime. Linux
setup installs missing desktop and packaging libraries with `apt` on Debian,
Ubuntu, and Linux Mint; it uses `sudo` when administrator access is needed.
On other Linux distributions, install the system libraries listed by
`bash setup.sh --help` and the script's diagnostic, then use
`bash setup.sh --skip-system-packages`.

macOS setup supports Intel and Apple Silicon on macOS 13 or later, following
[Qt's platform requirements](https://doc.qt.io/qt-6/supported-platforms.html).
It uses the system graphics frameworks and does not require Homebrew. macOS
packaged releases and bundled Vulkan are not currently provided.

After setup, tests can be run directly without activating the environment:

```console
.venv/bin/python -m pytest -q
```

On Windows, use `.venv\Scripts\python.exe -m pytest -q` instead.

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

Run the setup script above first. If `uv` was installed locally, use
`build/tools/uv` (`build\tools\uv.exe` on Windows) in place of `uv` below,
or add that directory to your terminal's PATH. To refresh the environment:

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
