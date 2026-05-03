import bpy
import math

# ---------- CONFIG ----------
PLANET_NAME = "Mercury"
RADIUS = 0.38              # relative size
SPIN_FRAMES = 240         # frames per full rotation
FPS = 24
TEXTURE_NAME_HINT = "mercury"  # change to match your image name
# ----------------------------

scene = bpy.context.scene
scene.render.fps = FPS

# Remove existing Mercury if present
if PLANET_NAME in bpy.data.objects:
    obj = bpy.data.objects[PLANET_NAME]
    bpy.data.objects.remove(obj, do_unlink=True)

# Create sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS, location=(0, 0, 0))
planet = bpy.context.object
planet.name = PLANET_NAME

# Create material
mat = bpy.data.materials.new(name="MercuryMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Clear default nodes
for n in nodes:
    nodes.remove(n)

# Nodes
out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
tex = nodes.new("ShaderNodeTexImage")

# Layout (optional)
tex.location = (-400, 200)
bsdf.location = (-200, 200)
out.location = (200, 200)

# Try to find BlenderKit texture image
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

# Linear interpolation before keyframes
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

# Animate spin (Z rotation)
planet.rotation_euler = (0, 0, 0)
planet.keyframe_insert(data_path="rotation_euler", frame=1)

planet.rotation_euler = (0, 0, math.radians(360))
planet.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)