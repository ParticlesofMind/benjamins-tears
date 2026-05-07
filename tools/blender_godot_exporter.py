"""
Benjamin Character Pipeline Blender Addon

Keeps Benjamin's source art workflow inside Blender:
- pack MPFB textures so the .blend is self-contained
- export a clean static GLB for Mesh2Motion
- set up/launch the local Mesh2Motion app
- optionally export the animated runtime GLB to Godot later
"""

bl_info = {
    "name": "Benjamin Character Pipeline",
    "author": "Benjamin's Tears Pipeline",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Benjamin",
    "description": "MPFB source cleanup, Mesh2Motion handoff, and optional Godot runtime export",
    "category": "Import-Export",
}

import bmesh
import bpy
import json
import os
import subprocess
import sys
import webbrowser
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.app.handlers import persistent

_mesh2motion_proc: "subprocess.Popen | None" = None
_mesh2motion_auto_proc: "subprocess.Popen | None" = None
_blend_session_mtime: "float | None" = None

PROJECT_ROOT = "/Users/benjaminjacklaubacher/benjamin's-tears"
TOOL_CACHE_ROOT = os.path.expanduser("~/Library/Application Support/BenjaminTears")
DEFAULT_MESH2MOTION_TARGETS = (
    "Benjamin_MPFB_Tall_Caucasian_Male",
    "Benjamin_MPFB_MaleElegantSuit01",
    "Benjamin_MPFB_BlackFormalShoes04",
    "Benjamin_MPFB_DeepBlueEyes",
    "Benjamin_MPFB_BushyDarkEyebrows",
    "Benjamin_MPFB_ShortDarkHair",
    "Benjamin_MPFB_HatHair",
    "Benjamin_MPFB_Fedora01",
)
BODY_INSPECTION_BODY_OBJECT = "Benjamin_MPFB_Tall_Caucasian_Male"
BODY_INSPECTION_CLOTHING_OBJECTS = (
    "Benjamin_MPFB_MaleElegantSuit01",
    "Benjamin_MPFB_BlackFormalShoes04",
)
DEFAULT_MESH2MOTION_APP_PATH = TOOL_CACHE_ROOT + "/mesh2motion-app"
DEFAULT_MESH2MOTION_ASSETS_PATH = TOOL_CACHE_ROOT + "/mesh2motion-assets"
DEFAULT_MESH2MOTION_UPLOAD_PATH = (
    PROJECT_ROOT + "/assets/models/characters/benjamin/source/BenjaminCharacter_mesh2motion_upload.glb"
)
DEFAULT_MESH2MOTION_FULL_BODY_UPLOAD_PATH = (
    PROJECT_ROOT + "/assets/models/characters/benjamin/source/BenjaminCharacter_mesh2motion_full_body_upload.glb"
)
DEFAULT_MESH2MOTION_RIGGED_PATH = (
    PROJECT_ROOT + "/assets/models/characters/benjamin/source/BenjaminCharacter_mesh2motion_rigged.glb"
)
DEFAULT_MESH2MOTION_FULL_BODY_RIGGED_PATH = (
    PROJECT_ROOT + "/assets/models/characters/benjamin/source/BenjaminCharacter_mesh2motion_full_body_rigged.glb"
)
DEFAULT_GODOT_MODELS_PATH = PROJECT_ROOT + "/assets/models/characters/benjamin/runtime"


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

class GodotExporterPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    mesh2motion_app_path: StringProperty(
        name="Mesh2Motion App Checkout",
        description="Local Mesh2Motion/mesh2motion-app checkout outside the Godot project",
        default=DEFAULT_MESH2MOTION_APP_PATH,
        subtype="DIR_PATH",
    )

    mesh2motion_assets_path: StringProperty(
        name="Mesh2Motion Blender Assets Checkout",
        description="Local Mesh2Motion/mesh2motion-assets checkout outside the Godot project",
        default=DEFAULT_MESH2MOTION_ASSETS_PATH,
        subtype="DIR_PATH",
    )

    mesh2motion_upload_path: StringProperty(
        name="Mesh2Motion Upload GLB",
        description="Clean static GLB exported from the MPFB source meshes for rigging in Mesh2Motion",
        default=DEFAULT_MESH2MOTION_UPLOAD_PATH,
        subtype="FILE_PATH",
    )

    mesh2motion_rigged_output_path: StringProperty(
        name="Mesh2Motion Rigged GLB",
        description="First-pass rigged GLB downloaded from the automated Mesh2Motion browser flow",
        default=DEFAULT_MESH2MOTION_RIGGED_PATH,
        subtype="FILE_PATH",
    )

    mesh2motion_full_body_upload_path: StringProperty(
        name="Mesh2Motion Full Body Upload GLB",
        description="Static Mesh2Motion upload GLB that keeps Benjamin's body under clothing",
        default=DEFAULT_MESH2MOTION_FULL_BODY_UPLOAD_PATH,
        subtype="FILE_PATH",
    )

    mesh2motion_full_body_rigged_output_path: StringProperty(
        name="Mesh2Motion Full Body Rigged GLB",
        description="Rigged Mesh2Motion output that keeps Benjamin's body under clothing",
        default=DEFAULT_MESH2MOTION_FULL_BODY_RIGGED_PATH,
        subtype="FILE_PATH",
    )

    mesh2motion_port: IntProperty(
        name="Mesh2Motion Local Port",
        description="Port used by the local Vite development server",
        default=5173,
        min=1024,
        max=65535,
    )

    godot_models_path: StringProperty(
        name="Godot Runtime Character Folder",
        description="Absolute path to the Godot runtime character export folder",
        default=DEFAULT_GODOT_MODELS_PATH,
        subtype="DIR_PATH",
    )

    godot_project_path: StringProperty(
        name="Godot Project Root",
        description="Absolute path to the Godot project root (the folder containing project.godot). "
                    "Used to write the pipeline_sync_trigger file so Godot auto-reimports on build.",
        default=PROJECT_ROOT,
        subtype="DIR_PATH",
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Mesh2Motion")
        layout.prop(self, "mesh2motion_app_path")
        layout.prop(self, "mesh2motion_assets_path")
        layout.prop(self, "mesh2motion_upload_path")
        layout.prop(self, "mesh2motion_rigged_output_path")
        layout.prop(self, "mesh2motion_full_body_upload_path")
        layout.prop(self, "mesh2motion_full_body_rigged_output_path")
        layout.prop(self, "mesh2motion_port")
        layout.separator()
        layout.label(text="Godot Runtime")
        layout.prop(self, "godot_models_path")
        layout.prop(self, "godot_project_path")


# ---------------------------------------------------------------------------
# Scene-level settings (stored on the scene so they persist per .blend)
# ---------------------------------------------------------------------------

class GodotExporterSettings(bpy.types.PropertyGroup):
    mesh2motion_target_names: StringProperty(
        name="Source Mesh Names",
        description="Comma-separated MPFB source meshes used for clean Mesh2Motion uploads",
        default=",".join(DEFAULT_MESH2MOTION_TARGETS),
    )
    mesh2motion_prune_clothed_body: BoolProperty(
        name="Prune Hidden Body Faces",
        description="Remove body faces covered by the suit from the upload duplicate only",
        default=True,
    )
    mesh2motion_join_upload_meshes: BoolProperty(
        name="Join Upload Meshes",
        description="Join the temporary upload duplicates into one mesh before exporting",
        default=False,
    )
    auto_export: BoolProperty(
        name="Auto-export on Save",
        description="Automatically export to Godot every time you save this .blend file",
        default=False,
    )
    export_filename: StringProperty(
        name="Export Filename",
        description="Name of the .glb file (without extension)",
        default="",
    )
    export_selection_only: BoolProperty(
        name="Selection Only",
        description="Export only selected objects instead of the whole scene",
        default=False,
    )


# ---------------------------------------------------------------------------
# Mesh2Motion source workflow
# ---------------------------------------------------------------------------

def _safe_path(path: str) -> str:
    return bpy.path.abspath(path) if path else path


def _addon_prefs(context):
    addon = context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def _pref(context, attr: str, default):
    prefs = _addon_prefs(context)
    return getattr(prefs, attr, default) if prefs else default


def _path_env() -> dict[str, str]:
    env = os.environ.copy()
    extra = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    env["PATH"] = extra + os.pathsep + env.get("PATH", "")
    return env


def _current_blend_mtime(filepath: str | None = None) -> float | None:
    path = filepath or bpy.data.filepath
    if not path:
        return None
    try:
        return os.path.getmtime(bpy.path.abspath(path))
    except OSError:
        return None


def _record_blend_session_mtime(filepath: str | None = None) -> None:
    global _blend_session_mtime
    _blend_session_mtime = _current_blend_mtime(filepath)


def _blend_disk_status() -> dict[str, object]:
    disk_mtime = _current_blend_mtime()
    if disk_mtime is None or _blend_session_mtime is None:
        return {"state": "unknown", "disk_mtime": disk_mtime, "session_mtime": _blend_session_mtime}
    if disk_mtime > _blend_session_mtime + 0.5:
        return {"state": "disk_newer", "disk_mtime": disk_mtime, "session_mtime": _blend_session_mtime}
    return {"state": "current", "disk_mtime": disk_mtime, "session_mtime": _blend_session_mtime}


def _get_setup_script_path() -> str:
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(tools_dir, "setup_mesh2motion.py")


def _get_mesh2motion_auto_rig_script_path() -> str:
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(tools_dir, "mesh2motion_auto_rig.py")


def _pack_external_images() -> tuple[int, list[str]]:
    packed = 0
    missing = []
    for image in bpy.data.images:
        if image.packed_file or not image.filepath:
            continue
        filepath = bpy.path.abspath(image.filepath)
        if not os.path.exists(filepath):
            missing.append(image.name)
            continue
        try:
            image.pack()
            packed += 1
        except Exception:
            missing.append(image.name)
    return packed, missing


def _target_source_meshes(context) -> tuple[list[bpy.types.Object], list[str]]:
    settings = context.scene.godot_exporter
    names = [name.strip() for name in settings.mesh2motion_target_names.split(",") if name.strip()]
    objects = []
    missing = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            objects.append(obj)
        else:
            missing.append(name)
    return objects, missing


def _copy_materials(source: bpy.types.Object, target: bpy.types.Object) -> None:
    if target.data.materials:
        return
    for material in source.data.materials:
        target.data.materials.append(material)


def _find_image(*names: str) -> bpy.types.Image | None:
    for candidate in names:
        image = bpy.data.images.get(candidate)
        if image:
            return image
    lowered = {name.lower() for name in names}
    for image in bpy.data.images:
        if image.name.lower() in lowered:
            return image
    return None


def _m2m_image_material(name: str, color: tuple[float, float, float, float], image: bpy.types.Image | None) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    material.blend_method = "OPAQUE"
    material.use_screen_refraction = False
    material.show_transparent_back = False

    nodes = material.node_tree.nodes
    for node in list(nodes):
        nodes.remove(node)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    shader = nodes.new(type="ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.72
    shader.inputs["Alpha"].default_value = 1.0
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    if image:
        tex = nodes.new(type="ShaderNodeTexImage")
        tex.image = image
        tex.extension = "REPEAT"
        # Do not connect image alpha. Mesh2Motion/three.js sorts transparent
        # human face parts poorly, so uploads must remain fully opaque.
        material.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])

    return material


