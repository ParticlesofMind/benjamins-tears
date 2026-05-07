extends Node3D

enum LoopState { CALM, WARNING, UBERFALL, AFTERMATH }

@export var crater_spawn := Vector3(0.0, 1.2, 55.0)
@export var calm_duration := 65.0
@export var warning_duration := 20.0
@export var uberfall_duration := 24.0
@export var aftermath_duration := 4.0

var _state := LoopState.CALM
var _state_time := 0.0
var _safe_area_count := 0
var _current_safe_area := ""
var _deaths := 0

@onready var _hud_title: Label = $LoopHUD/Panel/Margin/Stack/Title
@onready var _hud_detail: Label = $LoopHUD/Panel/Margin/Stack/Detail
@onready var _hud_timer: Label = $LoopHUD/Panel/Margin/Stack/Timer
@onready var _danger_tint: ColorRect = $LoopHUD/DangerTint
@onready var _player: CharacterBody3D = _find_player()


func _ready() -> void:
	if is_instance_valid(_player):
		_player.add_to_group("player")
		_player.global_position = crater_spawn
		_player.velocity = Vector3.ZERO

	for safe_area in get_tree().get_nodes_in_group("safe_area"):
		if safe_area.has_signal("player_entered"):
			safe_area.player_entered.connect(_on_safe_area_entered)
		if safe_area.has_signal("player_exited"):
			safe_area.player_exited.connect(_on_safe_area_exited)

	_enter_state(LoopState.CALM)


func _process(delta: float) -> void:
	_state_time -= delta

	match _state:
		LoopState.CALM:
			if _state_time <= 0.0:
				_enter_state(LoopState.WARNING)
		LoopState.WARNING:
			if _state_time <= 0.0:
				_enter_state(LoopState.UBERFALL)
		LoopState.UBERFALL:
			if not _is_player_safe():
				_kill_benjamin()
			elif _state_time <= 0.0:
				_enter_state(LoopState.AFTERMATH)
		LoopState.AFTERMATH:
			if _state_time <= 0.0:
				_enter_state(LoopState.CALM)

	_update_hud()


func request_uberfall_warning() -> void:
	if _state == LoopState.UBERFALL:
		return
	_enter_state(LoopState.WARNING)


func _enter_state(next_state: LoopState) -> void:
	_state = next_state
	match _state:
		LoopState.CALM:
			_state_time = calm_duration
		LoopState.WARNING:
			_state_time = warning_duration
		LoopState.UBERFALL:
			_state_time = uberfall_duration
		LoopState.AFTERMATH:
			_state_time = aftermath_duration


func _kill_benjamin() -> void:
	_deaths += 1
	if is_instance_valid(_player):
		_player.global_position = crater_spawn
		_player.velocity = Vector3.ZERO
	_safe_area_count = 0
	_current_safe_area = ""
	_enter_state(LoopState.AFTERMATH)


func _on_safe_area_entered(area_name: String) -> void:
	_safe_area_count += 1
	_current_safe_area = area_name


func _on_safe_area_exited(area_name: String) -> void:
	_safe_area_count = max(0, _safe_area_count - 1)
	if _current_safe_area == area_name:
		_current_safe_area = ""


func _is_player_safe() -> bool:
	return _safe_area_count > 0


func _find_player() -> CharacterBody3D:
	var found := find_child("Player", true, false)
	return found as CharacterBody3D


func _update_hud() -> void:
	var safe_text := "Safe: %s" % _current_safe_area if _is_player_safe() else "Outside"
	match _state:
		LoopState.CALM:
			_hud_title.text = "Crater"
			_hud_detail.text = "Reach the village. Learn where shelter is before the sky turns."
			_hud_timer.text = (
				"First Überfall in %s  |  %s  |  Deaths: %d"
				% [_format_time(_state_time), safe_text, _deaths]
			)
			_danger_tint.color = Color(0.0, 0.0, 0.0, 0.0)
		LoopState.WARNING:
			_hud_title.text = "The air changes"
			_hud_detail.text = "Find a marked shelter. No one survives an Überfall outside."
			_hud_timer.text = (
				"Impact in %s  |  %s  |  Deaths: %d"
				% [_format_time(_state_time), safe_text, _deaths]
			)
			_danger_tint.color = Color(0.45, 0.08, 0.02, 0.14)
		LoopState.UBERFALL:
			_hud_title.text = "Überfall"
			_hud_detail.text = "Stay inside. Surviving means waiting, not winning."
			_hud_timer.text = (
				"Wave passes in %s  |  %s  |  Deaths: %d"
				% [_format_time(_state_time), safe_text, _deaths]
			)
			_danger_tint.color = Color(0.7, 0.02, 0.0, 0.24)
		LoopState.AFTERMATH:
			_hud_title.text = "Aftermath"
			_hud_detail.text = "Benjamin opens his eyes again at the crater."
			_hud_timer.text = (
				"Resetting in %s  |  Deaths: %d" % [_format_time(_state_time), _deaths]
			)
			_danger_tint.color = Color(0.02, 0.0, 0.0, 0.18)


func _format_time(seconds: float) -> String:
	var clamped: int = max(0, int(ceil(seconds)))
	return "%02d:%02d" % [clamped / 60, clamped % 60]
