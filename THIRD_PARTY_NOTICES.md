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

## Proprietary game assets

The supported games, their artwork, game files, saved games, names, and
trademarks remain subject to their respective owners' terms. No original game
assets are distributed with pu6e Reloaded.
