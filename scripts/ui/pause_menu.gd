extends CanvasLayer

const MAIN_MENU_SCENE := "res://scenes/MainMenu.tscn"

@onready var _panel: Control = $Panel
@onready var _overlay: ColorRect = $Overlay
@onready var _resume_btn: Button = $Panel/VBox/Resume
@onready var _quit_btn: Button = $Panel/VBox/QuitToMenu


func _ready() -> void:
	# Must process while game is paused
	process_mode = Node.PROCESS_MODE_ALWAYS
	_overlay.visible = false
	_panel.visible = false
	_resume_btn.pressed.connect(_resume)
	_quit_btn.pressed.connect(_quit_to_menu)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		if _panel.visible:
			_resume()
		else:
			_open()
		get_viewport().set_input_as_handled()


func _open() -> void:
	_overlay.visible = true
	_panel.visible = true
	get_tree().paused = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	_resume_btn.grab_focus()


func _resume() -> void:
	_overlay.visible = false
	_panel.visible = false
	get_tree().paused = false
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _quit_to_menu() -> void:
	_overlay.visible = false
	_panel.visible = false
	get_tree().paused = false
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	get_tree().change_scene_to_file(MAIN_MENU_SCENE)
