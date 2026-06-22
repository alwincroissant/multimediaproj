import bpy
import math
import mathutils

# Preserved planet names to prevent losing custom textures/materials when rerunning
PRESERVED_NAMES = {"Sun", "Mercury", "Venus", "Earth", "Moon", "Mars", "Jupiter", "Saturn", "Saturn_Rings", "Uranus", "Neptune", "Pluto"}

# Find existing preserved objects in the scene
preserved_objs = {}
for name in PRESERVED_NAMES:
    obj = bpy.data.objects.get(name)
    if obj:
        preserved_objs[name] = obj
        # Unparent temporarily so we can rebuild the hierarchy cleanly
        obj.parent = None
        # Clear existing animations so we can write fresh keyframes
        if obj.animation_data:
            obj.animation_data_clear()
        # Force visibility in viewport and render
        obj.hide_viewport = False
        obj.hide_render = False

# Delete all other objects safely
objects_to_delete = [obj for obj in bpy.data.objects if obj.name not in PRESERVED_NAMES]
for obj in objects_to_delete:
    bpy.data.objects.remove(obj, do_unlink=True)

# Delete meshes that are not used by preserved objects
preserved_meshes = {obj.data.name for obj in preserved_objs.values() if obj.type == 'MESH' and obj.data}
meshes_to_delete = [mesh for mesh in bpy.data.meshes if mesh.name not in preserved_meshes]
for mesh in meshes_to_delete:
    bpy.data.meshes.remove(mesh)

# Delete curves (orbits)
for curve in bpy.data.curves:
    bpy.data.curves.remove(curve)

# Delete materials that are not used by preserved objects
preserved_materials = set()
for obj in preserved_objs.values():
    for slot in obj.material_slots:
        if slot.material:
            preserved_materials.add(slot.material.name)
            
materials_to_delete = [mat for mat in bpy.data.materials if mat.name not in preserved_materials]
for mat in materials_to_delete:
    bpy.data.materials.remove(mat)

FRAMES = 1440  # 60 seconds at 24 FPS
FPS = 24

ORBIT_MULT = 5.0   # Scales up orbits so differences are clearly visible in a loop
SPIN_MULT = 0.03   # Scales down spins so planets don't strobe rapidly

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAMES
scene.render.fps = FPS

# Set active frame to 1 at start so parenting transforms are computed from unrotated state
bpy.context.scene.frame_set(1)

# Safely set keyframe interpolation
try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
except AttributeError:
    pass

# Set renderer to Eevee
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

# ==========================================
# COLORS & SIZES & DISTANCES
# ==========================================
PLANET_COLORS = {
    "Sun":     (1.0, 0.7, 0.1, 1.0),
    "Mercury": (0.65, 0.6, 0.55, 1.0),
    "Venus":   (0.85, 0.8, 0.65, 1.0),
    "Earth":   (0.2, 0.5, 0.95, 1.0),
    "Moon":    (0.65, 0.65, 0.65, 1.0),
    "ISS":     (0.7, 0.85, 1.0, 1.0),
    "Mars":    (0.85, 0.35, 0.15, 1.0),
    "Jupiter": (0.78, 0.65, 0.5, 1.0),
    "Saturn":  (0.85, 0.78, 0.58, 1.0),
    "Uranus":  (0.55, 0.82, 0.85, 1.0),
    "Neptune": (0.15, 0.35, 0.85, 1.0),
    "Pluto":   (0.7, 0.62, 0.58, 1.0),
}

planet_tilts = {
    "Sun": 7.25,
    "Mercury": 0.03,
    "Venus": 177.3,
    "Earth": 23.44,
    "Moon": 6.68,
    "Mars": 25.19,
    "Jupiter": 3.13,
    "Saturn": 26.73,
    "Uranus": 97.77,
    "Neptune": 28.32,
    "Pluto": 122.53,
}

planet_dists = {
    "Sun": 0.0,
    "Mercury": 7.0,
    "Venus": 9.5,
    "Earth": 12.5,
    "Mars": 15.5,
    "Jupiter": 21.0,
    "Saturn": 28.0,
    "Uranus": 35.0,
    "Neptune": 42.0,
    "Pluto": 48.0
}