def _mesh2motion_safe_material(original_name: str) -> bpy.types.Material:
    lower = original_name.lower()
    if "male_elegantsuit" in lower:
        return _m2m_image_material(
            "BT_M2M_Suit_Opaque",
            (0.035, 0.034, 0.032, 1.0),
            _find_image("male_elegantsuit01_diffuse.png", "male_elegantsuit01_diffuse"),
        )
    if "shoes" in lower:
        return _m2m_image_material(
            "BT_M2M_Shoes_Opaque",
            (0.025, 0.018, 0.012, 1.0),
            _find_image("shoes04_diffuse.png", "shoes04_diffuse"),
        )
    if "fedora" in lower:
        return _m2m_image_material(
            "BT_M2M_Fedora_Opaque",
            (0.50, 0.48, 0.44, 1.0),
            _find_image("fedora_diffuse.png", "fedora_diffuse"),
        )
    if "eyebrow" in lower:
        return _m2m_image_material(
            "BT_M2M_Eyebrows_Opaque",
            (0.025, 0.018, 0.012, 1.0),
            _find_image("eyebrow012.png", "eyebrow012"),
        )
    if "high-poly" in lower or "eye" in lower:
        return _m2m_image_material(
            "BT_M2M_Eyes_Opaque",
            (0.86, 0.89, 0.95, 1.0),
            _find_image("deepblue_eye.png", "deepblue_eye"),
        )
    if "short01" in lower or "hair" in lower:
        return _m2m_image_material(
            "BT_M2M_Hair_Opaque",
            (0.05, 0.025, 0.015, 1.0),
            _find_image("short01_diffuse.png", "short01_diffuse"),
        )
    if "lips" in lower:
        return _m2m_image_material(
            "BT_M2M_Lips_Opaque",
            (0.56, 0.30, 0.27, 1.0),
            None,
        )
    if "fingernails" in lower or "toenails" in lower:
        return _m2m_image_material(
            "BT_M2M_Nails_Opaque",
            (0.80, 0.66, 0.58, 1.0),
            None,
        )
    if "body" in lower or "ears" in lower:
        return _m2m_image_material(
            "BT_M2M_Skin_Opaque",
            (0.77, 0.58, 0.46, 1.0),
            _find_image("young_lightskinned_male_diffuse2.png", "young_lightskinned_male_diffuse2"),
        )
    return _m2m_image_material("BT_M2M_Neutral_Opaque", (0.55, 0.55, 0.55, 1.0), None)


def _replace_with_mesh2motion_safe_materials(obj: bpy.types.Object) -> None:
    for slot in obj.material_slots:
        if slot.material:
            slot.material = _mesh2motion_safe_material(slot.material.name)


def _body_inspection_material() -> bpy.types.Material:
    material = bpy.data.materials.get("BT_BodyInspection_Clothes_Ghost")
    if material is None:
        material = bpy.data.materials.new("BT_BodyInspection_Clothes_Ghost")
    material.diffuse_color = (0.08, 0.13, 0.18, 0.28)
    material.use_nodes = True
    material.blend_method = "BLEND"
    material.show_transparent_back = True

    nodes = material.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (0.08, 0.13, 0.18, 0.28)
        shader.inputs["Alpha"].default_value = 0.28
        shader.inputs["Roughness"].default_value = 0.65
    return material


def _temporary_mesh_duplicate(source: bpy.types.Object, collection: bpy.types.Collection) -> bpy.types.Object:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = source.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated,
        depsgraph=depsgraph,
        preserve_all_data_layers=True,
    )
    mesh.name = f"{source.name}_Mesh2MotionMesh"

    duplicate = bpy.data.objects.new(f"{source.name}_Mesh2Motion", mesh)
    duplicate.matrix_world = source.matrix_world.copy()
    collection.objects.link(duplicate)
    _copy_materials(source, duplicate)
    duplicate.parent = None
    duplicate.animation_data_clear()
    return duplicate


def _object_has_body_material(obj: bpy.types.Object) -> bool:
    return any(material and material.name.endswith(".body") for material in obj.data.materials)


def _prune_clothed_body_geometry(obj: bpy.types.Object) -> int:
    body_material_indices = {
        index
        for index, material in enumerate(obj.data.materials)
        if material and material.name.endswith(".body")
    }
    if not body_material_indices:
        return 0

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    faces_to_delete = []
    for face in bm.faces:
        if face.material_index not in body_material_indices:
            continue
        center = face.calc_center_median()
        keep_head_and_neck = center.z >= 1.93
        keep_hands = (
            abs(center.x) >= 0.54
            and 1.05 <= center.z <= 1.48
            and center.y <= -0.28
        )
        if not (keep_head_and_neck or keep_hands):
            faces_to_delete.append(face)

    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")

    removed = len(faces_to_delete)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return removed


