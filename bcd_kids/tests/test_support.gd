# Shared assertions and helpers for the headless Godot test scripts.
class_name GodotTestSupport
extends RefCounted

var assertions := 0
var failures: Array[String] = []


func expect(condition: bool, label: String) -> void:
	assertions += 1
	if not condition:
		failures.append(label)


func equal(actual: Variant, expected: Variant, label: String) -> void:
	expect(actual == expected, "%s (expected %s, got %s)" % [label, expected, actual])


func approximately(actual: float, expected: float, label: String, tolerance := 0.001) -> void:
	expect(
		abs(actual - expected) <= tolerance,
		"%s (expected %s, got %s)" % [label, expected, actual]
	)


func wait_frames(tree: SceneTree, count := 1) -> void:
	for _index in range(count):
		await tree.process_frame


func finish(tree: SceneTree) -> void:
	if failures.is_empty():
		print("Godot tests passed (%d assertions)" % assertions)
		tree.quit(0)
		return

	for failure in failures:
		push_error("Godot test failed: " + failure)
	print("Godot tests failed (%d/%d assertions)" % [failures.size(), assertions])
	tree.quit(1)


func expect_scene_load(path: String, expected_type: String) -> Node:
	var packed = load(path)
	expect(packed != null, "scene loads: " + path)
	if packed == null:
		return null

	var instance: Node = packed.instantiate()
	expect(instance != null, "scene instantiates: " + path)
	if instance != null:
		expect(instance.get_class() == expected_type, "scene root type: " + path)
	return instance


func free_nodes(tree: SceneTree, nodes: Array) -> void:
	for node_variant in nodes:
		if node_variant is Node and is_instance_valid(node_variant):
			(node_variant as Node).queue_free()
	await wait_frames(tree)