planet_radii = {
    "Sun": 4.5,
    "Mercury": 0.18,
    "Venus": 0.38,
    "Earth": 0.40,
    "Mars": 0.22,
    "Jupiter": 2.20,
    "Saturn": 1.80,
    "Uranus": 1.10,
    "Neptune": 1.05,
    "Pluto": 0.14
}

planet_revs = {
    "Sun": 0.0,
    "Mercury": 4.15,
    "Venus": 1.62,
    "Earth": 1.0,
    "Mars": 0.53,
    "Jupiter": 0.08,
    "Saturn": 0.03,
    "Uranus": 0.01,
    "Neptune": 0.006,
    "Pluto": 0.004
}

# Earth Orbit Helpers
R_SUN     = planet_radii["Sun"]
R_MERCURY = planet_radii["Mercury"]
R_VENUS   = planet_radii["Venus"]
R_EARTH   = planet_radii["Earth"]
R_MOON    = 0.108
R_MARS    = planet_radii["Mars"]
R_JUPITER = planet_radii["Jupiter"]
R_SATURN  = planet_radii["Saturn"]
R_URANUS  = planet_radii["Uranus"]
R_NEPTUNE = planet_radii["Neptune"]
R_PLUTO   = planet_radii["Pluto"]

D_MERCURY = planet_dists["Mercury"]
D_VENUS   = planet_dists["Venus"]
D_EARTH   = planet_dists["Earth"]
D_MOON    = 0.75
D_ISS     = 0.58
D_MARS    = planet_dists["Mars"]
D_JUPITER = planet_dists["Jupiter"]
D_SATURN  = planet_dists["Saturn"]
D_URANUS  = planet_dists["Uranus"]
D_NEPTUNE = planet_dists["Neptune"]
D_PLUTO   = planet_dists["Pluto"]

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
        shader.inputs["Color"].default_value = PLANET_COLORS.get("Sun", (1.0, 0.8, 0.1, 1.0))
    else:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        base_color = PLANET_COLORS.get(name, (0.8, 0.8, 0.8, 1.0))
        shader.inputs["Base Color"].default_value = base_color
        shader.inputs["Roughness"].default_value = 0.6
        if name in ["Jupiter", "Saturn", "Uranus", "Neptune"]:
            shader.inputs["Roughness"].default_value = 0.4
        elif name == "Earth":
            shader.inputs["Roughness"].default_value = 0.3
        
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
        noise.inputs["Scale"].default_value = 8.0
        color_ramp = nodes.new("ShaderNodeValToRGB")
        
        base_color = PLANET_COLORS.get(name, (0.8, 0.8, 0.8, 1.0))
        color_dark = (base_color[0] * 0.45, base_color[1] * 0.45, base_color[2] * 0.45, 1.0)
        color_light = (min(base_color[0] * 1.35, 1.0), min(base_color[1] * 1.35, 1.0), min(base_color[2] * 1.35, 1.0), 1.0)
        
        color_ramp.color_ramp.elements[0].color = color_dark
        color_ramp.color_ramp.elements[1].color = color_light
        
        links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        if is_sun:
            links.new(color_ramp.outputs["Color"], shader.inputs["Color"])
        else:
            links.new(color_ramp.outputs["Color"], shader.inputs["Base Color"])
            
    links.new(shader.outputs[0], out.inputs["Surface"])
    obj.data.materials.append(mat)

