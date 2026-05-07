# Project Structure

This project keeps playable Godot resources separate from source art and old experiments.

## Canonical Layout

- `addons/` contains third-party Godot addons and small project-specific editor addons.
- `assets/` contains art, audio, animation, and other imported runtime assets.
- `scenes/` contains Godot scenes, grouped by role:
  - `scenes/atoms/` for small reusable scene prefabs.
  - `scenes/composites/` for assembled scene chunks.
  - root scene files for current entry points and screens.
- `scripts/` contains gameplay scripts grouped by feature:
  - `scripts/characters/` for player and NPC controllers.
  - `scripts/interaction/` for interactable actors and triggers.
  - `scripts/ui/` for menus, HUDs, and map overlays.
  - `scripts/world/` for world loop, terrain, safe-area, and training systems.
- `story/` contains narrative resources, dialogue files, and story autoload code.
- `tests/` contains automated GUT tests.
- `tools/` contains external pipeline scripts and local development helpers.
- `docs/` contains project documentation.
- `archive/` contains old experiments and failed exports that should remain available but not imported by Godot.

## Runtime Assets

- `assets/models/buildings/` contains building GLBs referenced by scenes.
- `assets/models/characters/*/runtime/` contains character GLBs used directly by scenes.
- Benjamin's active player model is `assets/models/characters/benjamin/runtime/benjamin_male_animated.glb`.

## Source Assets

- `assets/models/characters/benjamin/source/BenjaminCharacter.blend` is Benjamin's Character Creator/Blender source file.
- `tools/generate_benjamin_character.py` is deprecated placeholder generator code and must not overwrite active Benjamin assets.
- `assets/models/characters/*/source/` contains ignored source notes and handoff files that should not be referenced by scenes.
- `tools/setup_mesh2motion.py` keeps Mesh2Motion checkouts outside the project in `~/Library/Application Support/BenjaminTears/`, then launches the local app.
- `tools/blender_godot_exporter.py` installs as the Blender sidebar "Benjamin Pipeline" add-on for packing textures, exporting Mesh2Motion upload GLBs, and launching Mesh2Motion.
- `tools/blender_reduce_character_rig.py` can strip a Rigify-heavy export down to the gameplay deform rig used by Godot, but visually broken exports should be rejected rather than reduced.
- Mesh2Motion is the accepted rigging/runtime handoff path for Benjamin. See `docs/BENJAMIN_CHARACTER_PIPELINE.md`.

## Story

- `story/STORY.md` is the human-readable story outline.
- `story/act_*.tres` files are the runtime story resources loaded by `StoryManager`.
- `story/world_sketch.tldr` is the source sketch used for the journal map data.

## Archive

- `archive/` is Godot-ignored via `.gdignore`.
- Put failed exports, old experiments, and scratch assets there when they should remain available but not imported by Godot.

## Hygiene Rules

- Runtime scenes should reference cleaned assets under `assets/`, not root-level generated files.
- Temporary imports and generated experiments should move to `archive/` or be deleted.
- Python caches, browser traces, local virtual environments, Godot editor cache, and build exports stay out of git.
- Large binary art assets such as `.glb`, `.blend`, audio, and PNG textures are tracked with Git LFS.
