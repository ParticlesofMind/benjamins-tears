# Tools and Frameworks

This document tracks the important tools, addons, libraries, and workflow pieces used by
Benjamin's Tears. The goal is speed: each tool should remove repeated work, make content easier
to author, or protect the project from preventable breakage.

## Core Engine

### Godot 4.6.2

Godot is the runtime, editor, scene system, scripting environment, importer, and exporter for the
game. This project currently targets Godot 4.6 via `project.godot`.

Use Godot for:

- Scene composition.
- Character, area, collision, light, camera, and UI setup.
- Running and debugging the game.
- Importing runtime assets from `assets/`.
- Exporting playable builds.

Current main scene:

- `res://scenes/World.tscn`

Current project shape:

- Third-person exploration.
- Story resources and a `StoryManager` autoload.
- Journal map overlay.
- Uberfall survival loop.
- Town/street prototype with NPCs.

## Godot Addons

### Dialogue Manager 3.10.4

Path:

- `res://addons/dialogue_manager/`

Autoload:

- `DialogueManager`

Purpose:

- Author nonlinear dialogue in files instead of hard-coding conversations.
- Connect dialogue to game state through mutations and autoloads.
- Give story-heavy content a repeatable workflow.

Use it for:

- NPC conversations.
- Choice-driven dialogue.
- Short surreal observations.
- Dialogue that completes `StoryBeat` resources.
- Dialogue that adds journal/stringboard clues.

Do not use it for:

- Core story state ownership. `StoryManager` should stay the authority.
- Complex quest logic that belongs in gameplay scripts/resources.

Production rule:

- Dialogue files should trigger or request changes from `StoryManager`; they should not become a
  second story database.

### GUT 9.6.1

Path:

- `res://addons/gut/`

Config:

- `res://.gutconfig.json`

Purpose:

- Run automated tests inside Godot.
- Catch broken story resources, save/load bugs, interaction regressions, and loop-state mistakes.

Current tests:

- `res://tests/unit/test_story_resources.gd`
- `res://tests/unit/test_tooling_integrations.gd`

Current story/dialogue slice:

- `res://scenes/atoms/characters/Yumaya.tscn`
- `res://scripts/interaction/dialogue_actor.gd`
- `res://story/yumaya_first_meeting.dialogue`

VS Code task:

- `GUT: Run Tests`

Terminal command:

```sh
"/Applications/Godot.app/Contents/MacOS/Godot" --headless --path . -s res://addons/gut/gut_cmdln.gd -gexit -gdisable_colors
```

Use it for:

- Story resource loading.
- Tooling integration checks such as confirming LimboAI extension classes are available.
- `StoryManager` save/load.
- Uberfall state transitions.
- Safe area enter/exit behavior.
- Journal map zone/story status mapping.

### Phantom Camera 0.11

Path:

- `res://addons/phantom_camera/`

Autoload:

- `PhantomCameraManager`

Purpose:

- Speed up cinematic and authored camera behavior.
- Provide camera follow, framing, tweening, shake/noise, and camera switching tools.

Use it for:

- Surreal scene framing.
- Fall/crater sequences.
- Church and wall reveals.
- Camera transitions during dialogue or events.

Do not rush to replace the current player camera immediately. The existing `SpringArm3D` camera is
fine for movement prototyping. Use Phantom Camera when scenes need authored camera behavior.

### LimboAI 1.8.0

Path:

- `res://addons/limboai/`

Extension:

- `res://addons/limboai/bin/limboai.gdextension`

Purpose:

- Behavior trees and hierarchical state machines for reusable AI behavior.
- Built-in behavior tree editor, blackboards, debugger, and GDScript tasks/states.

Use it for:

- Enemy behavior once enemies exist.
- Beast patrol/chase/search/flee logic.
- NPC hide/flee behavior during Uberfall.
- Reusable behavior trees for multiple creature types.

Do not use it yet for:

- Simple sidewalk wandering. The current `scripts/characters/npc.gd` is enough.
- One-off scripted story events.

Production rule:

- First use LimboAI on one small enemy or NPC hiding prototype. Do not migrate all NPCs into
  behavior trees until that first prototype feels worth it.

### Terrain3D 1.0.2

Path:

- `res://addons/terrain_3d/`

Extension:

- `res://addons/terrain_3d/terrain.gdextension`

Purpose:

- Editable high-performance terrain for large outdoor zones.

Use it for:

- Drylands.
- Ruins.
- Crater outskirts.
- Coast or edge-of-town terrain.

Do not use it for:

- Dense interiors.
- Streets made from modular pieces.
- Areas that are faster to assemble from meshes.

### Godot AI 3.0.2

Path:

- `res://addons/godot_ai/`

Autoload:

- `_mcp_game_helper`

Purpose:

- Editor/runtime bridge for AI-assisted inspection and automation.
- Useful for screenshots, scene inspection, logs, and tool-assisted iteration.

Use it for:

- Fast debugging with AI/editor context.
- Inspecting scene state.
- Capturing errors and game logs.

### Meshy Godot Plugin 0.1.4

Path:

- `res://addons/meshy-godot-plugin/`

Purpose:

- Bridge Meshy-generated assets into Godot.

Use it for:

- Fast rough 3D asset generation.
- Prototype buildings/props before final cleanup.

Production rule:

