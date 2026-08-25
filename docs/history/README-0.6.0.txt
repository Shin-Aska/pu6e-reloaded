pu6e (Ultima 6 Editor) v0.6
Author: Jim Ursetto <jim@3e8.org>
URL:    http://3e8.org/hacks/ultima6
------------------------------------

pu6e is a world editor for Ultima 6 and the Worlds of Ultima
(Martian Dreams and Savage Empire).  It's written in Python
and uses wxWindows and OpenGL.  pu6e is tested on Linux and
Windows 2000, and requires a 3D card.

pu6e lets you:

- Create, modify, and delete objects
- Manipulate containers, via a tree view
- Edit terrain and map chunks
- View all map and object tiles
- View tile and palette animation
- View and move NPCs
- View book contents
- Save map, object and NPC data
- Play your new worlds with the Ultima 6 family!

pu6e is pronounced "puce", just like the color.

Getting Started
---------------

0. If you're not using a prebuilt package, read the 00INSTALL.txt
   file for installation instructions.
1. Edit pu6e.conf.  Set "gamedir" to your ULTIMA6 directory.
   Set "gametype" to:
      "fp"     U6: The False Prophet
      "md"     U6: Martian Dreams
      "se"     U6: Savage Empire
   You can also set initial width, height, and zoom if you like.
2. Run the game (pu6e.exe is the Windows binary; pu6e.py for
   everyone else).

pu6e needs the Ultima 6 font to show grid numbers and location.
If you're running a Worlds of Ultima game and have a copy of
Ultima 6, copy "u6.ch" over from the U6 directory.

Map Editor
----------

The map editor is your viewport into the world.  You start centered on
Lord British's castle, at (134, 16c, 0).  You can make the window any size,
subject only to your machine's horsepower.  In the window, you can:

- Left click on a location.  Its coordinates and a description of the maptile
  and any objects there are displayed on the console.  This data is sent to
  the Stack Editor, Chunk Editor, and Tile Editor (described later).

  pu6e also tells you what U6 would say if you "Look"ed at that location.
  U6 has several rules that determine which object takes priority for
  Looks and Gets--it's not always the topmost object at the location,
  or the one drawn on top.  If you've played the game, it'll make sense.

- Drag an object with the left button.  The object will be picked up
  and moved to the destination.  (No feedback is given until you drop it.)
  Hold down Control while dragging to copy the object rather than
  moving it.  Note that the object moved is the same one you'd "look"
  at in the game.

- Drag a maptile (background tile) with the left button.  If Options/Edit
  Terrain is active, and there's no object in the way, the source maptile will
  be copied to the destination.  Maptiles can't be moved, since every point in
  space must have a maptile, so Control is ignored.  You can turn off objects
  if you want to move maptiles around without interference.

- Create a new maptile with the right button.  The currently selected
  maptile from the Tile Viewer is placed at the clicked-upon location.
  (Edit Terrain does not have to be active in this case.) You can drag
  with the right button to "paint" the tile.

  Note: Tile Viewer can select any of the 2048 tiles, but you can only
  place maptiles (tiles 0 - 255).

- Drag (copy) an entire map chunk (8x8 maptiles) with Shift+Left button.

- Use the keyboard to navigate or to bring up auxiliary windows.

Navigation:

** On Windows, make sure NumLock is ON!

You can use the arrow keys to move one tile at a time.
Use the numeric keypad to move around by chunks (8 tiles).
Additionally, on the keypad:

5   Move down a level (descend).
0   Move up a level (ascend).
+   Zoom in by 2x.
-   Zoom out by 2x.

A tour of the menu:

- File / Save:             Save object, NPC and map data, overwriting your
                           current game.  Ultima 6 should almost always be
						   able to read my saves, but a backup is made to be safe.
- File / Quit:             Quit.
- View / Animated Tiles:   Animate tiles.
- View / Palette rotation: Rotate the palette.
- View / Hybrid Tiles:     Animate hybrid (shoreline, typically) tiles.
                           Currently unoptimized, so it's off by default.
- View / Objects:          Toggle object display, useful when editing maptiles.
- View / Grid:             Visually divide the world into chunks.  Each chunk is
                           labelled with its chunk number, from 0 - 1023.
- View / Location:         Toggle the on-screen display of the coordinates
                           of the center tile.
- View / Fullscreen:       Toggle fullscreen display.
- View / Zoom In/Out:      Zoom in or out by 2x.  Zooming is unlimited.
- Options / Edit Terrain:  Enable the copying of maptiles by dragging on the map.
                           This is disabled by default.
- Window / Stack Editor:   Toggle the display of the Stack Editor, which displays
                           objects at a location in a tree view.
- Window / Tile Viewer:    Show or hide the 2048 map and object tiles.
- Window / Chunk Editor:   Show or hide your interface to setting chunk numbers.
- Window / Book Editor:    View book contents.
- Window / Go to...:       Center the screen on the specified x, y, and z
                           hex coordinates (x, y range from 0 - 3ff;
					       z ranges from 0 to 5).

For convenience, keyboard shortcuts are provided for the menu commands.
I don't usually use the menu, especially because it doesn't work fullscreen.

Ctrl+S  Save
Q       Quit
A       Animate tiles
P       Palette rotation
H       Hybrid tiles
O       Objects
G       Grid
L       Location
F       Fullscreen
Ctrl+T  Edit terrain
S       Stack Editor
T       Tile Editor
C       Chunk Editor
Ctrl+G  Go to...

Stack Editor
------------

The Stack Editor provides a tree view of the currently selected map
location, showing all objects from bottom to top, including items
in containers.  Each item is described as it would be in the
game--"a chest", "30 gold coins".  The topmost object is automatically
selected for you by default.  Selecting an object places it in the Object
Editor, located on the right side of the window.

