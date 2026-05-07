extends GutTest


class WarningProbe:
	var requested := false

	func request_uberfall_warning() -> void:
		requested = true


const ACT_PATHS := [
	"res://story/act_01_the_fall.tres",
	"res://story/act_02_homecoming.tres",
	"res://story/act_03_renovations.tres",
	"res://story/act_04_uberfall.tres",
	"res://story/act_05_boy_meets_girl.tres",
	"res://story/act_06_cult_of_fire.tres",
	"res://story/act_07_edge_of_town.tres",
	"res://story/act_08_the_keyhole.tres",
]
const YUMAYA_DIALOGUE_PATH := "res://story/yumaya_first_meeting.dialogue"

var _restore_spot_yumaya: Variant = null


func after_each() -> void:
	if _restore_spot_yumaya == null:
		return
	var beat := StoryManager.find_beat(&"spot_yumaya")
	if beat:
		beat.completed = _restore_spot_yumaya
		StoryManager.call("_save_progress")
	_restore_spot_yumaya = null


func test_story_acts_load() -> void:
	for path in ACT_PATHS:
		var act: StoryAct = load(path) as StoryAct
		assert_not_null(act, path)


func test_story_outline_has_runtime_beats() -> void:
	var total_beats := 0
	for path in ACT_PATHS:
		var act: StoryAct = load(path) as StoryAct
		total_beats += act.beats.size()
	assert_gt(total_beats, 0, "Story resources should contain at least one runtime beat.")


func test_yumaya_first_meeting_dialogue_loads() -> void:
	var resource := load(YUMAYA_DIALOGUE_PATH) as DialogueResource
	assert_not_null(resource)
	assert_true(resource.titles.has("start"), "Yumaya dialogue should have a start title.")


func test_yumaya_first_meeting_runs_story_mutations() -> void:
	var resource := load(YUMAYA_DIALOGUE_PATH) as DialogueResource
	var beat := StoryManager.find_beat(&"spot_yumaya")
	assert_not_null(beat)

	_restore_spot_yumaya = beat.completed
	beat.completed = false

	var warning_probe := WarningProbe.new()
	var line := await resource.get_next_dialogue_line("start", [warning_probe])
	var guard := 0
	while line != null and guard < 12:
		guard += 1
		line = await resource.get_next_dialogue_line(line.next_id, [warning_probe])

	assert_lt(guard, 12, "Yumaya dialogue should reach END.")
	assert_true(StoryManager.is_beat_done(&"spot_yumaya"))
	assert_true(warning_probe.requested, "Yumaya dialogue should request the Uberfall warning.")