def apply_custom_material(obj, name, color=(0.8, 0.8, 0.8, 1.0), spec=0.5, rough=0.5, emission_strength=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes: nodes.remove(n)
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = spec
        
    if emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = color[:3] + (1.0,)
        for input_name in ["Emission Strength", "Emission"]:
            if input_name in bsdf.inputs:
                bsdf.inputs[input_name].default_value = emission_strength
                
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    obj.data.materials.append(mat)

def create_orbit_line(distance, name, parent_obj=None, location=(0,0,0), color=(1.0, 1.0, 1.0, 0.5), bevel_depth=0.004):
    curve_data = bpy.data.curves.new(name=f"{name}_OrbitLine", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = bevel_depth
    curve_data.resolution_u = 64
    
    spline = curve_data.splines.new('POLY')
    pts = 128
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
    mat.blend_method = 'BLEND'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes: nodes.remove(n)
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Emission Color"].default_value = color[:3] + (1.0,)
    for name_in in ["Emission Strength", "Emission"]:
        if name_in in bsdf.inputs:
            bsdf.inputs[name_in].default_value = 0.4
    bsdf.inputs["Alpha"].default_value = color[3]
    
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    orbit_curve.data.materials.append(mat)
    
    return orbit_curve

def create_planet(name, radius, distance, orbit_revs, desired_spin_revs):
    # Orbit Empty directly via data API to avoid context errors
    orbit = bpy.data.objects.new(f"{name}_Orbit", None)
    orbit.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(orbit)
    
    # Orbit Line (colored)
    color = PLANET_COLORS.get(name, (1.0, 1.0, 1.0, 1.0))[:3] + (0.45,)
    create_orbit_line(distance, name, color=color, bevel_depth=0.004)
    
    # Check if planet body already exists
    body = preserved_objs.get(name)
    
    if body:
        # Reposition existing body and ensure visible scale
        body.location = (distance, 0, 0)
        body.scale = (1.0, 1.0, 1.0)
    else:
        # Create fresh body
        objs_before = set(bpy.context.scene.objects)
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
            import bmesh
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=radius)
            bm.to_mesh(mesh)
            bm.free()

        body.name = name
        smooth_object(body)
        apply_material(body, name)
    
    # Parent body to orbit and explicitly set local location to center it on the orbit radius
    body.parent = orbit
    body.location = (distance, 0, 0)
    body.hide_viewport = False
    body.hide_render = False
    
    # Orbit Animation
    orbit.rotation_euler = (0, 0, 0)
    orbit.keyframe_insert(data_path="rotation_euler", frame=1)
    orbit.rotation_euler = (0, 0, math.radians(360 * orbit_revs * ORBIT_MULT))
    orbit.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    set_linear_interpolation(orbit)
    
    # Spin Animation (relative to orbit)
    # Axial tilt around X axis
    tilt_rad = math.radians(planet_tilts.get(name, 0.0))
    
    # Orbit rotation in turns
    orbit_turns = orbit_revs * ORBIT_MULT
    # Local spin in turns required to achieve desired_spin_revs in world space
    local_spin_turns = desired_spin_revs - orbit_turns
    
    body.rotation_euler = (tilt_rad, 0, 0)
    body.keyframe_insert(data_path="rotation_euler", frame=1)
    body.rotation_euler = (tilt_rad, 0, math.radians(360 * local_spin_turns))
    body.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    set_linear_interpolation(body)
    
    return orbit, body

def create_iss(parent_orbit):
    # Create the ISS Tilt Empty to tilt the orbit plane 51.6 degrees
    iss_tilt = bpy.data.objects.new("ISS_Tilt", None)
    iss_tilt.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(iss_tilt)
    iss_tilt.parent = parent_orbit
    iss_tilt.location = (D_EARTH, 0, 0)
    iss_tilt.rotation_euler = (math.radians(51.6), 0, 0)
    
    # Create Orbit Line for ISS (cyan-blue, thin)
    create_orbit_line(D_ISS, "ISS", iss_tilt, location=(0, 0, 0), color=PLANET_COLORS["ISS"][:3] + (0.35,), bevel_depth=0.0008)
    
    # Create the ISS Spin Empty (for animating rotation)
    iss_spin = bpy.data.objects.new("ISS_Spin", None)
    iss_spin.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(iss_spin)
    iss_spin.parent = iss_tilt
    iss_spin.location = (0, 0, 0)
    
    # ISS Model Container
    iss_model = bpy.data.objects.new("ISS_Model", None)
    bpy.context.scene.collection.objects.link(iss_model)
    iss_model.parent = iss_spin
    iss_model.location = (D_ISS, 0, 0)
    
    # 1. Main Truss (cylinder along X)
    mesh_truss = bpy.data.meshes.new("ISS_Truss")
    obj_truss = bpy.data.objects.new("ISS_Truss", mesh_truss)
    bpy.context.scene.collection.objects.link(obj_truss)
    obj_truss.parent = iss_model
    
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=8, radius1=0.003, radius2=0.003, depth=0.22)
    # Rotate 90 degrees around Y axis to align with X axis
    import mathutils
    bmesh.ops.rotate(bm, cent=(0,0,0), matrix=mathutils.Matrix.Rotation(math.radians(90), 4, 'Y'), verts=bm.verts)
    bm.to_mesh(mesh_truss)
    bm.free()
    smooth_object(obj_truss)
    apply_custom_material(obj_truss, "ISS_TrussMat", color=(0.7, 0.7, 0.7, 1.0), spec=0.8, rough=0.2)
    
    # 2. Main Modules (a couple of cylinders along Y)
    mesh_modules = bpy.data.meshes.new("ISS_Modules")
    obj_modules = bpy.data.objects.new("ISS_Modules", mesh_modules)
    bpy.context.scene.collection.objects.link(obj_modules)
    obj_modules.parent = iss_model
    
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=12, radius1=0.009, radius2=0.009, depth=0.065)
    # Rotate 90 degrees around X to align with Y axis
    bmesh.ops.rotate(bm, cent=(0,0,0), matrix=mathutils.Matrix.Rotation(math.radians(90), 4, 'X'), verts=bm.verts)
    bm.to_mesh(mesh_modules)
    bm.free()
    smooth_object(obj_modules)
    apply_custom_material(obj_modules, "ISS_ModuleMat", color=(0.85, 0.85, 0.85, 1.0), spec=0.7, rough=0.3)
    
    # 3. Solar Panels (4 panels at the ends of the truss)
    panel_positions = [
        (-0.09, 0.045, 0.0),
        (-0.09, -0.045, 0.0),
        (0.09, 0.045, 0.0),
        (0.09, -0.045, 0.0)
    ]
    
    for i, pos in enumerate(panel_positions):
        mesh_panel = bpy.data.meshes.new(f"ISS_Panel_{i}")
        obj_panel = bpy.data.objects.new(f"ISS_Panel_{i}", mesh_panel)
        bpy.context.scene.collection.objects.link(obj_panel)
        obj_panel.parent = iss_model
        obj_panel.location = pos
        
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        # scale to width=0.02, height=0.07, thickness=0.002
        bmesh.ops.scale(bm, vec=(0.022, 0.055, 0.0015), verts=bm.verts)
        bm.to_mesh(mesh_panel)
        bm.free()
        
        apply_custom_material(obj_panel, f"ISS_PanelMat_{i}", color=(0.08, 0.15, 0.4, 1.0), spec=0.9, rough=0.1)
        
    # Animate ISS Orbit (Relative to Earth)
    iss_spin.rotation_euler = (0, 0, 0)
    iss_spin.keyframe_insert(data_path="rotation_euler", frame=1)
    iss_spin.rotation_euler = (0, 0, math.radians(360 * 15.0 * ORBIT_MULT))
    iss_spin.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    set_linear_interpolation(iss_spin)

