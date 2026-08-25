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

- Primary family: `IBM Plex Sans`, `Noto Sans`, `Ubuntu`, sans-serif.
- Technical family: `IBM Plex Mono`, `JetBrains Mono`, `DejaVu Sans Mono`, monospace.
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

The window is a native `QMainWindow` shell: a fixed menu/toolbar above, a
fluid central OpenGL map, independently scrolling left/right docks, and a
fixed status rail below. The map owns map-wheel interaction; each object tree
or tile library owns its own bounded scroll region. Docks can hide, resize,
float, and tabify; narrow desktop windows prioritize the map and allow docks
to be hidden. Preferred initial window size is at least 1120 x 760.

## 5. Reusable components

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

## 8. Accessibility constraints and accepted debt

- Primary text targets at least WCAG AA 4.5:1 contrast on its surface.
- Keyboard users can reach menus, docks, object trees, fields, and save actions.
- Focus and selected states use both contrast and the brass accent.
- Status and editing modes are stated in text, not communicated by color alone.
- Desktop-first native editor: no mobile, browser, or web-Lighthouse claim.
- No accepted accessibility debt at the time this system was defined.
