# pu6e Reloaded

A Python 3.14 port of Jim Ursetto's **pu6e 0.6.0**, a world editor for
*Ultima VI*, *Martian Dreams*, and *Savage Empire*. The original source was
published at [3e8.org](https://3e8.org/hacks/ultima6/) in 2003.

The historical source and documentation are retained in this repository. The
runtime has been updated from Python 2 and wxPython Classic to Python 3.14,
wxPython Phoenix, NumPy, and current PyOpenGL. The obsolete SWIG LZW extension
has been replaced with a memory-safe pure-Python decoder. The old C sources are
kept for historical reference but are not part of the package build.

## Requirements

- Python 3.14
- A desktop OpenGL implementation
- GTK 3 development libraries on Linux (wxPython is built from source)
- The original game data for one of the supported games

## Install

Create and activate a virtual environment, then run:

```console
python -m pip install .
```

Set `gamedir` and `gametype` in `pu6e.conf`, then launch the editor:

```console
pu6e
```

Valid game types are `fp` (Ultima VI: The False Prophet), `md` (Martian
Dreams), and `se` (Savage Empire). Game assets are copyrighted and are not
included.

For game-data preparation, configuration examples, navigation, editing,
keyboard shortcuts, safe saving, and troubleshooting, see the
**[User Guide](docs/USAGE.md)**.

## Development

Install the project and pytest, then run the test suite:

```console
python -m pip install -e . pytest
python -m pytest
```

## License

The original pu6e sources are distributed under the license in
[`00LICENSE.txt`](00LICENSE.txt) and the GNU GPL text in [`00GPL.txt`](00GPL.txt).