def create_asteroid_mesh(name, radius):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    import bmesh
    import random
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=radius)
    
    # Deform rock
    for v in bm.verts:
        factor = 1.0 + random.uniform(-0.35, 0.35)
        v.co *= factor
        
    bm.to_mesh(mesh)
    bm.free()
    smooth_object(obj)
    return obj

def create_asteroid_belt(count=60):
    import random
    mat_name = "AsteroidMaterial"
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes: nodes.remove(n)
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.35, 0.3, 0.28, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    
    belt_parent = bpy.data.objects.new("AsteroidBelt", None)
    bpy.context.scene.collection.objects.link(belt_parent)
    
    for i in range(count):
        dist = random.uniform(17.2, 19.3)
        start_angle = random.uniform(0, 2 * math.pi)
        size = random.uniform(0.04, 0.12)
        height = random.uniform(-0.4, 0.4)
        orbit_revs = random.uniform(0.12, 0.28)
        
        ast = create_asteroid_mesh(f"Asteroid_{i}", size)
        ast.data.materials.append(mat)
        
        ast_orbit = bpy.data.objects.new(f"Asteroid_Orbit_{i}", None)
        bpy.context.scene.collection.objects.link(ast_orbit)
        ast_orbit.parent = belt_parent
        
        ast.parent = ast_orbit
        ast.location = (dist * math.cos(start_angle), dist * math.sin(start_angle), height)
        
        ast_orbit.rotation_euler = (0, 0, 0)
        ast_orbit.keyframe_insert(data_path="rotation_euler", frame=1)
        ast_orbit.rotation_euler = (0, 0, math.radians(360 * orbit_revs * ORBIT_MULT))
        ast_orbit.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
        set_linear_interpolation(ast_orbit)
        
        # Tumbling rotation
        ast.rotation_euler = (random.uniform(0, 3.14), random.uniform(0, 3.14), random.uniform(0, 3.14))
        ast.keyframe_insert(data_path="rotation_euler", frame=1)
        ast.rotation_euler = (ast.rotation_euler.x + random.uniform(5, 15), 
                              ast.rotation_euler.y + random.uniform(5, 15), 
                              ast.rotation_euler.z + random.uniform(5, 15))
        ast.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
        set_linear_interpolation(ast)