- Meshy assets should still pass through a cleanup/runtime install step. Avoid letting temporary
  generated files become permanent scene dependencies.

### Pipeline Sync 1.0.0

Path:

- `res://addons/pipeline_sync/`

Purpose:

- Watches for a build trigger file and auto-reimports assets after the Blender pipeline finishes.

Use it for:

- Reducing friction between Blender exports and Godot imports.
- Keeping character/building iteration fast.

## External Content Pipeline

### Blender

Purpose:

- Source-authority modeling, cleanup, material packing, and export.

Important source file:

- `assets/models/characters/benjamin/source/BenjaminCharacter.blend`

Project-specific Blender helper:

- `tools/blender_godot_exporter.py`
- `tools/generate_benjamin_character.py` (deprecated placeholder generator; archive output only)

Use Blender for:

- Character source edits.
- Cleaning and exporting the Character Creator/Mesh2Motion Benjamin source.
- Prop cleanup.
- Collision mesh prep.
- GLB export sanity checks.

Production rule:

- Runtime scenes should reference assets under `assets/models/**/runtime/`, not source handoff
  experiments.

Benjamin pipeline doc:

- `docs/BENJAMIN_CHARACTER_PIPELINE.md`

### Mesh2Motion

Purpose:

- Optional character rigging and starter animation handoff for future experiments.

Use it for:

- NPC runtime rig and animations.
- Starter animation sets before custom polish.
- Reference/testing when a generated character needs external rigging.

Production rule:

- Once a character export is accepted, install only the final GLB under `runtime/`.
- Benjamin's active runtime must use the accepted Character Creator/Mesh2Motion rigged export.
- Reject visually broken rig exports even when their metadata and animation names look valid.

### Meshy

Purpose:

- Fast generated 3D concepts/assets.

Use it for:

- Early building and prop exploration.
- Placeholder architecture.
- Quick visual ideation.

Production rule:

- Treat Meshy output as draft material until cleaned, named, organized, and installed in the
  runtime asset tree.

## VS Code Setup

Workspace:

- `.vscode/benjamins_tears.code-workspace`

Recommended extensions:

- `geequlim.godot-tools`
- `alfish.godot-files`
- `EddieDover.gdscript-formatter-linter`
- `tldraw-org.tldraw-vscode`
- `ms-python.python`

### Godot Tools

Purpose:

- GDScript language support.
- Godot launch/debug integration.
- Scene/resource awareness.

Configured Godot path:

- `/Applications/Godot.app/Contents/MacOS/Godot`

### GDScript Formatter and Linter

Extension:

- `EddieDover.gdscript-formatter-linter`

Back-end package:

- `gdtoolkit==4.5.0`

Config:

- `requirements-dev.txt`
- `.vscode/settings.json`

Local tools:

- `.venv/bin/gdformat`
- `.venv/bin/gdlint`

Use it for:

- Keeping new scripts consistently formatted.
- Catching avoidable style and structural issues.

Current note:

- Existing gameplay scripts still have format/lint warnings. That is expected until a dedicated
  cleanup pass is done.

### tldraw VS Code

Purpose:

- Edit `.tldr` sketches directly in VS Code.

Current source sketch:

- `res://story/world_sketch.tldr`

Use it for:

- World layout.
- Journal map planning.
- Zone relationship sketches.

## VS Code Tasks

Tasks are defined in:

- `.vscode/tasks.json`

Current tasks:

- `Godot: Run Main Scene`
- `Godot: Run Current Scene`
- `Godot: Import Assets`
- `Godot: Smoke Test Main Scene`
- `GDScript: Lint`
- `GDScript: Format Check`
- `GUT: Run Tests`

Use these instead of remembering command-line details.

Note:

- Dialogue Manager `.dialogue` files are imported resources. Run `Godot: Import Assets` before
  headless smoke tests or GUT on a fresh checkout. The smoke and GUT tasks already do this.

## Current Autoloads

Configured in `project.godot`:

- `DialogueManager`
- `PhantomCameraManager`
- `StoryManager`
- `_mcp_game_helper`

Story authority:

- `StoryManager`

Dialogue authority:

- Dialogue Manager should present dialogue and call into game state. It should not replace
  `StoryManager`.

Camera authority:

- Current player movement can keep using its existing camera.
- Phantom Camera should be introduced for authored shots and camera transitions.

AI authority:

- Simple behaviors can stay in normal scripts.
- LimboAI should handle reusable behavior-tree/state-machine AI once enemies or richer NPC states
  exist.

## Current Vertical Slice

The current production move is a vertical slice, not more tooling.

Target loop:

1. Benjamin emerges at the crater.
2. Player reaches town.
3. Player talks to Yumaya near the church using Dialogue Manager.
4. Dialogue completes `spot_yumaya`.
5. The journal map changes based on that beat.
6. The Uberfall warning begins from dialogue.
7. Player reaches a safe area and survives.
8. The next clue/zone unlocks.

This loop proves the whole game shape:

- Movement.
- World traversal.
- Dialogue.
- Story state.
- Journal feedback.
- Survival pressure.
- Progression.

## Tooling Rule

Every new tool should answer one of these questions:

- Does it let us author content faster?
- Does it make repeated content safer?
- Does it reduce manual asset pipeline work?
- Does it protect a fragile system with tests?

If the answer is no, wait.
