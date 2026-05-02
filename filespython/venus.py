import bpy
import math

# ---------- CONFIG ----------
PLANET_NAME = "Venus"
RADIUS = 0.95
SPIN_FRAMES = 240          # one full rotation over 240 frames
FPS = 24
TEXTURE_NAME_HINT = "venus"
# ----------------------------

scene = bpy.context.scene
scene.render.fps = FPS

# Remove existing Venus if present
if PLANET_NAME in bpy.data.objects:
    obj = bpy.data.objects[PLANET_NAME]
    bpy.data.objects.remove(obj, do_unlink=True)

# Create sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS, location=(0, 0, 0))
planet = bpy.context.object
planet.name = PLANET_NAME

# Create material
mat = bpy.data.materials.new(name="VenusMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
for n in nodes:
    nodes.remove(n)

out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
tex = nodes.new("ShaderNodeTexImage")

tex.location = (-400, 200)
bsdf.location = (-200, 200)
out.location = (200, 200)

# Find texture image
img = None
for image in bpy.data.images:
    if TEXTURE_NAME_HINT in image.name.lower():
        img = image
        break

if img:
    tex.image = img
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

# Assign material
if planet.data.materials:
    planet.data.materials[0] = mat
else:
    planet.data.materials.append(mat)

# Linear interpolation
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

# Animate spin
planet.rotation_euler = (0, 0, 0)
planet.keyframe_insert(data_path="rotation_euler", frame=1)

planet.rotation_euler = (0, 0, math.radians(-360))
planet.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)