def create_rogue_meteors():
    import random
    import bmesh
    
    mat_meteor = bpy.data.materials.new(name="MeteorMaterial")
    mat_meteor.use_nodes = True
    nodes = mat_meteor.node_tree.nodes
    links = mat_meteor.node_tree.links
    for n in nodes: nodes.remove(n)
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.15, 0.12, 0.12, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    
    mat_tail = bpy.data.materials.new(name="MeteorTailMaterial")
    mat_tail.use_nodes = True
    mat_tail.blend_method = 'BLEND'
    nodes = mat_tail.node_tree.nodes
    links = mat_tail.node_tree.links
    for n in nodes: nodes.remove(n)
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.85, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.5, 0.85, 1.0, 1.0)
    for name_in in ["Emission Strength", "Emission"]:
        if name_in in bsdf.inputs:
            bsdf.inputs[name_in].default_value = 3.0
    bsdf.inputs["Alpha"].default_value = 0.25
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    
    meteors_data = [
        ("Meteor_Alpha", mathutils.Vector((-45.0, -35.0, 15.0)), mathutils.Vector((45.0, 25.0, -10.0)), 950, 1100, 0.18),
        ("Meteor_Beta", mathutils.Vector((35.0, -45.0, -8.0)), mathutils.Vector((-35.0, 45.0, 12.0)), 1100, 1250, 0.15),
        ("Meteor_Gamma", mathutils.Vector((-25.0, 50.0, -15.0)), mathutils.Vector((25.0, -50.0, 15.0)), 1250, 1400, 0.16)
    ]
    
    meteors_parent = bpy.data.objects.new("RogueMeteors", None)
    bpy.context.scene.collection.objects.link(meteors_parent)
    
    for name, start_pos, end_pos, start_f, end_f, size in meteors_data:
        head = create_asteroid_mesh(name, size)
        head.parent = meteors_parent
        head.data.materials.append(mat_meteor)
        
        mesh_tail = bpy.data.meshes.new(f"{name}_Tail")
        tail = bpy.data.objects.new(f"{name}_Tail", mesh_tail)
        bpy.context.scene.collection.objects.link(tail)
        tail.parent = head
        
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=12, radius1=size * 0.45, radius2=0.0, depth=size * 8.0)
        bmesh.ops.translate(bm, vec=(0, 0, size * 4.0), verts=bm.verts)
        bm.to_mesh(mesh_tail)
        bm.free()
        smooth_object(tail)
        tail.data.materials.append(mat_tail)
        
        vel = (end_pos - start_pos).normalized()
        rot_quat = (-vel).to_track_quat('Z', 'Y')
        tail.rotation_euler = rot_quat.to_euler()
        
        # Scale animation to handle visibility
        head.scale = (0.0, 0.0, 0.0)
        head.keyframe_insert(data_path="scale", frame=1)
        head.keyframe_insert(data_path="scale", frame=start_f - 1)
        
        head.scale = (1.0, 1.0, 1.0)
        head.location = start_pos
        head.keyframe_insert(data_path="scale", frame=start_f)
        head.keyframe_insert(data_path="location", frame=start_f)
        
        head.scale = (1.0, 1.0, 1.0)
        head.location = end_pos
        head.keyframe_insert(data_path="scale", frame=end_f)
        head.keyframe_insert(data_path="location", frame=end_f)
        
        head.scale = (0.0, 0.0, 0.0)
        head.keyframe_insert(data_path="scale", frame=end_f + 1)
        head.keyframe_insert(data_path="scale", frame=FRAMES)
        
        set_linear_interpolation(head)
        
        head.rotation_euler = (0, 0, 0)
        head.keyframe_insert(data_path="rotation_euler", frame=start_f)
        head.rotation_euler = (random.uniform(5, 10), random.uniform(5, 10), random.uniform(5, 10))
        head.keyframe_insert(data_path="rotation_euler", frame=end_f)
        set_linear_interpolation(head)

