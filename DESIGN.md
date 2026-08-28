# pu6e Reloaded desktop design system

## 1. Atmosphere and identity

A cartographer's workbench for Britannia and the Worlds of Ultima: quiet,
precise, and built around the original pixel-art world. The world itself is
the brightest surface. Smoked-ink chrome, nested slate panels, and a restrained
brass accent frame it without competing with the 1990s game palette. Linear's
dark-native elevation and keyboard-first density inform the workbench; the
brass color story and DOS-era monospace coordinates belong specifically to
Ultima. The signature moment is a vivid, pixel-perfect map surrounded by
calm, instrument-like navigation and object-inspection panels.

The launcher follows the approved **Atlas** direction: a quiet, narrow world
library on the left and one cinematic, edge-to-edge illustrated world on the
right. Selecting Britannia, Mars, or Eodon changes the landscape, atmosphere,
story, availability, and primary action together. The composition is a native
desktop game launcher, never a vertical stack of web-like settings cards.

## 2. Color

| Role | Token | Value | Usage |
| --- | --- | --- | --- |
| Deep canvas | `surface.canvas` | `#101215` | Window and map surround |
| Primary panel | `surface.panel` | `#171a1f` | Dock and toolbar surfaces |
| Elevated panel | `surface.elevated` | `#1e2228` | Inputs, menus, selected rows |
| Hover panel | `surface.hover` | `#272c34` | Hovered controls and rows |
| Pressed panel | `surface.pressed` | `#303640` | Pressed controls |
| Primary text | `text.primary` | `#edf0f2` | Headings and selected values |
| Secondary text | `text.secondary` | `#b6bec8` | Body copy and field values |
| Muted text | `text.muted` | `#818b98` | Hints, metadata, empty states |
| Disabled text | `text.disabled` | `#626b76` | Disabled controls |
| Default border | `border.default` | `#303640` | Inputs and focused panel edges |
| Subtle border | `border.subtle` | `#242931` | Dock, menu, and toolbar separators |
| Brass accent | `accent.primary` | `#d6a657` | Selected controls and active tools |
| Brass hover | `accent.hover` | `#e7bb70` | Hovered accent controls |
| Brass pressed | `accent.pressed` | `#b88943` | Pressed accent controls |
| Brass wash | `accent.wash` | `#332a1c` | Selected rows and active backgrounds |
| Success | `status.success` | `#75b887` | Saved or ready status |
| Warning | `status.warning` | `#e0b35f` | Terrain-edit warning |
| Error | `status.error` | `#df7771` | Invalid or failed operations |
| Launcher rail | `surface.launcher_rail` | `#0d1116` | Atlas world-library rail |
| Britannia sky | `scene.britannia.sky` | `#435d60` | Britannia atmosphere |
| Britannia horizon | `scene.britannia.horizon` | `#293d3e` | Britannia mountains |
| Britannia foreground | `scene.britannia.foreground` | `#131e20` | Britannia castle silhouette |
| Britannia light | `scene.britannia.light` | `#dccca2` | Britannia moon and mist |
| Mars sky | `scene.mars.sky` | `#a75c3e` | Martian atmosphere |
| Mars horizon | `scene.mars.horizon` | `#653a35` | Martian ridges |
| Mars foreground | `scene.mars.foreground` | `#24181b` | Martian observatory |
| Mars light | `scene.mars.light` | `#efbd86` | Martian sun and haze |
| Eodon sky | `scene.eodon.sky` | `#758a64` | Eodon jungle atmosphere |
| Eodon horizon | `scene.eodon.horizon` | `#405940` | Eodon tree line |
| Eodon foreground | `scene.eodon.foreground` | `#162119` | Eodon prehistoric silhouette |
| Eodon light | `scene.eodon.light` | `#e0cf8f` | Eodon sun and jungle mist |

Rules: the brass accent denotes selection, focus, or meaningful actions; it is
never a decorative wash over the map. Original game art retains its own palette.
All Qt stylesheet colors are sourced from named theme tokens.

## 3. Typography

| Level | Size | Weight | Usage |
| --- | --- | --- | --- |
| Workbench title | 18 px | 650 | Product/title heading |
| Section heading | 14 px | 600 | Dock headings and selected object |
| Body | 13 px | 400 | Controls, menus, and tree rows |
| Emphasis | 13 px | 550 | Active tabs and highlighted labels |
| Caption | 11 px | 500 | Helper text and section labels |
| Coordinates | 13 px | 500 | Hex locations, object IDs, tile values |
| Launcher wordmark | 26 px | 650 | Atlas product signature |
| Launcher world title | 42 px | 600 | Selected-world cinematic heading |
| Launcher world subtitle | 16 px | 400 | Selected game edition |

