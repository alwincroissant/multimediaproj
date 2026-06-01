import bpy
import math

# ---------- CONFIG ----------
PLANET_NAME = "Pluto"
RADIUS = 1.2
SPIN_FRAMES = 240
FPS = 24

CAMERA_NAME = "Pluto_Camera"
LIGHT_NAME = "Pluto_KeyLight"
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

# Pluto material (brownish ice + dark patch)
mat = bpy.data.materials.new(name="PlutoMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")

coord = nodes.new("ShaderNodeTexCoord")
mapping = nodes.new("ShaderNodeMapping")
noise1 = nodes.new("ShaderNodeTexNoise")
noise2 = nodes.new("ShaderNodeTexNoise")
ramp = nodes.new("ShaderNodeValToRGB")
mix = nodes.new("ShaderNodeMixRGB")

coord.location = (-800, 0)
mapping.location = (-600, 0)
noise1.location = (-400, 100)
noise2.location = (-400, -100)
ramp.location = (-200, 100)
mix.location = (0, 0)
bsdf.location = (200, 0)
out.location = (400, 0)

# UVs for even distribution
links.new(coord.outputs["UV"], mapping.inputs["Vector"])

# Large blotches (dark region)
noise1.inputs["Scale"].default_value = 2.0
noise1.inputs["Detail"].default_value = 1.0

# Fine speckle
noise2.inputs["Scale"].default_value = 15.0
noise2.inputs["Detail"].default_value = 8.0

# Brownish palette
ramp.color_ramp.elements[0].position = 0.45
ramp.color_ramp.elements[1].position = 0.75
ramp.color_ramp.elements[0].color = (0.85, 0.78, 0.70, 1)  # light tan ice
ramp.color_ramp.elements[1].color = (0.35, 0.22, 0.14, 1)  # dark brown

links.new(mapping.outputs["Vector"], noise1.inputs["Vector"])
links.new(mapping.outputs["Vector"], noise2.inputs["Vector"])
links.new(noise1.outputs["Fac"], ramp.inputs["Fac"])

# Mix in fine speckle
mix.blend_type = 'MULTIPLY'
mix.inputs["Fac"].default_value = 0.4
links.new(ramp.outputs["Color"], mix.inputs[1])
links.new(noise2.outputs["Fac"], mix.inputs[2])

links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.9
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

planet.data.materials.clear()
planet.data.materials.append(mat)

# Camera
bpy.ops.object.camera_add(location=(0, -10, 5), rotation=(math.radians(75), 0, 0))
camera = bpy.context.object
camera.name = CAMERA_NAME
scene.camera = camera

# Light (Sun)
bpy.ops.object.light_add(type='SUN', location=(15, -15, 20))
light = bpy.context.object
light.name = LIGHT_NAME
light.data.energy = 2.5
light.data.angle = math.radians(2.0)

# Spin
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
planet.rotation_euler = (0, 0, 0)
planet.keyframe_insert(data_path="rotation_euler", frame=1)
planet.rotation_euler = (0, 0, math.radians(360))
planet.keyframe_insert(data_path="rotation_euler", frame=SPIN_FRAMES)