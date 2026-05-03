import bpy
import math

# Clear scene safely without operators
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in bpy.data.meshes:
    bpy.data.meshes.remove(mesh)
for curve in bpy.data.curves:
    bpy.data.curves.remove(curve)
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

FRAMES = 1440  # 60 seconds at 24 FPS
FPS = 24

ORBIT_MULT = 25.0  # Scales up orbits so differences are clearly visible
SPIN_MULT = 0.02   # Scales down spins so planets don't strobe rapidly

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAMES
scene.render.fps = FPS

# Safely set keyframe interpolation
try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
except AttributeError:
    pass

# Set renderer to Eevee (robust against 4.2+ changes where EEVEE_NEXT is the real engine but EEVEE works for compat)
try:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE'

def set_linear_interpolation(obj):
    if obj and obj.animation_data and obj.animation_data.action:
        try:
            fcurves = obj.animation_data.action.fcurves
        except AttributeError:
            from bpy_extras import anim_utils
            slot = getattr(obj.animation_data, "action_slot", None)
            if slot:
                channelbag = anim_utils.action_get_channelbag_for_slot(obj.animation_data.action, slot)
                fcurves = channelbag.fcurves if channelbag else []
            else:
                fcurves = []
        for fcurve in fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

def smooth_object(obj):
    """Smooth without bpy.ops context errors."""
    if obj and obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True

def get_texture(hint):
    hint = hint.lower()
    for img in bpy.data.images:
        if hint in img.name.lower():
            return img
    return None

def apply_material(obj, name, is_sun=False):
    mat = bpy.data.materials.new(name=f"{name}Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        nodes.remove(n)
        
    out = nodes.new("ShaderNodeOutputMaterial")
    
    if is_sun:
        shader = nodes.new("ShaderNodeEmission")
        shader.inputs["Strength"].default_value = 5.0
        shader.inputs["Color"].default_value = (1.0, 0.8, 0.1, 1.0)
    else:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        
    tex_img = get_texture(name)
    if tex_img:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = tex_img
        if is_sun:
            links.new(tex.outputs["Color"], shader.inputs["Color"])
        else:
            links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    else:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 5.0
        color_ramp = nodes.new("ShaderNodeValToRGB")
        color_ramp.color_ramp.elements[0].color = (0.2, 0.2, 0.2, 1)
        color_ramp.color_ramp.elements[1].color = (0.8, 0.8, 0.8, 1)
        links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        if is_sun:
            links.new(color_ramp.outputs["Color"], shader.inputs["Color"])
        else:
            links.new(color_ramp.outputs["Color"], shader.inputs["Base Color"])
            
    links.new(shader.outputs[0], out.inputs["Surface"])
    obj.data.materials.append(mat)

def create_orbit_line(distance, name, parent_obj=None, location=(0,0,0)):
    # Create curve data directly to avoid context errors in 5.1
    curve_data = bpy.data.curves.new(name=f"{name}_OrbitLine", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.02
    curve_data.resolution_u = 64
    
    spline = curve_data.splines.new('POLY')
    pts = 64
    spline.points.add(pts - 1)
    for i in range(pts):
        angle = (i / pts) * 2 * math.pi
        x = distance * math.cos(angle)
        y = distance * math.sin(angle)
        spline.points[i].co = (x, y, 0, 1)
    spline.use_cyclic_u = True
    
    orbit_curve = bpy.data.objects.new(f"{name}_OrbitLine", curve_data)
    bpy.context.scene.collection.objects.link(orbit_curve)
    orbit_curve.location = location
    
    if parent_obj:
        orbit_curve.parent = parent_obj
    
    mat = bpy.data.materials.new(name=f"{name}_OrbitMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes: nodes.remove(n)
    
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 0.5
    links.new(emission.outputs[0], out.inputs["Surface"])
    orbit_curve.data.materials.append(mat)
    
    return orbit_curve

def create_planet(name, radius, distance, orbit_revs, spin_revs):
    # Orbit Empty directly via data API to avoid context errors
    orbit = bpy.data.objects.new(f"{name}_Orbit", None)
    orbit.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(orbit)
    
    # Orbit Line
    create_orbit_line(distance, name)
    
    # Body
    # Ensure active object capturing is robust if we use operators, or create manually.
    objs_before = set(bpy.context.scene.objects)
    
    # In some Blender contexts, operators fail if not in 3D Viewport. 
    # Try using the operator, if it fails, create it manually.
    try:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(distance, 0, 0))
        new_objs = set(bpy.context.scene.objects) - objs_before
        if new_objs:
            body = list(new_objs)[0]
        else:
            body = bpy.context.active_object
    except Exception:
        # Fallback if operator fails due to context
        mesh = bpy.data.meshes.new(name)
        body = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(body)
        body.location = (distance, 0, 0)
        # Create a basic sphere mesh using bmesh
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=radius)
        bm.to_mesh(mesh)
        bm.free()

    body.name = name
    smooth_object(body)
    
    # Parent body to orbit
    body.parent = orbit
    
    apply_material(body, name)
    
    # Orbit Animation
    orbit.rotation_euler = (0, 0, 0)
    orbit.keyframe_insert(data_path="rotation_euler", frame=1)
    orbit.rotation_euler = (0, 0, math.radians(360 * orbit_revs * ORBIT_MULT))
    orbit.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    set_linear_interpolation(orbit)
    
    # Spin Animation (relative to orbit)
    body.rotation_euler = (0, 0, 0)
    body.keyframe_insert(data_path="rotation_euler", frame=1)
    body.rotation_euler = (0, 0, math.radians(360 * spin_revs * SPIN_MULT))
    body.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    set_linear_interpolation(body)
    
    return orbit, body

# ==========================================
# SIZES (Earth = 0.1, scaled down Sun slightly for better view)
# ==========================================
R_SUN     = 5.0   # Scaled down from 10.92 so planets are more visible
R_MERCURY = 0.0383
R_VENUS   = 0.0949
R_EARTH   = 0.1
R_MOON    = 0.0272
R_MARS    = 0.0532
R_JUPITER = 1.121
R_SATURN  = 0.945
R_URANUS  = 0.401
R_NEPTUNE = 0.388
R_PLUTO   = 0.0186

# DISTANCES (Spaced to fit Sun and not overlap, Sun is radius 5, so start at 7)
D_MERCURY = 7.0
D_VENUS   = 9.0
D_EARTH   = 12.0
D_MOON    = 0.3  # Distance from Earth
D_MARS    = 15.0
D_JUPITER = 21.0
D_SATURN  = 28.0
D_URANUS  = 35.0
D_NEPTUNE = 42.0
D_PLUTO   = 49.0

# REVOLUTIONS
# Earth: Orbit = 1.0, Abs Spin = 366.25 -> Rel Spin = 365.25
# Moon: Orbit = 13.37, Rel Spin = 0
# Mercury: Orbit = 4.15, Rel Spin = 2.08
# Venus: Orbit = 1.62, Rel Spin = -3.12
# Mars: Orbit = 0.53, Rel Spin = 355.47
# Jupiter: Orbit = 0.08, Rel Spin = 883.14
# Saturn: Orbit = 0.03, Rel Spin = 822.58
# Uranus: Orbit = 0.01, Rel Spin = -508.48
# Neptune: Orbit = 0.006, Rel Spin = 544.12
# Pluto: Orbit = 0.004, Rel Spin = -57.18

# 1. SUN
objs_before = set(bpy.context.scene.objects)
try:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R_SUN, location=(0, 0, 0))
    new_objs = set(bpy.context.scene.objects) - objs_before
    if new_objs:
        sun = list(new_objs)[0]
    else:
        sun = bpy.context.active_object
