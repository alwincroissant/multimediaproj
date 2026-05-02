import bpy
import math

# ---------- CONFIG ----------
PLANET_NAME = "Saturn"
RADIUS = 9.45
SPIN_FRAMES = 240
FPS = 24
TEXTURE_NAME_HINT = "saturn"

RING_NAME = "Saturn_Rings"
RING_INNER = 12.0
RING_OUTER = 20.0
RING_THICKNESS = 0.05

CAMERA_NAME = "Saturn_Camera"
LIGHT_NAME = "Saturn_KeyLight"
# ----------------------------

scene = bpy.context.scene
scene.render.fps = FPS

# Remove existing objects if present
for name in [PLANET_NAME, RING_NAME, CAMERA_NAME, LIGHT_NAME]:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# Create planet
bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS, location=(0, 0, 0))
planet = bpy.context.object
planet.name = PLANET_NAME

# Planet material
mat = bpy.data.materials.new(name="SaturnMaterial")
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

# Rings (flat disc)
bpy.ops.mesh.primitive_torus_add(
    major_radius=(RING_INNER + RING_OUTER) / 2,
    minor_radius=(RING_OUTER - RING_INNER) / 2,
    location=(0, 0, 0),
    rotation=(0, 0, 0)
)
rings = bpy.context.object
rings.name = RING_NAME
rings.scale.z = RING_THICKNESS

# Simple ring material
ring_mat = bpy.data.materials.new(name="RingMaterial")
ring_mat.use_nodes = True
nodes = ring_mat.node_tree.nodes
links = ring_mat.node_tree.links
for n in nodes:
    nodes.remove(n)

r_out = nodes.new("ShaderNodeOutputMaterial")
r_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
r_tex = nodes.new("ShaderNodeTexNoise")
r_ramp = nodes.new("ShaderNodeValToRGB")
r_coord = nodes.new("ShaderNodeTexCoord")
r_map = nodes.new("ShaderNodeMapping")

r_coord.location = (-800, 0)
r_map.location = (-600, 0)
r_tex.location = (-400, 0)
r_ramp.location = (-200, 0)
r_bsdf.location = (0, 0)
r_out.location = (200, 0)

r_map.inputs["Scale"].default_value = (20.0, 1.0, 1.0)
r_tex.inputs["Scale"].default_value = 12.0
r_tex.inputs["Detail"].default_value = 2.0

r_ramp.color_ramp.elements[0].position = 0.35
r_ramp.color_ramp.elements[1].position = 0.65
r_ramp.color_ramp.elements[0].color = (0.6, 0.55, 0.5, 1)
r_ramp.color_ramp.elements[1].color = (0.85, 0.8, 0.75, 1)

links.new(r_coord.outputs["Object"], r_map.inputs["Vector"])
links.new(r_map.outputs["Vector"], r_tex.inputs["Vector"])
links.new(r_tex.outputs["Fac"], r_ramp.inputs["Fac"])
links.new(r_ramp.outputs["Color"], r_bsdf.inputs["Base Color"])
links.new(r_bsdf.outputs["BSDF"], r_out.inputs["Surface"])

if rings.data.materials:
    rings.data.materials[0] = ring_mat
else:
    rings.data.materials.append(ring_mat)

# Parent rings to planet
rings.parent = planet

# Camera
bpy.ops.object.camera_add(location=(0, -45, 15), rotation=(math.radians(75), 0, 0))
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
planet.rotation_euler = (0, 0, math.radians(360))
planet.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)