def _remove_unused_material_slots(obj: bpy.types.Object) -> int:
    mesh = obj.data
    if not mesh.materials:
        return 0
    polygon_material_indices = [poly.material_index for poly in mesh.polygons]
    used_indices = sorted(set(polygon_material_indices))
    if len(used_indices) == len(mesh.materials):
        return 0

    old_materials = list(mesh.materials)
    remap = {old_index: new_index for new_index, old_index in enumerate(used_indices)}
    mesh.materials.clear()
    for old_index in used_indices:
        mesh.materials.append(old_materials[old_index])
    for poly, old_index in zip(mesh.polygons, polygon_material_indices):
        poly.material_index = remap[old_index]
    mesh.update()
    return len(old_materials) - len(used_indices)


def _join_temp_meshes(meshes: list[bpy.types.Object]) -> bpy.types.Object:
    if len(meshes) == 1:
        return meshes[0]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = "Benjamin_Mesh2Motion_Upload"
    joined.data.name = "Benjamin_Mesh2Motion_UploadMesh"
    return joined


def export_mesh2motion_upload(context) -> tuple[str | None, str | None, str]:
    settings = context.scene.godot_exporter
    output_path = _safe_path(_pref(context, "mesh2motion_upload_path", DEFAULT_MESH2MOTION_UPLOAD_PATH))

    if not output_path:
        return None, "Mesh2Motion upload path is empty.", ""

    targets, missing = _target_source_meshes(context)
    if not targets:
        return None, "No source MPFB target meshes were found.", ""

    original_active = context.view_layer.objects.active
    original_selected = list(context.selected_objects)
    original_mode = context.object.mode if context.object else 'OBJECT'

    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    temp_collection = bpy.data.collections.new("BT Mesh2Motion Export Temp")
    context.scene.collection.children.link(temp_collection)
    temp_objects: list[bpy.types.Object] = []
    removed_faces = 0
    removed_slots = 0

    try:
        for target in targets:
            duplicate = _temporary_mesh_duplicate(target, temp_collection)
            temp_objects.append(duplicate)
            if settings.mesh2motion_prune_clothed_body and _object_has_body_material(duplicate):
                removed_faces += _prune_clothed_body_geometry(duplicate)
                removed_slots += _remove_unused_material_slots(duplicate)
            _replace_with_mesh2motion_safe_materials(duplicate)

        export_objects = temp_objects
        if settings.mesh2motion_join_upload_meshes:
            export_objects = [_join_temp_meshes(temp_objects)]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in export_objects:
            obj.hide_set(False)
            obj.hide_viewport = False
            obj.hide_render = False
            obj.select_set(True)
        context.view_layer.objects.active = export_objects[0]

        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=True,
            export_apply=True,
            export_materials='EXPORT',
            export_texcoords=True,
            export_normals=True,
            export_skins=False,
            export_morph=False,
            export_animations=False,
            export_cameras=False,
            export_lights=False,
            export_yup=True,
        )

        note = (
            f"exported {len(export_objects)} object(s), "
            f"removed {removed_faces} covered body faces, "
            f"removed {removed_slots} unused material slot(s)"
        )
        if missing:
            note += f"; missing targets: {', '.join(missing)}"
        return output_path, None, note
    except Exception as exc:
        return None, str(exc), ""
    finally:
        for obj in list(temp_objects):
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        if temp_collection.name in bpy.data.collections:
            bpy.data.collections.remove(temp_collection)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selected:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except Exception:
                    pass


