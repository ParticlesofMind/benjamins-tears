extends CharacterBody3D

## Controls: WASD/arrow keys = move, Space = jump, Shift = sprint

const WALK_SPEED        := 4.0
const SPRINT_SPEED      := 7.0
const JUMP_VELOCITY     := 5.5
const GRAVITY           := 9.8
const MOUSE_SENSITIVITY := 0.003

@onready var spring_arm: SpringArm3D = $SpringArm3D
@onready var mesh: Node3D            = $Mesh

var _anim: AnimationPlayer
var _cam_yaw:   float = 0.0
var _cam_pitch: float = -0.17
var _land_timer: float = 0.0
var _was_on_floor: bool = true


func _ready() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	_anim = mesh.find_child("AnimationPlayer", true, false) as AnimationPlayer
	_play("idle")


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		_cam_yaw   -= event.relative.x * MOUSE_SENSITIVITY
		_cam_pitch  = clamp(_cam_pitch - event.relative.y * MOUSE_SENSITIVITY, -0.6, 0.4)
		spring_arm.rotation.y = _cam_yaw
		spring_arm.rotation.x = _cam_pitch
	if event.is_action_pressed("ui_cancel"):
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta

	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY

	var input    := Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var sprinting := Input.is_action_pressed("run")
	var speed    := SPRINT_SPEED if sprinting else WALK_SPEED

	if input.length() > 0.1:
		var dir := (Basis(Vector3.UP, _cam_yaw) * Vector3(input.x, 0.0, input.y)).normalized()
		velocity.x = dir.x * speed
		velocity.z = dir.z * speed
		mesh.look_at(mesh.global_position + dir, Vector3.UP)
	else:
		velocity.x = move_toward(velocity.x, 0.0, speed * 3.0)
		velocity.z = move_toward(velocity.z, 0.0, speed * 3.0)

	move_and_slide()

	var on_floor := is_on_floor()
	if on_floor and not _was_on_floor:
		_land_timer = 0.45
	_land_timer   = max(0.0, _land_timer - delta)
	_was_on_floor = on_floor

	_update_anim(input, sprinting, on_floor)


func _update_anim(input: Vector2, sprinting: bool, on_floor: bool) -> void:
	if not on_floor:
		var airborne_anim := "jump" if velocity.y > 0.0 else "fall"
		if airborne_anim == "fall" and is_instance_valid(_anim) and not _anim.has_animation("fall"):
			airborne_anim = "jump"
		_play(airborne_anim)
	elif _land_timer > 0.0:
		_play("land")
	elif input.length() > 0.1:
		_play(_locomotion_anim(input, sprinting))
	else:
		_play("idle")


func _locomotion_anim(input: Vector2, sprinting: bool) -> String:
	if sprinting and input.y < -0.35 and absf(input.x) < 0.45:
		return "sprint"
	if input.y > 0.35 and input.y > absf(input.x):
		return "walk_backward"
	if input.x < -0.35 and absf(input.x) >= absf(input.y):
		return "walk_strafe_left"
	if input.x > 0.35 and absf(input.x) >= absf(input.y):
		return "walk_strafe_right"
	return "walk"


const LOOP_ANIMS := ["idle", "walk", "walk_backward", "walk_strafe_left", "walk_strafe_right", "sprint"]

func _play(anim: String) -> void:
	if not is_instance_valid(_anim) or not _anim.has_animation(anim) or _anim.current_animation == anim:
		return
	var res := _anim.get_animation(anim)
	if res:
		res.loop_mode = Animation.LOOP_LINEAR if anim in LOOP_ANIMS else Animation.LOOP_NONE
	_anim.play(anim)
