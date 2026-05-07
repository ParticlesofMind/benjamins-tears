extends Area3D

@export var dialogue_resource: DialogueResource
@export var start_title := "start"
@export var prompt_text := "E Talk"
@export var interact_action: StringName = &"interact"
@export var face_player := true

var _player: Node3D
var _talking := false

@onready var _prompt: Label3D = get_node_or_null("Prompt")


func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	if is_instance_valid(_prompt):
		_prompt.text = prompt_text
		_prompt.visible = false


func _unhandled_input(event: InputEvent) -> void:
	if _talking or not is_instance_valid(_player):
		return
	if event.is_action_pressed(interact_action):
		_start_dialogue()
		get_viewport().set_input_as_handled()


func _on_body_entered(body: Node3D) -> void:
	if not _is_player(body):
		return
	_player = body
	if is_instance_valid(_prompt) and not _talking:
		_prompt.visible = true


func _on_body_exited(body: Node3D) -> void:
	if body != _player:
		return
	_player = null
	if is_instance_valid(_prompt):
		_prompt.visible = false


func _start_dialogue() -> void:
	if not is_instance_valid(dialogue_resource):
		push_warning("%s has no dialogue resource." % name)
		return

	_talking = true
	if face_player:
		_face_player()
	if is_instance_valid(_prompt):
		_prompt.visible = false

	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	var dialogue_manager := Engine.get_singleton("DialogueManager")
	if dialogue_manager.has_signal(&"dialogue_ended"):
		dialogue_manager.dialogue_ended.connect(_on_dialogue_ended, CONNECT_ONE_SHOT)
	dialogue_manager.show_dialogue_balloon(
		dialogue_resource, start_title, [get_tree().current_scene, self]
	)


func _on_dialogue_ended(_resource: DialogueResource) -> void:
	_talking = false
	if is_instance_valid(_player) and is_instance_valid(_prompt):
		_prompt.visible = true
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _is_player(body: Node3D) -> bool:
	return body.is_in_group(&"player") or body.name == &"Player"


func _face_player() -> void:
	if not is_instance_valid(_player):
		return
	var target := _player.global_position
	target.y = global_position.y
	if global_position.distance_squared_to(target) > 0.01:
		look_at(target, Vector3.UP)
