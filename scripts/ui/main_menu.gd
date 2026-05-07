extends Control

const WORLD_SCENE := "res://scenes/World.tscn"

@onready var _new_game_btn: Button = $VBox/Buttons/NewGame
@onready var _quit_btn: Button = $VBox/Buttons/Quit


func _ready() -> void:
	_new_game_btn.pressed.connect(_on_new_game)
	_quit_btn.pressed.connect(_on_quit)
	_new_game_btn.grab_focus()


func _on_new_game() -> void:
	get_tree().change_scene_to_file(WORLD_SCENE)


func _on_quit() -> void:
	get_tree().quit()
