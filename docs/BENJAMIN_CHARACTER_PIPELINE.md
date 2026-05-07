# Benjamin Character Pipeline

Benjamin's active source is the Godot-ignored Character Creator/Blender file:

`assets/models/characters/benjamin/source/BenjaminCharacter.blend`

The runtime file used by Godot scenes is the accepted Mesh2Motion game rig export:

`assets/models/characters/benjamin/runtime/benjamin_male_animated.glb`

## Current Rule

Do not generate Benjamin from primitives or procedural body parts for the active
player model. Benjamin must come from the professional character creator source,
then be rigged/exported through the game character pipeline.

The old procedural placeholder was retired to:

`archive/character_export_attempts/procedural_placeholder_retired_20260716_1330/`

## Refresh Benjamin

Use this flow when replacing or improving Benjamin:

1. Build or adjust Benjamin in the character creator source.
2. Open `assets/models/characters/benjamin/source/BenjaminCharacter.blend` in Blender for cleanup and export prep.
3. Use the Mesh2Motion/rigging handoff for the accepted game rig.
4. Install only the accepted rigged GLB under `assets/models/characters/benjamin/runtime/`.
5. Run `Godot: Import Assets`, then `GUT: Run Tests`.

`tools/generate_benjamin_character.py` is deprecated reference code. It now
defaults to archive output and refuses to run unless `BT_ALLOW_PLACEHOLDER_BENJAMIN=1`
is set.

Keep source `.blend` files under `source/`; that folder is ignored by Godot.
The runtime scene must load the accepted GLB, not a top-level `.blend` import.

## Runtime Animation Clips

The generated GLB must contain these animation names:

`idle`, `walk`, `walk_backward`, `walk_strafe_left`, `walk_strafe_right`, `sprint`, `jump`,
`fall`, `land`.

The focused GUT test that protects this is:

`tests/unit/test_character_runtime.gd`

## Godot Import

After regenerating the GLB, run:

- `Godot: Import Assets`

Godot scenes should keep referencing the runtime GLB path above, not files in
`source/` or `archive/`.

## Mesh2Motion

Mesh2Motion is the rigging/animation handoff path for Benjamin's accepted runtime.
Reject exports that visually collapse or explode, even if their animation names
look correct.
