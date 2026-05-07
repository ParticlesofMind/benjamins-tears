extends CharacterBody3D

## Pedestrian NPC — wanders between random waypoints on the sidewalk.

enum State { IDLE, WALKING }

# --- tunables ---
@export var walk_speed: float = 1.4          # m/s
@export var idle_time_min: float = 1.5
@export var idle_time_max: float = 4.0
@export var waypoint_reach_dist: float = 0.5

# Sidewalk bounds (match RoadSurface dimensions)
const SIDEWALK_X_OPTIONS: Array[float] = [-4.25, 4.25]
const SIDEWALK_Z_MIN := -5.0
const SIDEWALK_Z_MAX := -135.0

const GRAVITY := 9.8

var _state: State = State.IDLE
var _target: Vector3 = Vector3.ZERO
var _idle_timer: float = 0.0
var _anim: AnimationPlayer
var _sidewalk_x: float = SIDEWALK_X_OPTIONS[0]


func _ready() -> void:
	_sidewalk_x = _nearest_sidewalk_x(global_position.x)
	# Find the AnimationPlayer inside the mesh child (same structure as player)
	var mesh_node := find_child("Mesh", true, false)
	if is_instance_valid(mesh_node):
		_anim = mesh_node.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if is_instance_valid(_anim):
		_set_loop("idle", true)
		_set_loop("walk", true)
		_anim.play("idle")
	_pick_new_target()


func _physics_process(delta: float) -> void:
	# Always apply gravity
	if not is_on_floor():
		velocity.y -= GRAVITY * delta

	match _state:
		State.IDLE:
			velocity.x = 0.0
			velocity.z = 0.0
			_idle_timer -= delta
			if _idle_timer <= 0.0:
				_pick_new_target()
				_state = State.WALKING
				_play("walk")

		State.WALKING:
			var flat_pos := Vector3(global_position.x, 0.0, global_position.z)
			var flat_target := Vector3(_target.x, 0.0, _target.z)
			var to_target := flat_target - flat_pos

			if to_target.length() < waypoint_reach_dist:
				velocity.x = 0.0
				velocity.z = 0.0
				_idle_timer = randf_range(idle_time_min, idle_time_max)
				_state = State.IDLE
				_play("idle")
			else:
				var dir := to_target.normalized()
				velocity.x = dir.x * walk_speed
				velocity.z = dir.z * walk_speed
				# Face direction of travel
				look_at(global_position + dir, Vector3.UP)

	move_and_slide()


func _pick_new_target() -> void:
	var z := randf_range(SIDEWALK_Z_MAX, SIDEWALK_Z_MIN)
	_target = Vector3(_sidewalk_x, 0.0, z)


func _nearest_sidewalk_x(x: float) -> float:
	var nearest := SIDEWALK_X_OPTIONS[0]
	var nearest_dist := absf(x - nearest)
	for sidewalk_x in SIDEWALK_X_OPTIONS:
		var dist := absf(x - sidewalk_x)
		if dist < nearest_dist:
			nearest = sidewalk_x
			nearest_dist = dist
	return nearest


func _set_loop(anim: String, looping: bool) -> void:
	if not is_instance_valid(_anim) or not _anim.has_animation(anim):
		return
	var res := _anim.get_animation(anim)
	if is_instance_valid(res):
		res.loop_mode = Animation.LOOP_LINEAR if looping else Animation.LOOP_NONE


func _play(anim: String) -> void:
	if not is_instance_valid(_anim):        return
	if not _anim.has_animation(anim):       return
	if _anim.current_animation == anim:     return
	_anim.play(anim)
