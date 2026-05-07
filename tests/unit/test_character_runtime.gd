extends GutTest

const BENJAMIN_RUNTIME_DIR := "res://assets/models/characters/benjamin/runtime"
const BENJAMIN_RUNTIME_FILE := "benjamin_male_animated.glb"
const REQUIRED_PLAYER_ANIMS := [
	&"idle",
	&"walk",
	&"walk_backward",
	&"walk_strafe_left",
	&"walk_strafe_right",
	&"sprint",
	&"jump",
	&"fall",
	&"land",
]
const REQUIRED_CHARACTER_CREATOR_NODES := [
	&"Benjamin_Body",
	&"Benjamin_Fedora",
	&"Benjamin_Suit",
	&"Benjamin_Shoes",
]
const FORBIDDEN_PLACEHOLDER_NODES := [
	&"Benjamin_Chest",
	&"Benjamin_Nose",
	&"Benjamin_Hair_Cap",
]


func test_benjamin_runtime_loads_with_player_animations() -> void:
	var runtime_path := "%s/%s" % [BENJAMIN_RUNTIME_DIR, BENJAMIN_RUNTIME_FILE]
	var scene := load(runtime_path) as PackedScene
	assert_not_null(scene)

	var instance := scene.instantiate()
	add_child_autofree(instance)

	var animation_player := instance.find_child("AnimationPlayer", true, false) as AnimationPlayer
	assert_not_null(animation_player)
	for animation_name in REQUIRED_PLAYER_ANIMS:
		assert_true(
			animation_player.has_animation(animation_name),
			"Benjamin runtime should include %s." % animation_name
		)

	for node_name in REQUIRED_CHARACTER_CREATOR_NODES:
		assert_not_null(
			instance.find_child(String(node_name), true, false),
			"Benjamin runtime should include Character Creator mesh node %s." % node_name
		)

	for node_name in FORBIDDEN_PLACEHOLDER_NODES:
		assert_null(
			instance.find_child(String(node_name), true, false),
			"Benjamin runtime should not use procedural placeholder node %s." % node_name
		)
