import bpy
import math

# ---------- CONFIG ----------
SUN_NAME = "SpinningSun"
SPIN_FRAMES = 240          # total frames for one full rotation
FPS = 24
TEXTURE_NAME_HINT = "sun"  # used to find BlenderKit sun texture by name
# ----------------------------

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = SPIN_FRAMES
scene.render.fps = FPS

# Remove existing sun if present
if SUN_NAME in bpy.data.objects:
    obj = bpy.data.objects[SUN_NAME]
    bpy.data.objects.remove(obj, do_unlink=True)

# Create sun mesh (UV sphere)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
sun = bpy.context.object
sun.name = SUN_NAME

# Create material
mat = bpy.data.materials.new(name="SunMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Clear default nodes
for n in nodes:
    nodes.remove(n)

# Nodes
out = nodes.new("ShaderNodeOutputMaterial")
em = nodes.new("ShaderNodeEmission")
tex = nodes.new("ShaderNodeTexImage")

# Layout (optional)
tex.location = (-400, 200)
em.location = (-200, 200)
out.location = (200, 0)

# Try to find a BlenderKit sun texture image
sun_img = None
for img in bpy.data.images:
    name_lower = img.name.lower()
    if TEXTURE_NAME_HINT in name_lower:
        sun_img = img
        break

if sun_img:
    tex.image = sun_img
    links.new(tex.outputs["Color"], em.inputs["Color"])
else:
    # Fallback: use bright yellow/orange emission
    em.inputs["Color"].default_value = (1.0, 0.6, 0.1, 1.0)

em.inputs["Strength"].default_value = 10.0
links.new(em.outputs["Emission"], out.inputs["Surface"])

# Assign material
if sun.data.materials:
    sun.data.materials[0] = mat
else:
    sun.data.materials.append(mat)

# Set default interpolation to linear before inserting keyframes
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

# Animate spin (Z rotation)
sun.rotation_euler = (0, 0, 0)
sun.keyframe_insert(data_path="rotation_euler", frame=1)

sun.rotation_euler = (0, 0, math.radians(360))
sun.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)