# Architecture

pu6e Reloaded separates editable game data from its desktop presentation. The
game package can load, inspect, edit, and save a world without importing Qt or
OpenGL.
Each open editor owns a world session, a camera, and rendering options.

## Package boundaries

| Package | Responsibility |
| --- | --- |
| `game.models` | Game types, coordinates, objects and NPCs, terrain, immutable asset catalogs, and mutable world state. |
| `game.format` | Game resource manifests, DOS path resolution, compression, and binary decoding and encoding. |
| `game.services` | Loading complete worlds, querying and editing world state, and saving changed game files. |
| `ui.app`, `ui.profile`, `ui.launcher`, `ui.settings`, and `ui.shared` | Editor composition, installation profiles, launcher, persisted preferences, and reusable Qt widgets. |
| `ui.runtime` | Renderer probing, process restart, renderer setup, Vulkan discovery, and Windows runtime adapters. |
| `ui.rendering` | Camera geometry, rendering options, OpenGL batches, animation, and GPU resources. |
| `src/pu6e.py` | Application entry point, also exposed as the `pu6e` console command. |

Importable Python code lives under `src/`: `src/game`, `src/ui`, and
`src/pu6e.py`. Import names remain `game`, `ui`, and `pu6e`. Setup installs an
editable package, and tests exercise that installation without adding source
directories to `PYTHONPATH`.

Documentation is in `src/docs` and is excluded from Python package discovery.
Tests, setup scripts, and packaging tools stay at the repository root.

The UI package is organized by responsibility:

```text
src/ui/
  app/          # bootstrap, window composition, actions, docks, controller, commands
    map/         # canvas, input, navigation, panning, minimap, level labels, dialogs
    objects/     # object tree and inspector
    terrain/     # tile browser and chunk inspector
    books/       # book viewer
    quests/      # conversation search and navigation
  profile/       # installation profiles, validation, and configuration dialog
  launcher/      # launcher window, cards, stage, artwork, and style
  settings/      # INI persistence, renderer preferences, and settings dialog
  runtime/       # renderer probe, restart, Vulkan discovery, and platform adapters
    windows/     # Mesa, Vulkan, and OpenGL adapters
  shared/        # theme, icons, widget primitives, and reusable widgets
  rendering/     # camera, batches, overlays, textures, pixels, and renderer
```

Place code with the concept it implements: coordinate operations belong in
`game.models.coordinates`, file encodings in `game.format`, and world operations in
`game.services.editor`. Small functions stay beside their callers until they have a
clear shared responsibility.

## Application and configuration boundaries

`ui.app.bootstrap` owns the application flow. It creates the launcher and
injects editor-launch and restart callbacks, so `ui.launcher` never imports the
startup module. `SettingsStore` owns the existing configuration INI document and
preserves its profile and renderer sections; `GameProfileStore` manages game
installation directories and validation through that store.

Conversations follow the same game boundary: immutable records live in
`game.models.conversations`, archive decoding in `game.format.conversations`,
and installation reads in `game.services.conversations`. Quest UI code consumes
the service output without owning game-file parsing.

## State and dependencies

`WorldState` holds one game's directory, terrain, objects, NPCs, assets, and
dirty markers. `WorldSession` pairs that state with a `WorldEditor` bound to it.
Assets are immutable and may be read by several consumers; the terrain and
objects are mutable because editing them is the purpose of the application.

Game services depend on game models and formats. Formats depend on models where a
decoded value needs a domain type. Models do not import services. The Qt layer
depends on game; game does not depend on UI, Qt, or OpenGL code.

There is no process-wide active world and loading does not change the process
working directory. Every query and edit goes through an explicit state or
editor. This permits independent sessions without sharing objects, dirty
flags, palette animation, or camera position.

## Load, edit, and save

1. `WorldLoader.load(directory, game)` reads the selected installation and
   saved-world resources into a complete `WorldSession`. A failed load leaves
   the controller's existing session available.
2. `EditorController` installs the new session, clears selection and undo
   history, and signals views to refresh their data.
3. `WorldEditor` queries and changes the session's world, recording which
   terrain data and object blocks need saving. Undo commands retain the editor
   that originated them.
4. `WorldSaver.save(session)` writes changed object blocks, the NPC object
   list, and changed terrain data, preserving the existing backup policy.
   Codecs encode bytes without modifying objects, and retain data outside the
   known NPC section.

The original binary formats remain compatible with Ultima VI, Martian Dreams,
and The Savage Empire. The separation changes ownership and dependencies,
while retaining object identity, container order, and game-specific resources.

## Rendering lifecycle

The controller owns `CameraState` and `RenderOptions`. Camera coordinates and
viewport geometry can be updated without a graphics context. The canvas sends
its zoom-change signal after updating camera bounds, so the minimap viewport
rectangle changes immediately when zooming.

The canvas owns a `MapRenderer` for its session and Qt OpenGL context. Texture
IDs, animation state, and palette rotation belong to that renderer. GPU
resources are initialized and disposed while the canvas context is current;
changing the session rebuilds resources for the new assets. Rendering reads
game data and does not load game files.

## Distribution and provenance

Setuptools discovers `game` and `ui` recursively under `src` and packages
`src/pu6e.py` as the console entry module. The frozen Linux and Windows
builds collect `game` and `ui.rendering` alongside OpenGL's dynamically selected
platform modules. The Windows build also includes
`ui.runtime.windows.opengl` and the bundled Mesa runtime.

The former `U6` package and top-level `mapedit_gl.py` and `fastgl.py` modules
have been replaced by these packages. Their maintained game-format and
rendering behavior descends from Jim Ursetto's original pu6e. Attribution and
licensing remain in [NOTICE.md](../../NOTICE.md), [LICENSE](../../LICENSE), and the
unaltered documents under [history/](history/).
