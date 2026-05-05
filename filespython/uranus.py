import bpy
import math

# ---------- CONFIG ----------
PLANET_NAME = "Uranus"
RADIUS = 4.0
SPIN_FRAMES = 240
FPS = 24
TEXTURE_NAME_HINT = "uranus"

CAMERA_NAME = "Uranus_Camera"
LIGHT_NAME = "Uranus_KeyLight"
# ----------------------------

scene = bpy.context.scene
scene.render.fps = FPS

# Remove existing objects if present
for name in [PLANET_NAME, CAMERA_NAME, LIGHT_NAME]:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# Create planet
bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS, location=(0, 0, 0))
planet = bpy.context.object
planet.name = PLANET_NAME

# Planet material
mat = bpy.data.materials.new(name="UranusMaterial")
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

img = None
for image in bpy.data.images:
    if TEXTURE_NAME_HINT in image.name.lower():
        img = image
        break

if img:
    tex.image = img
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

if planet.data.materials:
    planet.data.materials[0] = mat
else:
    planet.data.materials.append(mat)

# Camera
bpy.ops.object.camera_add(location=(0, -25, 10), rotation=(math.radians(75), 0, 0))
camera = bpy.context.object
camera.name = CAMERA_NAME
scene.camera = camera

# Light (Sun)
bpy.ops.object.light_add(type='SUN', location=(20, -20, 30))
light = bpy.context.object
light.name = LIGHT_NAME
light.data.energy = 3.0
light.data.angle = math.radians(2.0)

# Animate spin (prograde)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
planet.rotation_euler = (0, 0, 0)
planet.keyframe_insert(data_path="rotation_euler", frame=1)
planet.rotation_euler = (0, 0, math.radians(-360))
planet.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)