def _spawn_mesh2motion_setup(context, launch: bool) -> subprocess.Popen:
    global _mesh2motion_proc

    script = _get_setup_script_path()
    command = [
        sys.executable,
        script,
        "--port",
        str(_pref(context, "mesh2motion_port", 5173)),
    ]
    if launch:
        command.append("--launch")

    log_path = os.path.join(TOOL_CACHE_ROOT, "mesh2motion-setup.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log = open(log_path, "a", encoding="utf-8")

    _mesh2motion_proc = subprocess.Popen(
        command,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=_path_env(),
    )
    print(f"[Benjamin Pipeline] Mesh2Motion setup started (PID {_mesh2motion_proc.pid})")
    print(f"[Benjamin Pipeline] Log: {log_path}")
    return _mesh2motion_proc


# ---------------------------------------------------------------------------
# Core export logic
# ---------------------------------------------------------------------------

def get_export_path(context):
    models_dir = _pref(context, "godot_models_path", DEFAULT_GODOT_MODELS_PATH)

    settings = context.scene.godot_exporter
    filename = settings.export_filename.strip()
    if not filename:
        # Derive from .blend filename
        blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        filename = blend_name if blend_name else "export"

    return os.path.join(models_dir, filename + ".glb")


def do_export(context):
    """
    Export the scene to Godot as GLB:
    - Converts curves/hair to meshes on temporary duplicates (non-destructive)
    - Includes materials
    - Exports armatures + meshes
    """
    export_path = get_export_path(context)
    settings = context.scene.godot_exporter
    selection_only = settings.export_selection_only

    # Remember original selection and active object
    original_active = context.view_layer.objects.active
    original_selected = [obj for obj in context.selected_objects]
    original_mode = context.object.mode if context.object else 'OBJECT'

    # Ensure we're in object mode
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Find all CURVES objects that need conversion
    if selection_only:
        objects_to_check = original_selected
    else:
        objects_to_check = list(context.scene.objects)

    curve_objects = [obj for obj in objects_to_check if obj.type == 'CURVES']

    converted_meshes = []
    try:
        # Temporarily convert curves to meshes (duplicates, non-destructive)
        for curve_obj in curve_objects:
            # Deselect all, select just this curve
            bpy.ops.object.select_all(action='DESELECT')
            curve_obj.select_set(True)
            context.view_layer.objects.active = curve_obj

            # Duplicate it
            bpy.ops.object.duplicate(linked=False)
            dup = context.active_object
            dup.name = curve_obj.name + "__export_mesh_temp"

            # Convert to mesh
            try:
                bpy.ops.object.convert(target='MESH')
                converted_meshes.append((curve_obj, dup))
                # Hide original curve from export temporarily
                curve_obj.hide_render = True
                curve_obj.hide_viewport = True
            except Exception as e:
                print(f"[Godot Exporter] Could not convert {curve_obj.name}: {e}")
                # Remove the duplicate if conversion failed
                bpy.data.objects.remove(dup)

        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selected:
            if obj.name in context.scene.objects:
                obj.select_set(True)
        if original_active and original_active.name in context.scene.objects:
            context.view_layer.objects.active = original_active

        # Ensure export directory exists
        os.makedirs(os.path.dirname(export_path), exist_ok=True)

        # Export
        bpy.ops.export_scene.gltf(
            filepath=export_path,
            export_format='GLB',
            use_selection=selection_only,
            export_materials='EXPORT',          # Include materials + textures (string enum)
            export_texcoords=True,
            export_normals=True,
            export_skins=True,
            export_morph=True,
            export_animations=True,
            export_cameras=False,
            export_lights=False,
            export_yup=True,
        )

        print(f"[Godot Exporter] Exported → {export_path}")
        return export_path, None

    except Exception as e:
        return None, str(e)

    finally:
        # Restore curve objects and remove temp meshes
        for curve_obj, temp_mesh in converted_meshes:
            curve_obj.hide_render = False
            curve_obj.hide_viewport = False
            bpy.data.objects.remove(temp_mesh)

        # Restore mode
        if original_active and original_active.name in context.scene.objects:
            context.view_layer.objects.active = original_active
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Operators: Mesh2Motion source workflow
# ---------------------------------------------------------------------------

class GODOT_OT_pack_benjamin_textures(bpy.types.Operator):
    bl_idname = "godot_exporter.pack_benjamin_textures"
    bl_label = "Pack MPFB Textures"
    bl_description = "Pack external MPFB texture images into this .blend so Benjamin travels as a self-contained source file"

    def execute(self, context):
        packed, missing = _pack_external_images()
        if bpy.data.filepath:
            bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        message = f"Packed {packed} image(s)"
        if missing:
            message += f"; missing: {', '.join(missing[:4])}"
        self.report({'WARNING'} if missing else {'INFO'}, message)
        return {'FINISHED'}


class GODOT_OT_export_mesh2motion_upload(bpy.types.Operator):
    bl_idname = "godot_exporter.export_mesh2motion_upload"
    bl_label = "Export Mesh2Motion Upload GLB"
    bl_description = "Export only Benjamin's clean MPFB source meshes as a static GLB for Mesh2Motion"

    def execute(self, context):
        path, error, note = export_mesh2motion_upload(context)
        if error:
            self.report({'ERROR'}, f"Mesh2Motion upload export failed: {error}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Exported {os.path.basename(path)} ({note})")
        return {'FINISHED'}


class GODOT_OT_reload_blend_from_disk(bpy.types.Operator):
    bl_idname = "godot_exporter.reload_blend_from_disk"
    bl_label = "Reload .blend From Disk"
    bl_description = "Reload the current .blend only when there are no unsaved live edits"

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "This .blend has not been saved yet.")
            return {'CANCELLED'}
        if bpy.data.is_dirty:
            self.report({'ERROR'}, "Live scene has unsaved edits. Save or discard them before reloading.")
            return {'CANCELLED'}
        bpy.ops.wm.revert_mainfile()
        _record_blend_session_mtime()
        return {'FINISHED'}