except Exception:
    mesh = bpy.data.meshes.new("Sun")
    sun = bpy.data.objects.new("Sun", mesh)
    bpy.context.scene.collection.objects.link(sun)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=R_SUN)
    bm.to_mesh(mesh)
    bm.free()

sun.name = "Sun"
smooth_object(sun)
apply_material(sun, "sun", is_sun=True)
sun.rotation_euler = (0, 0, 0)
sun.keyframe_insert(data_path="rotation_euler", frame=1)
sun.rotation_euler = (0, 0, math.radians(360 * 14.39 * SPIN_MULT))
sun.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
set_linear_interpolation(sun)

# 2. PLANETS
create_planet("Mercury", R_MERCURY, D_MERCURY, 4.15,  2.08)
create_planet("Venus",   R_VENUS,   D_VENUS,   1.62, -3.12)

# EARTH & MOON
earth_orbit, earth_body = create_planet("Earth", R_EARTH, D_EARTH, 1.0, 365.25)

moon_orbit = bpy.data.objects.new("Moon_Orbit", None)
moon_orbit.empty_display_type = 'PLAIN_AXES'
bpy.context.scene.collection.objects.link(moon_orbit)
moon_orbit.parent = earth_orbit
moon_orbit.location = (D_EARTH, 0, 0)

create_orbit_line(D_MOON, "Moon", earth_orbit, location=(D_EARTH, 0, 0))

objs_before = set(bpy.context.scene.objects)
try:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R_MOON, location=(D_EARTH + D_MOON, 0, 0))
    new_objs = set(bpy.context.scene.objects) - objs_before
    if new_objs:
        moon_body = list(new_objs)[0]
    else:
        moon_body = bpy.context.active_object
except Exception:
    mesh = bpy.data.meshes.new("Moon")
    moon_body = bpy.data.objects.new("Moon", mesh)
    bpy.context.scene.collection.objects.link(moon_body)
    moon_body.location = (D_EARTH + D_MOON, 0, 0)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=R_MOON)
    bm.to_mesh(mesh)
    bm.free()