# ==========================================
# GENERATION START
# ==========================================

# 1. SUN
sun = preserved_objs.get("Sun")
if sun:
    sun.location = (0, 0, 0)
    sun.scale = (1.0, 1.0, 1.0)
else:
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
# Force visibility in viewport and render
sun.hide_viewport = False
sun.hide_render = False
# Tilt Sun by 7.25 degrees and animate spin (1.5 turns in world space)
tilt_sun = math.radians(7.25)
sun.rotation_euler = (tilt_sun, 0, 0)
sun.keyframe_insert(data_path="rotation_euler", frame=1)
sun.rotation_euler = (tilt_sun, 0, math.radians(360 * 1.5))
sun.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
set_linear_interpolation(sun)

# 2. PLANETS
create_planet("Mercury", R_MERCURY, D_MERCURY, 4.15,  5.53)
create_planet("Venus",   R_VENUS,   D_VENUS,   1.62, -3.0)

# EARTH, MOON, ISS
earth_orbit, earth_body = create_planet("Earth", R_EARTH, D_EARTH, 1.0, 8.0)

moon_orbit = bpy.data.objects.new("Moon_Orbit", None)
moon_orbit.empty_display_type = 'PLAIN_AXES'
bpy.context.scene.collection.objects.link(moon_orbit)
moon_orbit.parent = earth_orbit
moon_orbit.location = (D_EARTH, 0, 0)

create_orbit_line(D_MOON, "Moon", earth_orbit, location=(D_EARTH, 0, 0), color=PLANET_COLORS["Moon"][:3] + (0.35,), bevel_depth=0.0012)

# Create Moon sphere
moon_body = preserved_objs.get("Moon")
if moon_body:
    moon_body.location = (D_MOON, 0, 0)
    moon_body.scale = (1.0, 1.0, 1.0)
else:
    objs_before = set(bpy.context.scene.objects)
    try:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=R_MOON, location=(D_MOON, 0, 0))
        new_objs = set(bpy.context.scene.objects) - objs_before
        if new_objs:
            moon_body = list(new_objs)[0]
        else:
            moon_body = bpy.context.active_object
    except Exception:
        mesh = bpy.data.meshes.new("Moon")
        moon_body = bpy.data.objects.new("Moon", mesh)
        bpy.context.scene.collection.objects.link(moon_body)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=R_MOON)
        bm.to_mesh(mesh)
        bm.free()

    moon_body.name = "Moon"
    smooth_object(moon_body)
    apply_material(moon_body, "moon")

# Parent Moon to Moon_Orbit and set local coordinates
moon_body.parent = moon_orbit
moon_body.location = (D_MOON, 0, 0)
moon_body.hide_viewport = False
moon_body.hide_render = False

# Tilt Moon relative to its orbit plane (6.68 degrees)
moon_body.rotation_euler = (math.radians(6.68), 0, 0)

moon_orbit.rotation_euler = (0, 0, 0)
moon_orbit.keyframe_insert(data_path="rotation_euler", frame=1)
moon_orbit.rotation_euler = (0, 0, math.radians(360 * 13.37 * ORBIT_MULT))
moon_orbit.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
set_linear_interpolation(moon_orbit)
set_linear_interpolation(moon_body)