You can reorder objects and move them into containers with the keyboard:

X       Cut the selected object to the clipboard.
C       Copy the selected object to the clipboard.
V       Paste the object on the clipboard, after the selection.
Shift+V Paste the object on the clipboard, before the selection.
B       Paste the clipboard into the selection, treating it as
        a container.  -Any- object may be a container.
		Alias: Ctrl+V.
N       Create a default object (leather helm) on the clipboard,
        which you can then paste into existence.  Alias: Insert.
Delete  Delete the selection; don't put it on the clipboard.
S       Close the Stack Editor (same as the command to open it).
        Alias: Escape.

Note that you can, for example, cut an object, click somewhere else
on the map, and then paste it in--effectively moving that object
between two points on arbitrary levels.

When you paste an object, it disappears from the clipboard.  This is
because the object on the clipboard is really an object, not just
a name, and objects must be unique.  So, to duplicate an object
five times, type "CV" five times.

On Linux, you can drag objects from one place to another with the mouse,
including into and out of containers.  On Windows, dragging is currently
disabled.  Don't worry, using the keyboard is much better anyway; I
don't bother dragging.

Notes: - Ultima 6 will crash if you leave an egg empty.
       - NPCs cannot be copied (and requests to do so are ignored).
	     However, you can move (cut/paste) them at will.
       - Objects bigger than one tile actually "exist" at the location
	     of their lower-right tile; the other tiles won't show up in
	     the Stack Editor.

Object Editor
-------------

The Object Editor lets you modify objects' attributes.
Some attributes require that you have some technical knowledge
of the game, for best operation.  You can edit the following attributes:

- Type: select one of 1024 objects.

- Frame: In general, represents different views of the same object.
  For example, a chair has one frame for each of its four
  orientations; a brazier has four frames for its four types;
  a chest's frames signify that it's open, shut, locked, or magically
  locked.  The object description may vary for different frames of the
  same object.  You may have to experiment to find the right frame
  to display a large (bigger than one tile) object correctly.

- Quantity: In general, controls how many of an object there are,
  for objects such as gold coins and black pearls.  A quantity of
  zero does not mean zero objects; it means the object is singular,
  and will not stack / aggregate / whatever you like to call it.

- Quality: Controls such things as which door a lever opens, the type of
  spell, the contents of a book, and so on.  There are some notes about
  ladders at the end of this document.

- Status: Status byte, in hex.  You have to read the technical documentation to
  understand this value.  However, pu6e should automatically correct any errors
  you make whenever it saves your changes.  In general, you'll only care about
  bit 0.  This is the 0wned (OK to take) bit -- if it's 0, taking the object is
  stealing.  For most objects, you can just type 0 (stealing) or 1 (owned) in
  the box.  Note: you MUST press enter after entering the value
  (unfortunately).  You can't just tab out of the control yet.

- Weight: The total weight of the object plus any objects inside it.
  You can't currently edit this value.

Changes to attributes are reflected in the Stack Editor and in the
map window as you make them.

Chunk Editor
------------

This is a very simple dialog that lets you edit the chunk number associated
with the currently selected chunk.  (You select a chunk by clicking on it on
the map screen.)  There are 1024 possible chunks--and U6 uses almost every one!

If you'd like to edit the contents of a given chunk, simply drag maptiles
onto it or use the right mouse button in the map window, as described above.
You can also copy chunk numbers around by Shift+Left dragging.

Be sure to activate the grid--it's a big help.  "C" or Escape will close
the chunk editor.

Tile Viewer
-----------

Displays the 2048 game tiles.  The default window displays exactly 256 tiles.
Click on one, and it will be selected and the tile number and name reported.
If you select a maptile (having a number between 0 and 255), you can drop it in
the map window by right-clicking and/or dragging.

"T" or Escape will close the tile viewer.

Book Editor
-----------

Simple book viewer (not an editor yet).  Although I mostly understand the
markup the designers used to signify hint words, Gargish, and so on,
I haven't implemented the display.  This should be hooked up to the Stack
Editor; in lieu of that, the contents of books are displayed on the console
when you click on the map.

Ladders
-------

The dungeon levels are 4 times smaller than the surface in both the x and y
dimensions.  When you descend to the dungeons, a 4x4 area of surface
chunks is mapped onto the same dungeon chunk.  When going up, though, how
does the game know which of the 16 chunks to put you in?  The answer lies
in the quality of the ladder.  Given a 4x4 grid of surface chunks:

       0  1  2  3
       4  5  6  7 <--- a ladder quality of 7 will bring you here.
       8  9 10 11
      12 13 14 15

When descending from the surface, pu6e will put you at the corresponding
dungeon coordinates.  When ascending to the surface, pu6e always puts you
at chunk #0 in the grid above.  You can use these facts to place ladders
correctly without repeatedly trying them out in the game.
Note: quality has no effect for descending ladders.

Misc
----

I chose OpenGL because the goal is to allow editing and simulation of the U6
engine in very high resolutions (I run at 1280x1024 fullscreen) and framebuffer
access is just not fast enough. However, I wrote three other renderers while
speed testing and there's nothing that restricts pu6e to OpenGL in the future.

Bugs
----

- Rendering is subject to glitches as you zoom far out.
- "Draw-below-all-tiles" tiles are not supported.  They're drawn in normal object
  order, so certain doorways appear incorrectly.
- The only Look order rule I do not yet emulate is that NPCs are considered
  "on top" of everything in U6, while I use the standard object rules.
- The grid and hybrid tiles are both fairly expensive.
- Menu items should really be check items.
- MD/SE books are not displayed.
- Quite a few other annoyances...

--
* Copyright 2003 Jim Ursetto <jim@3e8.org>.
* All trademarks mentioned herein are the property of their respective owners.
