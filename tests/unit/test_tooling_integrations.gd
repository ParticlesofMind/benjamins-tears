extends GutTest


func test_limboai_extension_classes_are_available() -> void:
	assert_true(ClassDB.class_exists("BehaviorTree"), "LimboAI should register BehaviorTree.")
	assert_true(ClassDB.class_exists("BTPlayer"), "LimboAI should register BTPlayer.")