- Primary family: `IBM Plex Sans`, `Noto Sans`, `Ubuntu`, sans-serif.
- Technical family: `IBM Plex Mono`, `JetBrains Mono`, `DejaVu Sans Mono`, monospace.
- Cinematic launcher headings: `Georgia`, `Noto Serif`, serif; the rest of the
  launcher keeps the existing primary and technical families.
- All object identifiers, coordinates, level indicators, and byte fields use
  the technical family. Native Qt application font scaling remains enabled.
- Label casing is sentence case; hexadecimal coordinates use lowercase digits.

## 4. Spacing and layout

| Token | Value | Usage |
| --- | --- | --- |
| `space.1` | 4 px | Icon-to-label or dense inner rhythm |
| `space.2` | 8 px | Toolbar groups, tree indentation rhythm |
| `space.3` | 12 px | Form padding and compact gaps |
| `space.4` | 16 px | Dock and section padding |
| `space.5` | 20 px | Comfortable editor grouping |
| `space.6` | 24 px | Major panel separation |
| `space.7` | 32 px | Launcher hero copy separation |
| `space.8` | 40 px | Launcher stage outer padding |

The window is a native `QMainWindow` shell: a fixed menu/toolbar above, a
fluid central OpenGL map, independently scrolling left/right docks, and a
fixed status rail below. The map owns map-wheel interaction; each object tree
or tile library owns its own bounded scroll region. Docks can hide, resize,
float, and tabify; narrow desktop windows prioritize the map and allow docks
to be hidden. Preferred initial window size is at least 1120 x 760.

The Atlas launcher uses a native horizontal shell, a fixed 232 px world rail,
and a flexible illustrated stage. Its minimum desktop size is 860 x 560;
the preferred opening size is 1040 x 660. Hero controls stay visible at the
minimum size, world titles may wrap once, and long game paths elide instead of
overlapping the action row.

## 5. Reusable components

### Atlas world selector

- Structure: native clickable selection row with a brass game sigil, game
  title, compact readiness text, and an independently reachable settings cog.
- Variants: Britannia, Mars, Eodon.
- Spacing: `space.2` inner rhythm; `space.3` row padding.
- States: normal, hover, keyboard focus, selected, ready, unavailable.
- Accessibility: native keyboard focus, descriptive selection/configuration
  names, text-based availability, and actionable diagnostic tooltips.
- Layout: fixed-width left rail; exactly one world is selected at a time.

### Atlas illustrated world stage

- Structure: full-bleed world-specific painted sky, layered terrain silhouette,
  distinctive landmark, legible dark foreground veil, setting label, game
  title/subtitle, short world description, launch/configuration controls, and
  visible readiness or recovery guidance.
- Variants: Britannia moon/castle, Mars sun/observatory, Eodon sun/jungle.
- Spacing: `space.8` stage padding; `space.4` action gaps; `space.6` between
  story and controls.
- States: selected ready, selected unavailable, keyboard focus, configure,
  launch failure, and recovery after files are repaired.
- Accessibility: the artwork is decorative; all world identity, readiness,
  recovery detail, and actions remain available as real native controls/text.
- Layout: fluid right stage; the primary action remains in the lower reading
  zone and diagnostics do not clip at the minimum window size.

### Launcher renderer settings

- Structure: a global settings action in the Atlas rail opens one compact
  native dialog with a labeled renderer selector, backend explanation, a
  Vulkan-only GPU selector, restart guidance, and cancel/save actions.
- Variants: Software, OpenGL, Vulkan.
- Spacing: `space.6` dialog padding; `space.3` field and action rhythm.
- States: current value, changed value, saved, persistence failure, keyboard
  focus, and restart required.
- Accessibility: the settings action and selector have explicit accessible
  names; every backend and Vulkan adapter is named in text and its tradeoff is
  described without depending on color.
- GPU selection: Automatic is the recommended default; Vulkan adapters include
  their reported name and device type. The row is hidden for Software and
  OpenGL, and a saved adapter that disappears falls back to Automatic with a
  startup notice.
- First-run behavior: Vulkan with Automatic GPU selection is the default when
  no renderer preference has ever been saved; later launches preserve the
  user's explicit renderer and GPU choices.
