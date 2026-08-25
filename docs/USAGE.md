# Using pu6e Reloaded

pu6e is a world editor for **Ultima VI: The False Prophet**, **Martian
Dreams**, and **The Savage Empire**. Its native PySide6/Qt 6 desktop workbench
uses a compatibility-profile OpenGL map and dockable object, tile, chunk, and
book tools. It writes original game data and saved-object files when you
explicitly save. Read the backup guidance below before making changes.

## 1. Prepare a safe game-data directory

Do not point pu6e at your only game installation or only save. Start with a
complete, disposable copy of the game directory. The directory should contain
files such as `map`, `chunks`, `basetile`, `tileflag`, `tileindx.vga`, and a
`savegame` directory containing `objlist` and the `objblk*` files.

Game files are not distributed with pu6e. Install the game from your own media
or store, run it once so a save exists, exit the game, and copy its data
folder. For example:

```console
cp -a ~/Games/ULTIMA6 ~/Games/ULTIMA6-pu6e
```

On Windows, copy the directory in File Explorer instead. Do not edit a game
while it or a cloud-save client is running.

> **Linux note:** the historical editor uses lowercase DOS filenames. If an
> installation has uppercase names, make a lowercase-named working copy or
> run pu6e on a case-insensitive filesystem. Do not rename the only copy of an
> installation.

## 2. Install

From the repository root, use host `uv` to create a Python 3.14 environment
and install the project:

```console
uv venv --python 3.14
uv sync
```

PySide6 is installed as an official prebuilt Qt 6 wheel; no desktop-toolkit
source compilation is needed. The application needs a real desktop OpenGL
implementation with compatibility-profile support; it is not a terminal-only
program.

On Ubuntu systems running Qt through X11, install the Qt platform plugin's
cursor dependency when it is not already present:

```console
sudo apt install libxcb-cursor0
```

The current checked-out `.venv` may already run through a localized workaround,
but the system package is the reliable setup for a fresh environment.

## 3. Configure a game

Edit `pu6e.conf` in the directory from which you launch the editor:

```ini
[pu6e]
gamedir = /home/example/Games/ULTIMA6-pu6e
gametype = fp
width = 1024
height = 768
zoom = 1
```

On Windows, either use forward slashes or double backslashes:

```ini
gamedir = C:/Games/ULTIMA6-pu6e
```

Choose the matching game type:

| Value | Game |
| --- | --- |
| `fp` | Ultima VI: The False Prophet |
| `md` | Martian Dreams |
| `se` | The Savage Empire |

`width` and `height` set the initial viewport. `zoom` is the initial scale;
`1` displays each game pixel at its normal size.

Martian Dreams and Savage Empire do not normally include the Ultima VI bitmap
font. Copy `u6.ch` from an owned Ultima VI installation into their working
directory if you want the coordinate and grid-number overlays.

## 4. Start the editor

Run the installed editor from the directory containing `pu6e.conf`:

```console
.venv/bin/pu6e
```

For development checks, use the same virtual environment rather than a bare
host Python:

```console
.venv/bin/pytest
```

The Qt workbench keeps the compatibility-profile OpenGL map in the center,
with dockable object stack and properties, tile browser, chunk inspector, and
read-only book viewer around it. Docks can be resized, hidden, floated, or
tabified. The initial view is centered near Lord British's castle at hexadecimal
world coordinates `(134, 16c, 0)`.

## 5. Navigate the map

Click the map before using map-navigation shortcuts so the canvas has focus.
Coordinates shown by the editor are hexadecimal. Menus, docks, trees, and
fields are keyboard reachable; use normal Qt focus navigation to move between
them, then return focus to the map for map controls.

| Input | Action |
| --- | --- |
| Arrow keys | Move one tile |
| Middle-button drag | Pan the world without changing game data |
| Left-drag empty terrain | Pan while terrain editing is disabled |
| Numeric keypad directions | Move one 8×8 chunk |
| Numpad `5` | Descend one level |
| Numpad `0` | Ascend one level |
| `+` / numpad `+` | Zoom in 2× |
| `-` / numpad `-` | Zoom out 2× |
| `Ctrl+G` | Go to hexadecimal X, Y, Z coordinates |

On Windows, enable Num Lock for numeric-keypad navigation.

## 6. Inspect and edit the world

### Select a location

Left-click a tile to select it. pu6e updates the coordinate status and its
object-stack, map-chunk, and tile-library tools.

### Move or copy objects

- **Left-drag an object** to move it.
- **Ctrl+left-drag** to copy a copyable object.
- NPCs can be moved but cannot be cloned.
- Multi-tile objects are anchored at their lower-right tile.

### Edit terrain

There are two terrain workflows:

1. Enable **Tools → Edit terrain**, then left-drag a background tile to copy
   it to another position. Disable object display if an object blocks the
   desired source tile.
2. Open **Window → Tile library**, select a map tile numbered 0–255, then
   right-click or right-drag on the map to paint it.

The Tile Viewer can display all 2,048 tiles, but only tiles 0–255 are valid as
background map tiles.

