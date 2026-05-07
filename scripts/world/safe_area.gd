extends Area3D

signal player_entered(area_name: String)
signal player_exited(area_name: String)

@export var area_name: String = "Safe Area"


func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)


func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player") or body.name == "Player":
		player_entered.emit(area_name)


func _on_body_exited(body: Node3D) -> void:
	if body.is_in_group("player") or body.name == "Player":
		player_exited.emit(area_name)
