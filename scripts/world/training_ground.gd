extends Node3D

const WORLD_SCENE := "res://scenes/World.tscn"

enum Lesson { WALK, RUN, JUMP, COMPLETE }

@onready var _player: CharacterBody3D = $Player
@onready var _prompt: Label = $TrainingHUD/Panel/Margin/Stack/Prompt
@onready var _detail: Label = $TrainingHUD/Panel/Margin/Stack/Detail
@onready var _progress: Label = $TrainingHUD/Panel/Margin/Stack/Progress
@onready var _walk_marker: Node3D = $Markers/WalkMarker
@onready var _jump_marker: Node3D = $Markers/JumpMarker
@onready var _run_markers: Array[Node3D] = [
	$Markers/RunMarker1,
	$Markers/RunMarker2,
	$Markers/RunMarker3,
	$Markers/RunMarker4,
]

var _lesson := Lesson.WALK
var _run_marker_index := 0
var _jump_started := false


func _ready() -> void:
	_set_lesson(Lesson.WALK)


func _physics_process(_delta: float) -> void:
	match _lesson:
		Lesson.WALK:
			if _flat_distance(_player.global_position, _walk_marker.global_position) < 1.4:
				_set_lesson(Lesson.RUN)

		Lesson.RUN:
			var target := _run_markers[_run_marker_index]
			if Input.is_action_pressed("run") and _flat_distance(_player.global_position, target.global_position) < 1.6:
				_run_marker_index += 1
				if _run_marker_index >= _run_markers.size():
					_set_lesson(Lesson.JUMP)
				else:
					_update_marker_visibility()
					_update_text()

		Lesson.JUMP:
			if Input.is_action_just_pressed("jump"):
				_jump_started = true
			if _jump_started and _player.is_on_floor() and _flat_distance(_player.global_position, _jump_marker.global_position) < 1.7:
				_set_lesson(Lesson.COMPLETE)

		Lesson.COMPLETE:
			if Input.is_action_just_pressed("ui_accept"):
				get_tree().change_scene_to_file(WORLD_SCENE)


func _set_lesson(next_lesson: Lesson) -> void:
	_lesson = next_lesson
	if _lesson == Lesson.RUN:
		_run_marker_index = 0
	if _lesson == Lesson.JUMP:
		_jump_started = false
	_update_marker_visibility()
	_update_text()


func _update_marker_visibility() -> void:
	_walk_marker.visible = _lesson == Lesson.WALK
	_jump_marker.visible = _lesson == Lesson.JUMP

	for index in _run_markers.size():
		_run_markers[index].visible = _lesson == Lesson.RUN and index == _run_marker_index


func _update_text() -> void:
	match _lesson:
		Lesson.WALK:
			_prompt.text = "Lesson 1: find Benjamin's walk."
			_detail.text = "Move to the blue mark. Let him take a few steady steps before you hurry him."
			_progress.text = "Walk"

		Lesson.RUN:
			_prompt.text = "Lesson 2: teach him to run around."
			_detail.text = "Hold Shift and guide Benjamin through the amber marks in order."
			_progress.text = "Run mark %d / %d" % [_run_marker_index + 1, _run_markers.size()]

		Lesson.JUMP:
			_prompt.text = "Lesson 3: teach him to jump cleanly."
			_detail.text = "Press Space before the practice bar and land on the green mark."
			_progress.text = "Jump"

		Lesson.COMPLETE:
			_prompt.text = "Benjamin remembers how to move."
			_detail.text = "Walk, run, turn, jump. Press Enter when he is ready for town."
			_progress.text = "Training complete"


func _flat_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x, a.z).distance_to(Vector2(b.x, b.z))
