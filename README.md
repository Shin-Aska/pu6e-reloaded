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

## Supported games

| Game | Configuration key |
| --- | --- |
| Ultima VI: The False Prophet | `fp` |
| Worlds of Ultima: Martian Dreams | `md` |
| Worlds of Ultima: The Savage Empire | `se` |

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
- Added automated coverage for supported games, game data, launcher behavior,
  editor operations, and configuration migration.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) on the host machine
- A desktop OpenGL implementation that supports a compatibility-profile context
- The original game data for one of the supported games

PySide6 provides official prebuilt Qt 6 wheels. Installing pu6e does not
require compiling the desktop toolkit from source.

## Install

Create the environment and install the locked project dependencies from the
repository root:

```console
uv venv --python 3.14
uv sync
```

Start the native game launcher:

```console
.venv/bin/pu6e
```

Use the cog beside Ultima VI, Martian Dreams, or The Savage Empire to choose
that game's working directory. The launcher checks the original game files and
saved-world data before revealing its **Launch editor** button, and remembers
each game independently in your user configuration directory
(`~/.config/pu6e-reloaded/config.ini` on Linux). Existing repository-local
`pu6e.conf` configurations are migrated automatically. Game assets are
copyrighted and are not included.

On Ubuntu systems using Qt's X11 platform plugin, install the required cursor
library if it is absent:

```console
sudo apt install libxcb-cursor0
```

The current checked-out `.venv` may already run through a localized workaround;
installing the system library is the reliable setup for a fresh environment.

For game-data preparation, configuration examples, navigation, editing,
keyboard shortcuts, safe saving, and troubleshooting, see the
**[User Guide](docs/USAGE.md)**. The complete
[documentation index](docs/README.md) also includes original manuals and
Ultima VI file-format research.

## Development

Sync the development environment with host `uv`, then run the test suite from
the virtual environment:

```console
uv sync
.venv/bin/pytest
```

The original source and documentation are retained for historical reference.
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