create_iss(earth_orbit)

# OTHER PLANETS
create_planet("Mars",    R_MARS,    D_MARS,    0.53,  7.5)
create_planet("Jupiter", R_JUPITER, D_JUPITER, 0.08, 20.0)

# SATURN & RINGS
saturn_orbit, saturn_body = create_planet("Saturn", R_SATURN, D_SATURN, 0.03, 18.0)

saturn_rings = preserved_objs.get("Saturn_Rings")
if saturn_rings:
    saturn_rings.location = (0, 0, 0)
    saturn_rings.rotation_euler = (0, 0, 0)
    saturn_rings.scale = (1.0, 1.0, 1.0)
else:
    objs_before = set(bpy.context.scene.objects)
    try:
        # Create at local origin (0, 0, 0) relative to Saturn body
        bpy.ops.mesh.primitive_cylinder_add(radius=R_SATURN * 2.2, depth=0.01, location=(0, 0, 0))
        new_objs = set(bpy.context.scene.objects) - objs_before
        if new_objs:
            saturn_rings = list(new_objs)[0]
        else:
            saturn_rings = bpy.context.active_object
    except Exception:
        mesh = bpy.data.meshes.new("Saturn_Rings")
        saturn_rings = bpy.data.objects.new("Saturn_Rings", mesh)
        bpy.context.scene.collection.objects.link(saturn_rings)
        saturn_rings.location = (0, 0, 0)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=32, radius1=R_SATURN * 1.1, radius2=R_SATURN * 1.1, depth=0.01)
        bm.to_mesh(mesh)
        bm.free()

    saturn_rings.name = "Saturn_Rings"
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
        bsdf.inputs["Base Color"].default_value = (0.78, 0.72, 0.62, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    saturn_rings.data.materials.append(mat)

# Parent rings directly to saturn_body and center them
saturn_rings.parent = saturn_body
saturn_rings.location = (0, 0, 0)
saturn_rings.rotation_euler = (0, 0, 0)

create_planet("Uranus",  R_URANUS,  D_URANUS,  0.01, -14.0)
create_planet("Neptune", R_NEPTUNE, D_NEPTUNE, 0.006, 15.0)
create_planet("Pluto",   R_PLUTO,   D_PLUTO,   0.004, -4.0)

# PROCEDURAL ASTEROIDS & METEORS
create_asteroid_belt(count=60)
create_rogue_meteors()

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

# ==========================================
# CINEMATIC CAMERA SYSTEM & BAKING
# ==========================================

stages = [
    ("Sun", 1, 35),
    ("Mercury", 65, 100),
    ("Venus", 130, 165),
    ("Earth", 195, 265),
    ("Mars", 295, 330),
    ("Jupiter", 360, 395),
    ("Saturn", 425, 460),
    ("Uranus", 490, 525),
    ("Neptune", 555, 590),
    ("Pluto", 620, 655),
    ("Cinematic", 720, 1080),
    ("Wide", 1080, 1440)
]

def get_cinematic_pos(F):
    F_clamped = max(720, min(1080, F))
    t = (F_clamped - 720) / 360.0
    
    P0 = mathutils.Vector((38.0, 28.0, 10.0))
    P1 = mathutils.Vector((-14.0, -10.0, 2.0))
    P2 = mathutils.Vector((0.0, -115.0, 70.0))
    
    cam_pos = (1.0 - t)**2 * P0 + 2.0 * (1.0 - t) * t * P1 + t**2 * P2
    
    # We query target positions at F_clamped
    T0 = get_world_pos("Saturn", F_clamped)
    T1 = get_world_pos("Earth", F_clamped)
    T2 = mathutils.Vector((0.0, 0.0, 0.0))
    
    target_pos = (1.0 - t)**2 * T0 + 2.0 * (1.0 - t) * t * T1 + t**2 * T2
    
    return target_pos, cam_pos

def get_world_pos(name, F):
    if name == "Cinematic":
        target_pos, _ = get_cinematic_pos(F)
        return target_pos
        
    if name == "Sun" or name == "Wide":
        return mathutils.Vector((0.0, 0.0, 0.0))
        
    D = planet_dists[name]
    revs = planet_revs[name]
    
    angle_deg = (F - 1) * (360.0 * revs * ORBIT_MULT) / (FRAMES - 1)
    angle_rad = math.radians(angle_deg)
    
    return mathutils.Vector((D * math.cos(angle_rad), D * math.sin(angle_rad), 0.0))

def get_camera_focus_pos(name, F):
    if name == "Cinematic":
        _, cam_pos = get_cinematic_pos(F)
        return cam_pos
        
    if name == "Sun":
        return mathutils.Vector((0.0, -22.0, 9.0))
        
    if name == "Wide":
        # Slowly rotating wide shot (using new start frame 1080)
        angle_rad = math.radians((F - 1080) * 0.25)
        r_wide = 115.0
        return mathutils.Vector((r_wide * math.sin(angle_rad), -r_wide * math.cos(angle_rad), 70.0))
        
    R = planet_radii[name]
    D = planet_dists[name]
    revs = planet_revs[name]
    
    angle_deg = (F - 1) * (360.0 * revs * ORBIT_MULT) / (FRAMES - 1)
    theta = math.radians(angle_deg)
    
    # Camera distance is 4.5 * R. Position it closer to the Sun and slightly offset.
    alpha = (3.0 * R) / D if D != 0 else 0.0
    phi = theta - alpha
    
    cam_dist_factor = 7.2 if name == "Earth" else 5.5
    cam_z_factor = 2.8 if name == "Earth" else 2.2
    
    x = (D - cam_dist_factor * R) * math.cos(phi)
    y = (D - cam_dist_factor * R) * math.sin(phi)
    z = R * cam_z_factor
    
    return mathutils.Vector((x, y, z))

# Create Camera Target Empty
camera_target = bpy.data.objects.new("CameraTarget", None)
bpy.context.scene.collection.objects.link(camera_target)

# Setup AngleCamera
cam_data = bpy.data.cameras.new("AngleCamera")
cam_data.clip_end = 50000.0
camera = bpy.data.objects.new("AngleCamera", cam_data)
bpy.context.scene.collection.objects.link(camera)
bpy.context.scene.camera = camera

if bpy.context.screen:
    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            for space in a.spaces:
                if space.type == 'VIEW_3D':
                    space.clip_end = 50000.0

# Add Track To constraint to Camera
track_constraint = camera.constraints.new(type='TRACK_TO')
track_constraint.target = camera_target
track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
track_constraint.up_axis = 'UP_Y'

# Animate Camera & Target frame by frame
for frame in range(1, FRAMES + 1):
    target_pos = None
    camera_pos = None
    
    inside_stage = False
    for i, (name, start, end) in enumerate(stages):
        if start <= frame <= end:
            target_pos = get_world_pos(name, frame)
            camera_pos = get_camera_focus_pos(name, frame)
            inside_stage = True
            break
            
    if not inside_stage:
        for i in range(len(stages) - 1):
            name1, start1, end1 = stages[i]
            name2, start2, end2 = stages[i+1]
            if end1 < frame < start2:
                # Interpolate using smoothstep (S-curve)
                t = (frame - end1) / (start2 - end1)
                smooth_t = 3 * (t ** 2) - 2 * (t ** 3)
                
                T1 = get_world_pos(name1, frame)
                C1 = get_camera_focus_pos(name1, frame)
                
                T2 = get_world_pos(name2, frame)
                C2 = get_camera_focus_pos(name2, frame)
                
                target_pos = (1.0 - smooth_t) * T1 + smooth_t * T2
                camera_pos = (1.0 - smooth_t) * C1 + smooth_t * C2
                break
                
    if target_pos is not None and camera_pos is not None:
        camera_target.location = target_pos
        camera_target.keyframe_insert(data_path="location", frame=frame)
        camera.location = camera_pos
        camera.keyframe_insert(data_path="location", frame=frame)

set_linear_interpolation(camera_target)
set_linear_interpolation(camera)

print("✅ Solar System Generation Complete (With Tilted ISS, Asteroid Belt, Rogue Meteors, Colored Orbits, and Cinematic Camera Tour)!")