- Restart flow: saving a changed renderer or Vulkan GPU opens a native choice
  between **Restart now** and **Later**. The current process exits only after a
  replacement process starts successfully; failure remains visible and leaves
  the current launcher running.
- Runtime indicator: launcher and workbench window titles append the resolved
  renderer name; CPU Vulkan is identified separately and a fallback reports
  the backend actually in use rather than the saved preference.
- Layout: the global action remains separate from per-world configuration and
  reachable at the bottom of the fixed launcher rail.

### Workbench toolbar

- Structure: compact action clusters separated by subtle vertical dividers.
- Variants: file actions, navigation, view overlays, terrain mode.
- Spacing: `space.2` inside clusters; `space.3` between clusters.
- States: normal, hover, pressed, checked, disabled, keyboard focus.
- Accessibility: descriptive action text/tooltips and native keyboard shortcuts.
- Layout: horizontal fixed-height cluster; commands remain in menus as well.

### Inspector dock

- Structure: named dock title, optional summary, bounded scrollable content.
- Variants: object stack/properties, tiles, chunk, books.
- Spacing: `space.4` outer padding; `space.2` row spacing.
- States: populated, no selection, hidden, floating, focused.
- Accessibility: native dock visibility actions, keyboard-reachable controls.
- Layout: independently scrollable dock; window toolbar/status remain fixed.

### Property field

- Structure: sentence-case label paired with a native spin box or read-only value.
- Variants: decimal object fields, hexadecimal byte/coordinate, static weight.
- Spacing: `space.2` between rows; `space.3` inner field padding.
- States: normal, hover, focus, disabled, invalid, committed.
- Accessibility: explicit label buddies, bounded numeric ranges, visible focus.
- Layout: two-column form that remains readable when dock width changes.

### Object stack tree

- Structure: selected map position, nested object rows, current selection.
- Variants: root location, object, container, contained object.
- Spacing: `space.1` row breathing room; `space.4` nesting.
- States: empty, populated, selected, focused, expanded, collapsed, drag target.
- Accessibility: native tree keyboard navigation and meaningful row labels.
- Layout: bounded tree scroll owner above the separately sized property form.

### Tile library

- Structure: filter/search field, icon-and-label tile grid, selected-tile summary.
- Variants: background tile, object tile, selected paint tile.
- Spacing: `space.2` between icons and rows.
- States: normal, hover, selected, filtered-empty, paint-invalid.
- Accessibility: keyboard-selectable grid, readable tile names and numeric IDs.
- Layout: only the tile grid scrolls; search and current selection remain fixed.

### Location rail

- Structure: persistent hexadecimal X/Y, level, current tool, save feedback.
- Variants: normal location, terrain-edit warning, success, error.
- Spacing: `space.3` between rail groups.
- States: ready, changed, saving, saved, failed.
- Accessibility: text conveys state independently of status color.
- Layout: fixed bottom status bar; technical fields use the mono family.

## 6. Motion and interaction

No decorative motion. Native hover, pressed, checked, selected, and focus states
must be visible immediately; game animation retains the existing 51 ms renderer
tick. All primary workflows have menu actions and keyboard shortcuts. Editing is
direct and immediate; failed operations use explicit native error messaging.
Undo/redo commands describe the mutation and remain disabled until available.

## 7. Depth and surface

Use tonal elevation plus restrained one-pixel separators: canvas `#101215`,
panel `#171a1f`, elevated input `#1e2228`, hover `#272c34`. Controls use a
4 px radius and dialogs/panels use a 6 px radius; no exaggerated rounded cards,
drop-shadow-heavy surfaces, decorative gradients, or unrelated accent colors.
The native OpenGL map remains sharp and unfiltered.

Exception: the Atlas selected-world stage intentionally uses authored,
world-specific atmospheric gradients, a softly lit celestial body, layered
silhouette depth, and a dark reading veil. These are illustrated game artwork,
not decorative gradients applied to the editor's functional controls.

## 8. Accessibility constraints and accepted debt

- Primary text targets at least WCAG AA 4.5:1 contrast on its surface.
- Keyboard users can reach menus, docks, object trees, fields, and save actions.
- Focus and selected states use both contrast and the brass accent.
- Status and editing modes are stated in text, not communicated by color alone.
- Each launcher world is keyboard selectable, exposes its availability in text,
  and retains an independently labeled configuration action.
- Unavailable worlds show a visible recovery reason and diagnostic tooltip;
  world selection never depends on color or mouse-only interaction.
- Desktop-first native editor: no mobile, browser, or web-Lighthouse claim.
- No accepted accessibility debt at the time this system was defined.