moon_body.name = "Moon"
smooth_object(moon_body)
moon_body.parent = moon_orbit
apply_material(moon_body, "moon")

moon_orbit.rotation_euler = (0, 0, 0)
moon_orbit.keyframe_insert(data_path="rotation_euler", frame=1)
moon_orbit.rotation_euler = (0, 0, math.radians(360 * 13.37 * ORBIT_MULT))
moon_orbit.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
set_linear_interpolation(moon_orbit)
set_linear_interpolation(moon_body)

create_planet("Mars",    R_MARS,    D_MARS,    0.53,  355.47)
create_planet("Jupiter", R_JUPITER, D_JUPITER, 0.08, 883.14)

# SATURN & RINGS
saturn_orbit, saturn_body = create_planet("Saturn", R_SATURN, D_SATURN, 0.03, 822.58)

objs_before = set(bpy.context.scene.objects)
try:
    bpy.ops.mesh.primitive_cylinder_add(radius=R_SATURN * 2.2, depth=0.01, location=(D_SATURN, 0, 0))
    new_objs = set(bpy.context.scene.objects) - objs_before
    if new_objs:
        saturn_rings = list(new_objs)[0]
    else:
        saturn_rings = bpy.context.active_object
except Exception:
    mesh = bpy.data.meshes.new("Saturn_Rings")
    saturn_rings = bpy.data.objects.new("Saturn_Rings", mesh)
    bpy.context.scene.collection.objects.link(saturn_rings)
    saturn_rings.location = (D_SATURN, 0, 0)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=32, diameter1=R_SATURN * 2.2, diameter2=R_SATURN * 2.2, depth=0.01)
    bm.to_mesh(mesh)
    bm.free()

saturn_rings.name = "Saturn_Rings"
saturn_rings.parent = saturn_orbit
mat = bpy.data.materials.new(name="SaturnRingsMaterial")
mat.use_nodes = True
mat.blend_method = 'BLEND'
nodes = mat.node_tree.nodes
links = mat.node_tree.links
for n in nodes: nodes.remove(n)
out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
tex_img = get_texture("ring")
if tex_img:
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = tex_img
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if "Alpha" in tex.outputs:
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
else:
    bsdf.inputs["Base Color"].default_value = (0.7, 0.6, 0.5, 1.0)
links.new(bsdf.outputs[0], out.inputs["Surface"])
saturn_rings.data.materials.append(mat)

saturn_rings.rotation_euler = (0, 0, 0)
saturn_rings.keyframe_insert(data_path="rotation_euler", frame=1)
saturn_rings.rotation_euler = (0, 0, math.radians(360 * 822.58 * SPIN_MULT))
saturn_rings.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
set_linear_interpolation(saturn_rings)

create_planet("Uranus",  R_URANUS,  D_URANUS,  0.01, -508.48)
create_planet("Neptune", R_NEPTUNE, D_NEPTUNE, 0.006, 544.12)
create_planet("Pluto",   R_PLUTO,   D_PLUTO,   0.004, -57.18)

# BACKGROUND (Stars)
bg_img = get_texture("star")
if bg_img:
    world = bpy.data.worlds.get("World")
    if not world:
        world = bpy.data.worlds.new("World")
        scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for n in nodes: nodes.remove(n)
    
    bg_node = nodes.new(type='ShaderNodeBackground')
    bg_node.inputs['Strength'].default_value = 0.5
    env_tex = nodes.new(type='ShaderNodeTexEnvironment')
    env_tex.image = bg_img
    output_node = nodes.new(type='ShaderNodeOutputWorld')
    
    links.new(env_tex.outputs['Color'], bg_node.inputs['Color'])
    links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])

# ANGLE VIEW CAMERA via Data API
cam_data = bpy.data.cameras.new("AngleCamera")
cam_data.clip_end = 50000.0
camera = bpy.data.objects.new("AngleCamera", cam_data)
bpy.context.scene.collection.objects.link(camera)
camera.location = (0, -100, 70)
camera.rotation_euler = (math.radians(55), 0, 0)
bpy.context.scene.camera = camera

if bpy.context.screen:
    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            for space in a.spaces:
                if space.type == 'VIEW_3D':
                    space.clip_end = 50000.0

# LIGHTING via Data API
light_data = bpy.data.lights.new(name="SunLight", type='SUN')
light_data.energy = 3.0
sun_light = bpy.data.objects.new("SunLight", light_data)
bpy.context.scene.collection.objects.link(sun_light)
sun_light.location = (0, 0, 10)

fill_data = bpy.data.lights.new(name="FillLight", type='AREA')
fill_data.energy = 1.0
fill_data.size = 100
fill_light = bpy.data.objects.new("FillLight", fill_data)
bpy.context.scene.collection.objects.link(fill_light)
fill_light.location = (0, 0, 50)

print("✅ Solar System Generation Complete (Robust Blender 5.1+ Compatible)!")