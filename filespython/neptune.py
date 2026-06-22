import bpy
import math

# ---------- CONFIG ----------
PLANET_NAME = "Neptune"
RADIUS = 3.88
SPIN_FRAMES = 240
FPS = 24

ORBIT_NAME = "Neptune_OrbitLines"
ORBIT_COUNT = 5
ORBIT_START = 6.0
ORBIT_END = 11.0
ORBIT_THICKNESS = 0.01  # line thickness

CAMERA_NAME = "Neptune_Camera"
LIGHT_NAME = "Neptune_KeyLight"
# ----------------------------

scene = bpy.context.scene
scene.render.fps = FPS

# Remove existing objects if present
for name in [PLANET_NAME, ORBIT_NAME, CAMERA_NAME, LIGHT_NAME]:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# Create planet
bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS, location=(0, 0, 0))
planet = bpy.context.object
planet.name = PLANET_NAME

# Procedural material (Neptune)
mat = bpy.data.materials.new(name="NeptuneMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
noise = nodes.new("ShaderNodeTexNoise")
ramp = nodes.new("ShaderNodeValToRGB")
coord = nodes.new("ShaderNodeTexCoord")
mapping = nodes.new("ShaderNodeMapping")

links.new(coord.outputs["UV"], mapping.inputs["Vector"])
mapping.inputs["Scale"].default_value = (1.0, 10.0, 1.0)
noise.inputs["Scale"].default_value = 4.0
noise.inputs["Detail"].default_value = 2.0

ramp.color_ramp.elements[0].position = 0.35
ramp.color_ramp.elements[1].position = 0.65
ramp.color_ramp.elements[0].color = (0.05, 0.2, 0.45, 1)
ramp.color_ramp.elements[1].color = (0.2, 0.5, 0.85, 1)

links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

planet.data.materials.clear()
planet.data.materials.append(mat)

# Orbit lines (curve circles)
orbit_parent = bpy.data.objects.new(ORBIT_NAME, None)
scene.collection.objects.link(orbit_parent)
orbit_parent.parent = planet

orbit_mat = bpy.data.materials.new(name="OrbitLineMaterial")
orbit_mat.use_nodes = True
orbit_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.7, 0.85, 1.0, 1)

step = (ORBIT_END - ORBIT_START) / (ORBIT_COUNT - 1)

for i in range(ORBIT_COUNT):
    r = ORBIT_START + i * step
    bpy.ops.curve.primitive_bezier_circle_add(radius=r, location=(0, 0, 0))
    c = bpy.context.object
    c.data.bevel_depth = ORBIT_THICKNESS
    c.data.bevel_resolution = 4
    c.data.materials.append(orbit_mat)
    c.parent = orbit_parent

# Camera
bpy.ops.object.camera_add(location=(0, -22, 9), rotation=(math.radians(75), 0, 0))
camera = bpy.context.object
camera.name = CAMERA_NAME
scene.camera = camera

# Light (Sun)
bpy.ops.object.light_add(type='SUN', location=(20, -20, 30))
light = bpy.context.object
light.name = LIGHT_NAME
light.data.energy = 3.0
light.data.angle = math.radians(2.0)

# Spin
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
planet.rotation_euler = (0, 0, 0)
planet.keyframe_insert(data_path="rotation_euler", frame=1)
planet.rotation_euler = (0, 0, math.radians(360))
planet.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)