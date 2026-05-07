extends StaticBody3D

@export var width := 42.0
@export var length := 225.0
@export var columns := 34
@export var rows := 120
@export var center_z := -28.0


func _ready() -> void:
	_build_terrain()


func _build_terrain() -> void:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)

	var verts: Array[Vector3] = []
	verts.resize((columns + 1) * (rows + 1))

	for z_i in rows + 1:
		for x_i in columns + 1:
			var x := lerpf(-width * 0.5, width * 0.5, float(x_i) / float(columns))
			var z := lerpf(center_z + length * 0.5, center_z - length * 0.5, float(z_i) / float(rows))
			var h := _height_at(x, z)
			verts[_index(x_i, z_i)] = Vector3(x, h, z)

	for z_i in rows:
		for x_i in columns:
			var a := verts[_index(x_i, z_i)]
			var b := verts[_index(x_i + 1, z_i)]
			var c := verts[_index(x_i, z_i + 1)]
			var d := verts[_index(x_i + 1, z_i + 1)]
			_add_triangle(surface, a, c, b)
			_add_triangle(surface, b, c, d)

	var mesh := surface.commit()
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = "TerrainMesh"
	mesh_instance.mesh = mesh
	mesh_instance.set_surface_override_material(0, _make_ground_material())
	add_child(mesh_instance)

	var collision := CollisionShape3D.new()
	collision.name = "TerrainCollision"
	var shape := ConcavePolygonShape3D.new()
	shape.set_faces(mesh.get_faces())
	collision.shape = shape
	add_child(collision)


func _height_at(x: float, z: float) -> float:
	var path_dip := -0.18 * exp(-pow(x / 4.8, 2.0))
	var side_rise := 0.55 * pow(absf(x) / (width * 0.5), 2.2)
	var crater_dist := Vector2(x, z - 55.0).length()
	var crater_bowl := -1.15 * exp(-pow(crater_dist / 8.5, 2.0))
	var crater_rim := 0.42 * exp(-pow((crater_dist - 9.0) / 2.8, 2.0))
	var long_roll := 0.16 * sin(z * 0.055) + 0.08 * sin((x + z) * 0.11)
	return path_dip + side_rise + crater_bowl + crater_rim + long_roll


func _index(x_i: int, z_i: int) -> int:
	return z_i * (columns + 1) + x_i


func _add_triangle(surface: SurfaceTool, a: Vector3, b: Vector3, c: Vector3) -> void:
	var normal := (b - a).cross(c - a).normalized()
	surface.set_normal(normal)
	surface.add_vertex(a)
	surface.set_normal(normal)
	surface.add_vertex(b)
	surface.set_normal(normal)
	surface.add_vertex(c)


func _make_ground_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.16, 0.19, 0.14, 1.0)
	mat.roughness = 0.95
	return mat
