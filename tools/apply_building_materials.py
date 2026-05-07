"""
apply_building_materials.py
Opens each building GLB in Blender, assigns a distinct PBR material, re-exports.

Run headlessly:
  blender --background --python tools/apply_building_materials.py
"""

import bpy
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (glb_path, mat_name, base_color_rgba, roughness, metallic)
BUILDINGS = [
    (
        "assets/models/buildings/church/church.glb",
        "mat_church",
        (0.60, 0.58, 0.54, 1.0),   # pale gray stone
        0.85, 0.0,
    ),
    (
        "assets/models/buildings/house_squat/house_squat.glb",
        "mat_house_squat",
        (0.90, 0.82, 0.60, 1.0),   # warm cream plaster
        0.90, 0.0,
    ),
    (
        "assets/models/buildings/house_commercial/house_commercial.glb",
        "mat_house_commercial",
        (0.62, 0.36, 0.24, 1.0),   # terracotta brick
        0.80, 0.0,
    ),
    (
        "assets/models/buildings/house_narrow/house_narrow.glb",
        "mat_house_narrow",
        (0.72, 0.76, 0.80, 1.0),   # muted blue-gray plaster
        0.88, 0.0,
    ),
]


def apply_material(glb_path, mat_name, base_color, roughness, metallic):
    abs_path = os.path.join(PROJECT_ROOT, glb_path)
    print(f"\n[apply_building_materials] Processing: {abs_path}")

    # Reset scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import GLB
    bpy.ops.import_scene.gltf(filepath=abs_path)

    # Create material
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    # Assign material to all mesh objects
    assigned = 0
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            # Clear existing materials and assign ours
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            assigned += 1

    if assigned == 0:
        print(f"  WARNING: no mesh objects found in {glb_path}")
        return

    print(f"  Assigned '{mat_name}' to {assigned} mesh object(s)")

    # Export back to same path
    bpy.ops.export_scene.gltf(
        filepath=abs_path,
        export_format="GLB",
        export_materials="EXPORT",
        export_texcoords=True,
        export_normals=True,
        export_skins=False,
        export_morph=False,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )
    print(f"  Exported → {abs_path}")


for args in BUILDINGS:
    apply_material(*args)

print("\n[apply_building_materials] All buildings done.")