class GODOT_OT_inspect_benjamin_body(bpy.types.Operator):
    bl_idname = "godot_exporter.inspect_benjamin_body"
    bl_label = "Inspect Body Under Clothes"
    bl_description = "Show Benjamin's clothing as viewport wireframe so the underlying MPFB body can be inspected"

    enabled: BoolProperty(
        name="Inspect Body",
        default=True,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        changed = []
        for name in BODY_INSPECTION_CLOTHING_OBJECTS:
            obj = bpy.data.objects.get(name)
            if not obj:
                continue
            obj.display_type = 'TEXTURED'
            obj.show_wire = False
            if self.enabled:
                obj["bt_body_inspection_original_materials"] = json.dumps(
                    [material.name if material else "" for material in obj.data.materials]
                )
                ghost = _body_inspection_material()
                for index in range(len(obj.data.materials)):
                    obj.data.materials[index] = ghost
            else:
                stored = obj.get("bt_body_inspection_original_materials")
                if stored:
                    try:
                        material_names = json.loads(stored)
                    except Exception:
                        material_names = []
                    for index, material_name in enumerate(material_names):
                        if index < len(obj.data.materials):
                            obj.data.materials[index] = bpy.data.materials.get(material_name)
                    del obj["bt_body_inspection_original_materials"]
            changed.append(name)

        body = bpy.data.objects.get(BODY_INSPECTION_BODY_OBJECT)
        if body:
            body.show_in_front = self.enabled
            if self.enabled:
                bpy.ops.object.select_all(action='DESELECT')
                body.select_set(True)
                context.view_layer.objects.active = body

        if not changed and not body:
            self.report({'ERROR'}, "Benjamin body/clothing objects were not found")
            return {'CANCELLED'}

        verb = "Inspecting" if self.enabled else "Restored"
        self.report({'INFO'}, f"{verb} Benjamin body view")
        return {'FINISHED'}


class GODOT_OT_setup_mesh2motion(bpy.types.Operator):
    bl_idname = "godot_exporter.setup_mesh2motion"
    bl_label = "Setup Mesh2Motion"
    bl_description = "Clone/update Mesh2Motion app/assets and install the app dependencies in external/"

    launch_after: BoolProperty(
        name="Launch After Setup",
        default=False,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        try:
            _spawn_mesh2motion_setup(context, launch=self.launch_after)
        except Exception as exc:
            self.report({'ERROR'}, f"Could not start setup: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Mesh2Motion setup started; check external/mesh2motion-setup.log")
        return {'FINISHED'}


class GODOT_OT_launch_mesh2motion(bpy.types.Operator):
    bl_idname = "godot_exporter.launch_mesh2motion"
    bl_label = "Launch Mesh2Motion"
    bl_description = "Start the local Mesh2Motion dev server and open it in the browser"

    def execute(self, context):
        try:
            script = _get_setup_script_path()
            command = [
                sys.executable,
                script,
                "--skip-app",
                "--skip-assets",
                "--no-install",
                "--launch",
                "--port",
                str(_pref(context, "mesh2motion_port", 5173)),
            ]
            subprocess.Popen(command, env=_path_env())
        except Exception as exc:
            self.report({'ERROR'}, f"Could not launch Mesh2Motion: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Mesh2Motion launch requested")
        return {'FINISHED'}


class GODOT_OT_open_mesh2motion_app(bpy.types.Operator):
    bl_idname = "godot_exporter.open_mesh2motion_app"
    bl_label = "Open Mesh2Motion Create Page"
    bl_description = "Open the local Mesh2Motion page used to upload and rig Benjamin"

    def execute(self, context):
        webbrowser.open(f"http://127.0.0.1:{_pref(context, 'mesh2motion_port', 5173)}/create.html")
        return {'FINISHED'}


class GODOT_OT_auto_mesh2motion_rig(bpy.types.Operator):
    bl_idname = "godot_exporter.auto_mesh2motion_rig"
    bl_label = "Auto Rig in Mesh2Motion"
    bl_description = "Export Benjamin's upload GLB, drive Mesh2Motion with Human + Single Hand Bone, and download a first-pass rigged GLB"

    export_upload_first: BoolProperty(
        name="Export Upload First",
        description="Rebuild the clean static Mesh2Motion upload GLB before starting the browser automation",
        default=True,
        options={'SKIP_SAVE'},
    )

    stop_at_joints: BoolProperty(
        name="Stop At Joints",
        description="Stop after Mesh2Motion creates the editable skeleton so joints can be adjusted manually",
        default=False,
        options={'SKIP_SAVE'},
    )

    keep_covered_body: BoolProperty(
        name="Keep Body Under Clothes",
        description="Do not prune body faces covered by clothing in the Mesh2Motion upload/export",
        default=False,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        global _mesh2motion_auto_proc

        upload_pref_name = "mesh2motion_upload_path"
        upload_default = DEFAULT_MESH2MOTION_UPLOAD_PATH
        output_pref_name = "mesh2motion_rigged_output_path"
        output_default = DEFAULT_MESH2MOTION_RIGGED_PATH
        if self.keep_covered_body:
            upload_pref_name = "mesh2motion_full_body_upload_path"
            upload_default = DEFAULT_MESH2MOTION_FULL_BODY_UPLOAD_PATH
            output_pref_name = "mesh2motion_full_body_rigged_output_path"
            output_default = DEFAULT_MESH2MOTION_FULL_BODY_RIGGED_PATH

        upload_path = _safe_path(_pref(context, upload_pref_name, upload_default))
        output_path = _safe_path(_pref(context, output_pref_name, output_default))

        if self.export_upload_first:
            addon_prefs = _addon_prefs(context)
            settings = context.scene.godot_exporter
            old_upload_path = getattr(addon_prefs, "mesh2motion_upload_path", None) if addon_prefs else None
            old_prune = settings.mesh2motion_prune_clothed_body
            try:
                if self.keep_covered_body:
                    settings.mesh2motion_prune_clothed_body = False
                    if addon_prefs:
                        addon_prefs.mesh2motion_upload_path = upload_path
                path, error, note = export_mesh2motion_upload(context)
                if error:
                    self.report({'ERROR'}, f"Upload export failed: {error}")
                    return {'CANCELLED'}
                upload_path = path
                print(f"[Benjamin Pipeline] Mesh2Motion upload refreshed: {path} ({note})")
            finally:
                settings.mesh2motion_prune_clothed_body = old_prune
                if addon_prefs and old_upload_path is not None:
                    addon_prefs.mesh2motion_upload_path = old_upload_path

        script = _get_mesh2motion_auto_rig_script_path()
        if not os.path.exists(script):
            self.report({'ERROR'}, f"Missing automation script: {script}")
            return {'CANCELLED'}

        command = [
            sys.executable,
            script,
            "--input",
            upload_path,
            "--output",
            output_path,
            "--port",
            str(_pref(context, "mesh2motion_port", 5173)),
            "--session",
            "mesh2motion-benjamin",
        ]
        if self.stop_at_joints:
            command.append("--stop-at-joints")

        log_path = os.path.join(TOOL_CACHE_ROOT, "mesh2motion-auto-rig.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log = open(log_path, "a", encoding="utf-8")
        try:
            _mesh2motion_auto_proc = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=_path_env(),
            )
        except Exception as exc:
            self.report({'ERROR'}, f"Could not start Mesh2Motion automation: {exc}")
            return {'CANCELLED'}

        variant = "full-body" if self.keep_covered_body else "suited"
        self.report({'INFO'}, f"Mesh2Motion {variant} automation started; log: {log_path}")
        return {'FINISHED'}


class GODOT_OT_open_mesh2motion_assets(bpy.types.Operator):
    bl_idname = "godot_exporter.open_mesh2motion_assets"
    bl_label = "Open Mesh2Motion Assets"
    bl_description = "Open the local Mesh2Motion Blender source assets checkout in Finder"

    def execute(self, context):
        assets_path = _pref(context, "mesh2motion_assets_path", DEFAULT_MESH2MOTION_ASSETS_PATH)
        subprocess.Popen(["open", _safe_path(assets_path)])
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Operator: Manual export
# ---------------------------------------------------------------------------

class GODOT_OT_export(bpy.types.Operator):
    bl_idname = "godot_exporter.export"
    bl_label = "Export to Godot"
    bl_description = "Export this scene as GLB to the Godot project (materials + curves handled automatically)"

    def execute(self, context):
        path, error = do_export(context)
        if error:
            self.report({'ERROR'}, f"Export failed: {error}")
            return {'CANCELLED'}

        filename = os.path.basename(path)
        self.report({'INFO'}, f"Exported: {filename}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Operator: Open Godot models folder in Finder
# ---------------------------------------------------------------------------

class GODOT_OT_open_folder(bpy.types.Operator):
    bl_idname = "godot_exporter.open_folder"
    bl_label = "Open Models Folder"
    bl_description = "Open the Godot assets/models folder in Finder"

    def execute(self, context):
        import subprocess
        subprocess.Popen(["open", _pref(context, "godot_models_path", DEFAULT_GODOT_MODELS_PATH)])
        return {'FINISHED'}


def _write_trigger_file(project_path: str) -> None:
    """Write the pipeline_sync_trigger file so Godot's EditorPlugin picks it up."""
    trigger = os.path.join(project_path, "pipeline_sync_trigger")
    try:
        with open(trigger, "w") as f:
            f.write("rebuild")
        print(f"[Godot Exporter] Trigger written → {trigger}")
    except Exception as exc:
        print(f"[Godot Exporter] Could not write trigger file: {exc}")


# ---------------------------------------------------------------------------
# Auto-export save handler
# ---------------------------------------------------------------------------

@persistent
def auto_export_on_save(filepath):
    context = bpy.context
    if not hasattr(context, 'scene'):
        return
    settings = context.scene.godot_exporter
    if not settings.auto_export:
        return

    print("[Godot Exporter] Auto-exporting on save...")
    path, error = do_export(context)
    if error:
        print(f"[Godot Exporter] Auto-export failed: {error}")
    else:
        print(f"[Godot Exporter] Auto-export done → {path}")


@persistent
def record_blend_loaded(filepath):
    _record_blend_session_mtime()


@persistent
def record_blend_saved(filepath):
    _record_blend_session_mtime(filepath)


# ---------------------------------------------------------------------------
# UI Panel
# ---------------------------------------------------------------------------

class GODOT_PT_exporter_panel(bpy.types.Panel):
    bl_label = "Benjamin Pipeline"
    bl_idname = "GODOT_PT_exporter_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Benjamin"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.godot_exporter
        mesh2motion_upload_path = _pref(context, "mesh2motion_upload_path", DEFAULT_MESH2MOTION_UPLOAD_PATH)
        mesh2motion_port = _pref(context, "mesh2motion_port", 5173)

        # ── Mesh2Motion source section ─────────────────────────────────────
        box = layout.box()
        box.label(text="Source Character", icon='OUTLINER_OB_ARMATURE')

        disk_status = _blend_disk_status()
        if disk_status["state"] == "disk_newer":
            stale = box.box()
            stale.alert = True
            stale.label(text="Disk .blend is newer than this session", icon='ERROR')
            stale.operator("godot_exporter.reload_blend_from_disk", icon='FILE_REFRESH')
        elif bpy.data.is_dirty:
            box.label(text="Live scene has unsaved edits", icon='FILE_TICK')

        row = box.row()
        row.scale_y = 1.25
        row.operator("godot_exporter.pack_benjamin_textures", icon='PACKAGE')

        row = box.row()
        row.scale_y = 1.35
        row.operator("godot_exporter.export_mesh2motion_upload", icon='EXPORT')

        upload = _safe_path(mesh2motion_upload_path)
        box.label(text=f"Upload: ...{upload[-42:]}" if len(upload) > 45 else f"Upload: {upload}",
                  icon='FILE_3D')
        box.prop(settings, "mesh2motion_prune_clothed_body")
        box.prop(settings, "mesh2motion_join_upload_meshes")

        row = box.row(align=True)
        inspect = row.operator("godot_exporter.inspect_benjamin_body", text="Inspect Body", icon='HIDE_OFF')
        inspect.enabled = True
        restore = row.operator("godot_exporter.inspect_benjamin_body", text="Restore Clothes", icon='HIDE_ON')
        restore.enabled = False

        targets = box.column(align=True)
        targets.prop(settings, "mesh2motion_target_names", text="Meshes")

        layout.separator()

        # ── Mesh2Motion app section ────────────────────────────────────────
        box = layout.box()
        box.label(text="Mesh2Motion", icon='MOD_ARMATURE')

        row = box.row(align=True)
        setup = row.operator("godot_exporter.setup_mesh2motion", text="Setup / Update", icon='FILE_REFRESH')
        setup.launch_after = False
        setup_launch = row.operator("godot_exporter.setup_mesh2motion", text="Setup + Launch", icon='PLAY')
        setup_launch.launch_after = True

        row = box.row(align=True)
        row.operator("godot_exporter.launch_mesh2motion", icon='PLAY')
        row.operator("godot_exporter.open_mesh2motion_app", icon='URL')

        row = box.row(align=True)
        row.scale_y = 1.35
        auto = row.operator("godot_exporter.auto_mesh2motion_rig", text="Auto Rig Suit", icon='ARMATURE_DATA')
        auto.export_upload_first = True
        auto.stop_at_joints = False
        auto.keep_covered_body = False
        auto_full = row.operator("godot_exporter.auto_mesh2motion_rig", text="Auto Rig Full Body", icon='MOD_CLOTH')
        auto_full.export_upload_first = True
        auto_full.stop_at_joints = False
        auto_full.keep_covered_body = True

        rigged_output = _safe_path(_pref(context, "mesh2motion_rigged_output_path", DEFAULT_MESH2MOTION_RIGGED_PATH))
        box.label(text=f"Rigged: ...{rigged_output[-42:]}" if len(rigged_output) > 45 else f"Rigged: {rigged_output}",
                  icon='FILE_3D')
        full_body_output = _safe_path(_pref(context, "mesh2motion_full_body_rigged_output_path", DEFAULT_MESH2MOTION_FULL_BODY_RIGGED_PATH))
        box.label(text=f"Full body: ...{full_body_output[-42:]}" if len(full_body_output) > 45 else f"Full body: {full_body_output}",
                  icon='FILE_3D')

        row = box.row()
        row.operator("godot_exporter.open_mesh2motion_assets", icon='FILE_FOLDER')
        box.label(text=f"Port: {mesh2motion_port}", icon='CONSOLE')

        layout.separator()

        # ── Direct export section ──────────────────────────────────────────
        box = layout.box()
        box.label(text="Direct Runtime GLB Export", icon='MESH_DATA')

        # Export path preview
        path = get_export_path(context)
        display = "…" + path[-35:] if len(path) > 38 else path
        box.label(text=display, icon='FILE_FOLDER')
        box.operator("godot_exporter.open_folder", icon='FOLDER_REDIRECT')

        box.prop(settings, "export_filename", text="Filename Override")
        box.prop(settings, "export_selection_only")

        row = box.row()
        row.scale_y = 1.3
        row.operator("godot_exporter.export", icon='EXPORT')

        row = box.row()
        icon = 'CHECKBOX_HLT' if settings.auto_export else 'CHECKBOX_DEHLT'
        row.prop(settings, "auto_export", icon=icon, text="Auto direct-export on Ctrl+S")

        layout.separator()

        # Preferences shortcut
        layout.operator("preferences.addon_show",
                        text="Configure Paths", icon='PREFERENCES').module = __name__


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    GodotExporterPreferences,
    GodotExporterSettings,
    GODOT_OT_pack_benjamin_textures,
    GODOT_OT_export_mesh2motion_upload,
    GODOT_OT_reload_blend_from_disk,
    GODOT_OT_inspect_benjamin_body,
    GODOT_OT_setup_mesh2motion,
    GODOT_OT_launch_mesh2motion,
    GODOT_OT_open_mesh2motion_app,
    GODOT_OT_auto_mesh2motion_rig,
    GODOT_OT_open_mesh2motion_assets,
    GODOT_OT_export,
    GODOT_OT_open_folder,
    GODOT_PT_exporter_panel,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
            bpy.utils.register_class(cls)
    if not hasattr(bpy.types.Scene, "godot_exporter"):
        bpy.types.Scene.godot_exporter = bpy.props.PointerProperty(type=GodotExporterSettings)
    if auto_export_on_save not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(auto_export_on_save)
    if record_blend_saved not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(record_blend_saved)
    if record_blend_loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(record_blend_loaded)
    _record_blend_session_mtime()


def unregister():
    if auto_export_on_save in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(auto_export_on_save)
    if record_blend_saved in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(record_blend_saved)
    if record_blend_loaded in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(record_blend_loaded)
    if hasattr(bpy.types.Scene, "godot_exporter"):
        del bpy.types.Scene.godot_exporter
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


if __name__ == "__main__":
    register()