### Copy an 8×8 chunk

Shift+left-drag copies the source map chunk to the destination chunk position.

## 7. Main shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+S` | Save objects, NPCs, map, and chunks |
| `Ctrl+Z` | Undo the most recent supported edit |
| `Ctrl+Y` | Redo the most recently undone supported edit |
| `Ctrl+Q` | Quit |
| `A` | Toggle animated tiles |
| `P` | Toggle palette rotation |
| `H` | Toggle hybrid-tile animation |
| `O` | Toggle objects |
| `G` | Toggle the chunk grid |
| `L` | Toggle center coordinates |
| `F` | Toggle fullscreen |
| `Ctrl+T` | Toggle terrain-edit mode |
| `S` | Toggle Object stack |
| `T` | Toggle Tile library |
| `C` | Toggle Map chunk |
| `M` | Toggle World map |
| `Ctrl+G` | Open Go To |

The same features are available from the workbench **File**, **Edit**, **View**,
**Tools**, and **Window** menus. Shortcut availability follows the focused
tool, and disabled Undo or Redo means there is no supported change to apply.

## 8. Auxiliary editors

### Object stack and inspector

The Object Stack dock shows every object at the selected location, from bottom
to top, with contained objects nested below their container. Selecting an
object updates the adjacent inspector.

| Key | Action |
| --- | --- |
| `X` | Cut selected object |
| `C` | Copy selected object |
| `V` | Paste after selection |
| `Shift+V` | Paste before selection |
| `B` or `Ctrl+V` | Paste into selected object as a container |
| `N` or `Insert` | Create the default object on the clipboard |
| `Delete` | Delete selection |
| `S` | Toggle the object-stack tool |

An object disappears from the clipboard after paste because game objects must
be unique. To create repeated copies, copy and paste repeatedly. Do not leave
an Ultima VI egg container empty; the original game can crash when loading it.

### Object inspector

Selecting an object in the stack exposes:

- **Type:** base object number.
- **Frame:** visual state or orientation.
- **Quantity:** stack size; zero means a singular object, not no object.
- **Quality:** game-specific behavior such as door links, spells, or books.
- **Status:** raw hexadecimal status byte. Press Enter after editing it.
- **Weight:** calculated read-only total.

Make small changes and test them in a disposable game copy. Type, quality, and
status values are game-format fields, not guarded gameplay-level settings.

### Chunk inspector

Selecting a map location shows its current 8×8 chunk. Change the chunk number
to replace that map location with another existing chunk.

### World map

The World map dock renders a live overview of the current surface or dungeon
level using the original game tiles and palette. Its brass outline marks the
currently visible map area. Click or drag anywhere in the overview to jump to
that world location; press `M` to toggle the dock.

### Tile browser

The viewer displays map and object tiles and supplies the current tile for
right-button terrain painting. Press `T` to toggle its visibility.

### Book viewer

The read-only Book Viewer displays Ultima VI book text by book number. Martian
Dreams and Savage Empire book formats are not decoded and appear empty.

## 9. Save safely

Choose **File → Save** or press `Ctrl+S`. pu6e writes changed object blocks,
NPC data, map data, and chunks. It creates `.bak` files beside files it
rewrites, but those backups are not a substitute for the untouched working
copy created in step 1.

Recommended workflow:

1. Exit the original game.
2. Copy the entire test game directory.
3. Make one small edit in pu6e.
4. Save and exit pu6e.
5. Start the game and verify the edit.
6. Keep the change only after the game successfully loads the save.

Do not synchronize the directory with GOG Galaxy, Steam Cloud, Proton Drive,
or another cloud client while pu6e or the game is writing it.

## 10. Troubleshooting

### `FileNotFoundError`

Confirm that `gamedir` points to the directory containing `map`, `chunks`, and
`tileflag`, not its parent. On a case-sensitive filesystem, confirm the DOS
filenames are lowercase.

### Missing `savegame/objblk*`

Run the game and create a save first. Some installations keep active saves in
a separate platform or cloud-save directory; copy the complete active save
into the working game's `savegame` directory.

### No coordinate or grid labels

The game directory lacks `u6.ch`. This is expected for Worlds of Ultima. Copy
that file from an owned Ultima VI installation if desired.

### OpenGL, blank-window, or compatibility-context errors

Update the graphics driver and verify that desktop OpenGL can create a
compatibility-profile context. Linux users in containers or remote shells must
forward a display and provide GLX or an equivalent compatible OpenGL context.
Wayland-only or software-only sessions may need an X11/GLX-capable desktop
session for this fixed-function renderer.

### Qt cannot load the `xcb` platform plugin

On Ubuntu, install the missing X11 cursor dependency and restart the editor:

```console
sudo apt install libxcb-cursor0
```

The repository's current `.venv` may already have a localized workaround, but
new environments should use the system dependency.

## Historical reference

The original detailed manual remains in [`../00README.txt`](../00README.txt),
and file-format research is retained under [`../doc/`](../doc/).
