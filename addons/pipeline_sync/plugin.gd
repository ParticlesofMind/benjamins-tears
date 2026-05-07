@tool
extends EditorPlugin

## PipelineSync — auto-reimports assets when the Blender build pipeline finishes.
##
## The Blender addon (blender_godot_exporter.py) and the terminal watcher
## (tools/watch_and_build.py) both write a file called `pipeline_sync_trigger`
## to the project root when a build completes.  This plugin detects that file,
## deletes it, and calls EditorInterface.get_resource_filesystem().scan() so
## Godot picks up the new GLB immediately — no manual focus switching needed.

const TRIGGER_FILE := "res://pipeline_sync_trigger"

var _timer: Timer


func _enter_tree() -> void:
	_timer = Timer.new()
	_timer.wait_time = 0.5
	_timer.autostart = true
	_timer.timeout.connect(_check_trigger)
	add_child(_timer)
	print("[PipelineSync] Active — watching for pipeline trigger.")


func _exit_tree() -> void:
	if is_instance_valid(_timer):
		_timer.queue_free()


func _check_trigger() -> void:
	if not FileAccess.file_exists(TRIGGER_FILE):
		return

	# Delete the trigger first so a stale file can't fire twice
	var abs_path := ProjectSettings.globalize_path(TRIGGER_FILE)
	var err := DirAccess.remove_absolute(abs_path)
	if err != OK:
		push_warning("[PipelineSync] Could not delete trigger file: " + abs_path)

	print("[PipelineSync] Build complete — rescanning project filesystem...")
	EditorInterface.get_resource_filesystem().scan()
	print("[PipelineSync] Rescan triggered. Godot will reimport changed assets.")
