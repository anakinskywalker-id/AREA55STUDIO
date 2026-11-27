import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Euler

# -------------------------------------------------------------
# 1. INITIALIZE CLEAN SCENE
# -------------------------------------------------------------
# Clear existing objects and materials cleanly
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat, do_unlink=True)
for col in list(bpy.context.scene.collection.children):
    bpy.context.scene.collection.children.unlink(col)

scene = bpy.context.scene
scene.name = "FloorPlan_3D"
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else 'BLENDER_EEVEE'
if scene.render.engine not in [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]:
    scene.render.engine = 'CYCLES'  # fallback

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.film_transparent = False

# Collections
col_walls = bpy.data.collections.new("01_Walls")
col_doors = bpy.data.collections.new("02_Doors")
col_windows = bpy.data.collections.new("03_Windows")
col_floors = bpy.data.collections.new("04_Floors")
col_fixtures = bpy.data.collections.new("05_Fixtures")
col_staging = bpy.data.collections.new("06_Staging")

for c in [col_walls, col_doors, col_windows, col_floors, col_fixtures, col_staging]:
    scene.collection.children.link(c)

# -------------------------------------------------------------
# 2. CREATE MATERIALS
# -------------------------------------------------------------
def make_material(name, base_color, roughness=0.5, metallic=0.0, transmission=0.0, ior=1.45, alpha=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    
    # Base color
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0) if len(base_color) == 3 else base_color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    
    # Transmission / Alpha for glass
    if 'Transmission Weight' in bsdf.inputs:
        bsdf.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in bsdf.inputs:
        bsdf.inputs['Transmission'].default_value = transmission
        
    if 'IOR' in bsdf.inputs:
        bsdf.inputs['IOR'].default_value = ior
    if 'Alpha' in bsdf.inputs:
        bsdf.inputs['Alpha'].default_value = alpha
        
    if transmission > 0.1 or alpha < 0.99:
        mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else 'HASHED'
        if hasattr(mat, 'shadow_method'):
            mat.shadow_method = 'HASHED'
            
    return mat

# Palette
mat_wall = make_material("Mat_Wall", (0.95, 0.94, 0.92), roughness=0.7)
mat_wall_exterior = make_material("Mat_Wall_Exterior", (0.90, 0.89, 0.87), roughness=0.8)
mat_floor_living = make_material("Mat_Floor_Terrazzo", (0.88, 0.86, 0.83), roughness=0.25)
mat_floor_wood = make_material("Mat_Floor_Oak", (0.75, 0.58, 0.38), roughness=0.35)
mat_floor_deck = make_material("Mat_Floor_TeakDeck", (0.50, 0.32, 0.18), roughness=0.6)
mat_floor_parking = make_material("Mat_Floor_Pavers", (0.35, 0.36, 0.38), roughness=0.7)
mat_floor_bath = make_material("Mat_Floor_Slate", (0.28, 0.30, 0.32), roughness=0.45)
mat_floor_gravel = make_material("Mat_Floor_Gravel", (0.78, 0.76, 0.72), roughness=0.9)
mat_plinth = make_material("Mat_Plinth_Concrete", (0.65, 0.64, 0.62), roughness=0.8)

mat_frame = make_material("Mat_Aluminum_Dark", (0.12, 0.12, 0.13), roughness=0.3, metallic=0.8)
mat_door_leaf = make_material("Mat_Door_Wood", (0.58, 0.38, 0.22), roughness=0.4)
mat_door_handle = make_material("Mat_Door_Chrome", (0.85, 0.85, 0.85), roughness=0.15, metallic=0.95)
mat_glass = make_material("Mat_Glass_Clear", (0.95, 0.98, 1.0), roughness=0.03, transmission=0.95, alpha=0.3)
mat_tub = make_material("Mat_Tub_Ceramic", (0.98, 0.98, 0.98), roughness=0.15)

# -------------------------------------------------------------
# 3. HELPER FUNCTIONS FOR MESH CREATION
# -------------------------------------------------------------
def create_box(name, x, y, z, sx, sy, sz, mat=None, collection=None):
    """Creates an axis-aligned box with origin at center."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = (x + sx/2.0, y + sy/2.0, z + sz/2.0)
    obj.scale = (sx, sy, sz)
    
    # Apply transform so scale is 1, 1, 1
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    
    if mat:
        obj.data.materials.append(mat)
    if collection:
        bpy.context.collection.objects.unlink(obj)
        collection.objects.link(obj)
        
    return obj

WALL_H = 2.80     # Wall height in meters
DOOR_H = 2.20     # Door opening height
WIN_H = 2.40      # Window / sliding door height
WIN_SILL = 0.50   # Regular window sill height

def create_wall(name, x0, y0, x1, y1, thickness=0.15, height=WALL_H, mat=mat_wall):
    """Creates a wall between (x0, y0) and (x1, y1)."""
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length < 0.001:
        return None
    angle = math.atan2(dy, dx)
    
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    
    # center position
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    cz = height / 2.0
    
    obj.location = (cx, cy, cz)
    obj.rotation_euler = (0, 0, angle)
    obj.scale = (length, thickness, height)
    
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    
    obj.data.materials.append(mat)
    bpy.context.collection.objects.unlink(obj)
    col_walls.objects.link(obj)
    return obj

def create_door_assembly(name, x, y, z, width, depth, is_open=True, angle_deg=25.0, flip=False):
    """Creates a realistic door with frame, panel and handle."""
    frame_th = 0.05
    door_th = 0.04
    height = DOOR_H
    
    # 1. Door Frame
    # Left jamb
    create_box(f"{name}_FrameL", x, y, z, frame_th, depth, height, mat_frame, col_doors)
    # Right jamb
    create_box(f"{name}_FrameR", x + width - frame_th, y, z, frame_th, depth, height, mat_frame, col_doors)
    # Top head
    create_box(f"{name}_FrameT", x, y, z + height - frame_th, width, depth, frame_th, mat_frame, col_doors)
    
    # 2. Door Panel
    panel_w = width - 2 * frame_th
    panel_h = height - frame_th - 0.01
    
    mesh = bpy.data.meshes.new(f"{name}_Leaf")
    leaf = bpy.data.objects.new(f"{name}_Leaf", mesh)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    
    # Pivot at hinge
    hinge_x = x + frame_th if not flip else x + width - frame_th
    hinge_y = y + depth/2.0
    hinge_z = z + panel_h/2.0
    
    rot_rad = math.radians(angle_deg if not flip else -angle_deg) if is_open else 0.0
    leaf.location = (hinge_x, hinge_y, hinge_z)
    leaf.rotation_euler = (0, 0, rot_rad)
    leaf.scale = (panel_w, door_th, panel_h)
    
    # Offset mesh vertices so pivot is at hinge edge
    for v in mesh.vertices:
        if not flip:
            v.co.x += 0.5
        else:
            v.co.x -= 0.5
            
    leaf.data.materials.append(mat_door_leaf)
    col_doors.objects.link(leaf)
    
    # 3. Handle
    handle_x = hinge_x + (panel_w * 0.85) * math.cos(rot_rad) if not flip else hinge_x - (panel_w * 0.85) * math.cos(rot_rad)
    handle_y = hinge_y + (panel_w * 0.85) * math.sin(rot_rad)
    handle = create_box(f"{name}_Handle", handle_x - 0.02, handle_y - 0.04, z + 1.0, 0.04, 0.08, 0.04, mat_door_handle, col_doors)
    return leaf

def create_sliding_glass_wall(name, x0, y0, x1, y1, height=WIN_H, panels=3):
    """Creates a floor-to-ceiling glass sliding door with mullions and glass."""
    dx = x1 - x0
    dy = y1 - y0
    total_w = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    frame_d = 0.10
    frame_w = 0.05
    
    # Outer frame
    # Bottom rail
    rail_b = create_box(f"{name}_RailB", 0, -frame_d/2, 0, total_w, frame_d, 0.04, mat_frame, col_windows)
    # Top rail
    rail_t = create_box(f"{name}_RailT", 0, -frame_d/2, height - 0.04, total_w, frame_d, 0.04, mat_frame, col_windows)
    # Left side
    side_l = create_box(f"{name}_SideL", 0, -frame_d/2, 0, frame_w, frame_d, height, mat_frame, col_windows)
    # Right side
    side_r = create_box(f"{name}_SideR", total_w - frame_w, -frame_d/2, 0, frame_w, frame_d, height, mat_frame, col_windows)
    
    # Panels
    pw = (total_w - 2 * frame_w) / panels
    panel_objs = [rail_b, rail_t, side_l, side_r]
    
    for i in range(panels):
        px = frame_w + i * pw
        # Vertical mullion between panels
        if i > 0:
            mull = create_box(f"{name}_Mullion_{i}", px - 0.02, -frame_d/2, 0, 0.04, frame_d, height, mat_frame, col_windows)
            panel_objs.append(mull)
        # Glass pane
        glass = create_box(f"{name}_Glass_{i}", px + 0.02, -0.005, 0.04, pw - 0.04, 0.01, height - 0.08, mat_glass, col_windows)
        panel_objs.append(glass)
        
    # Header wall above sliding door up to ceiling
    if height < WALL_H:
        head_wall = create_box(f"{name}_HeaderWall", 0, -0.075, height, total_w, 0.15, WALL_H - height, mat_wall, col_walls)
        panel_objs.append(head_wall)
        
    # Rotate and translate assembly
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    for obj in panel_objs:
        lx, ly, lz = obj.location
        # Rotate around (0,0)
        rx = lx * cos_a - ly * sin_a
        ry = lx * sin_a + ly * cos_a
        obj.location = (x0 + rx, y0 + ry, lz)
        obj.rotation_euler.z += angle

def create_window(name, x0, y0, x1, y1, sill=0.9, height=1.4):
    """Creates a regular window with sill wall, frame, glass, and header wall."""
    dx = x1 - x0
    dy = y1 - y0
    total_w = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    th = 0.15
    
    # 1. Sill wall
    sill_w = create_box(f"{name}_SillWall", 0, -th/2, 0, total_w, th, sill, mat_wall, col_walls)
    # 2. Window Frame
    frame_d = 0.08
    frame_w = 0.04
    fb = create_box(f"{name}_FrameB", 0, -frame_d/2, sill, total_w, frame_d, frame_w, mat_frame, col_windows)
    ft = create_box(f"{name}_FrameT", 0, -frame_d/2, sill + height - frame_w, total_w, frame_d, frame_w, mat_frame, col_windows)
    fl = create_box(f"{name}_FrameL", 0, -frame_d/2, sill, frame_w, frame_d, height, mat_frame, col_windows)
    fr = create_box(f"{name}_FrameR", total_w - frame_w, -frame_d/2, sill, frame_w, frame_d, height, mat_frame, col_windows)
    # Center mullion
    fm = create_box(f"{name}_FrameM", total_w/2 - frame_w/2, -frame_d/2, sill, frame_w, frame_d, height, mat_frame, col_windows)
    # Glass panes
    gw = (total_w - 3*frame_w)/2
    g1 = create_box(f"{name}_Glass1", frame_w, -0.005, sill + frame_w, gw, 0.01, height - 2*frame_w, mat_glass, col_windows)
    g2 = create_box(f"{name}_Glass2", total_w/2 + frame_w/2, -0.005, sill + frame_w, gw, 0.01, height - 2*frame_w, mat_glass, col_windows)
    # 3. Header wall
    head_h = WALL_H - (sill + height)
    head_w = create_box(f"{name}_HeaderWall", 0, -th/2, sill + height, total_w, th, head_h, mat_wall, col_walls)
    
    # Rotate & position
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    for obj in [sill_w, fb, ft, fl, fr, fm, g1, g2, head_w]:
        lx, ly, lz = obj.location
        rx = lx * cos_a - ly * sin_a
        ry = lx * sin_a + ly * cos_a
        obj.location = (x0 + rx, y0 + ry, lz)
        obj.rotation_euler.z += angle

print("Helper functions defined.")

# -------------------------------------------------------------
# 4. BUILDING WALLS LAYOUT (Exact 30.7m x 10.2m)
# -------------------------------------------------------------
T_OUT = 0.20   # Outer boundary wall thickness
T_IN = 0.15    # Interior wall thickness

# A. Outer Boundary Walls
# North Wall (Y = 10.2)
create_wall("Wall_Outer_North", 0.0, 10.2, 30.7, 10.2, thickness=T_OUT, mat=mat_wall_exterior)

# South Wall (Y = 0.0)
create_wall("Wall_Outer_South", 0.0, 0.0, 30.7, 0.0, thickness=T_OUT, mat=mat_wall_exterior)

# East Wall (X = 30.7) - Rear garden back wall
create_wall("Wall_Outer_East", 30.7, 0.0, 30.7, 10.2, thickness=T_OUT, mat=mat_wall_exterior)

# West Wall (X = 0.0) - Front Entrance Wall with Gate Opening
# Solid lower part (0.0 to 1.3)
create_wall("Wall_Front_L", 0.0, 0.0, 0.0, 1.3, thickness=T_OUT, mat=mat_wall_exterior)
# Gate header above car entrance (1.3 to 4.6, from Z=2.4 to 2.8)
create_box("Gate_Header", -T_OUT/2, 1.3, 2.4, T_OUT, 3.3, 0.4, mat_wall_exterior, col_walls)
# Solid upper part (4.6 to 10.2)
create_wall("Wall_Front_R", 0.0, 4.6, 0.0, 10.2, thickness=T_OUT, mat=mat_wall_exterior)

# Front Gate (Slats & Frame)
create_box("Gate_Pillar_L", -0.12, 1.25, 0.0, 0.24, 0.10, 2.4, mat_frame, col_doors)
create_box("Gate_Pillar_R", -0.12, 4.55, 0.0, 0.24, 0.10, 2.4, mat_frame, col_doors)
# Gate leaves (slightly open)
create_box("Gate_Leaf_1", -0.05, 1.35, 0.1, 0.05, 1.6, 2.2, mat_frame, col_doors)
create_box("Gate_Leaf_2", -0.05, 2.95, 0.1, 0.05, 1.6, 2.2, mat_frame, col_doors)

# B. Front Zone Dividers (X = 7.1)
# Parking divider to storage:
create_wall("Wall_Storage_Front", 7.1, 0.0, 7.1, 1.25, thickness=T_IN)
# Deck to Dining sliding door (4.2 to 8.2):
create_sliding_glass_wall("GlassDoor_FrontDeck_Dining", 7.1, 4.2, 7.1, 8.2, height=WIN_H, panels=4)
# Header wall between 8.2 and 10.2 with entrance door to Lobby 04:
create_wall("Wall_Deck_Lobby_Bot", 7.1, 8.2, 7.1, 8.6, thickness=T_IN)
create_door_assembly("Door_MainEntrance", 7.1, 8.6, 0.0, 1.0, T_IN, is_open=True, angle_deg=35)
create_box("Wall_MainDoor_Lintel", 7.1 - T_IN/2, 8.6, DOOR_H, T_IN, 1.0, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_Deck_Lobby_Top", 7.1, 9.6, 7.1, 10.2, thickness=T_IN)

# C. Storage Rooms 08 & Kitchen 07 & Dining 06 (X = 7.1 to 12.2)
# Storage north wall (dividing storage from kitchen at Y = 1.25):
create_wall("Wall_Storage_N1", 7.1, 1.25, 8.2, 1.25, thickness=T_IN)
create_door_assembly("Door_Storage_1", 8.2, 1.25, 0.0, 0.8, T_IN, is_open=False)
create_box("Door_Storage_1_Lintel", 8.2, 1.25 - T_IN/2, DOOR_H, 0.8, T_IN, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_Storage_N2", 9.0, 1.25, 10.2, 1.25, thickness=T_IN)
create_door_assembly("Door_Storage_2", 10.2, 1.25, 0.0, 0.8, T_IN, is_open=False)
create_box("Door_Storage_2_Lintel", 10.2, 1.25 - T_IN/2, DOOR_H, 0.8, T_IN, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_Storage_N3", 11.0, 1.25, 12.2, 1.25, thickness=T_IN)
# Vertical divider between storage 1 and 2:
create_wall("Wall_Storage_Divider", 9.6, 0.0, 9.6, 1.25, thickness=T_IN)

# Wall dividing Dining and Guest Restroom 05 / Lobby:
create_wall("Wall_Dining_Lobby_Pillar", 7.1, 8.2, 7.5, 8.2, thickness=T_IN)
# Beam / opening over dining-lobby transition (7.5 to 10.5):
create_box("Beam_Dining_Lobby", 7.5, 8.2 - T_IN/2, 2.5, 3.0, T_IN, WALL_H - 2.5, mat_wall, col_walls)
# Guest WC 05 walls (X = 10.5 to 12.2, Y = 8.8 to 10.2):
create_wall("Wall_WC05_South", 10.5, 8.8, 12.2, 8.8, thickness=T_IN)
create_wall("Wall_WC05_West_L", 10.5, 8.8, 10.5, 9.1, thickness=T_IN)
create_door_assembly("Door_GuestWC", 10.5, 9.1, 0.0, 0.8, T_IN, is_open=True, angle_deg=45)
create_box("Door_GuestWC_Lintel", 10.5 - T_IN/2, 9.1, DOOR_H, T_IN, 0.8, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_WC05_West_T", 10.5, 9.9, 10.5, 10.2, thickness=T_IN)

# D. Central Courtyard 10 & Workspace 11 (X = 12.2 to 16.1)
# Wall at X = 12.2:
# Storage/Workspace divider at bottom (0.0 to 1.25):
create_wall("Wall_Storage_Workspace_Divider", 12.2, 0.0, 12.2, 1.25, thickness=T_IN)
# Sliding glass wall between Dining 06 and Central Courtyard 10 (Y = 2.3 to 8.2):
create_sliding_glass_wall("GlassDoor_Dining_Courtyard1", 12.2, 2.3, 12.2, 8.2, height=WIN_H, panels=5)
# Top wall of Courtyard 10 along Corridor 09 (Y = 8.2, X = 12.2 to 16.1):
create_sliding_glass_wall("GlassWall_Courtyard1_Corridor", 12.2, 8.2, 16.1, 8.2, height=WIN_H, panels=4)

# Workspace 11 (X = 12.2 to 16.1, Y = 0.0 to 2.3):
# North wall facing courtyard (sliding glass facade):
create_sliding_glass_wall("GlassDoor_Workspace_Courtyard1", 12.2, 2.3, 16.1, 2.3, height=WIN_H, panels=3)

# E. Master Suite 12, 13, 14 & Corridor (X = 16.1 to 20.5)
# Wall at X = 16.1:
# Glass wall from Master Bed 12 to Central Courtyard 10 (Y = 4.35 to 8.2):
create_sliding_glass_wall("GlassDoor_Master_Courtyard1", 16.1, 4.35, 16.1, 8.2, height=WIN_H, panels=4)
# Solid wall for dressing room & bath at west (Y = 0.0 to 4.35):
create_wall("Wall_Master_West_Solid", 16.1, 0.0, 16.1, 4.35, thickness=T_IN)

# Corridor wall on north of Master Bed (Y = 8.2, X = 16.1 to 20.5):
create_wall("Wall_Master_Corridor_L", 16.1, 8.2, 16.6, 8.2, thickness=T_IN)
create_door_assembly("Door_MasterBedroom", 16.6, 8.2, 0.0, 0.9, T_IN, is_open=True, angle_deg=30)
create_box("Door_Master_Lintel", 16.6, 8.2 - T_IN/2, DOOR_H, 0.9, T_IN, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_Master_Corridor_R", 17.5, 8.2, 20.5, 8.2, thickness=T_IN)

# Partition wall between Master Bedroom 12 and Dressing Room 13 (Y = 4.35):
create_wall("Wall_Master_Dressing_L", 16.1, 4.35, 17.8, 4.35, thickness=T_IN)
# Open archway / portal in middle (17.8 to 19.0):
create_box("Arch_Master_Dressing", 17.8, 4.35 - T_IN/2, 2.4, 1.2, T_IN, WALL_H - 2.4, mat_wall, col_walls)
create_wall("Wall_Master_Dressing_R", 19.0, 4.35, 20.5, 4.35, thickness=T_IN)

# Partition between Dressing Room 13 and Master Bathroom 14 (Y = 2.05):
create_wall("Wall_Master_Bath_Divider_L", 16.1, 2.05, 17.2, 2.05, thickness=T_IN)
create_door_assembly("Door_MasterBath", 17.2, 2.05, 0.0, 0.8, T_IN, is_open=True, angle_deg=40)
create_box("Door_MasterBath_Lintel", 17.2, 2.05 - T_IN/2, DOOR_H, 0.8, T_IN, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_Master_Bath_Divider_R", 18.0, 2.05, 20.5, 2.05, thickness=T_IN)

# F. Second Courtyard 10 & Outdoor Bathtub 15 & Restrooms 14 (X = 20.5 to 25.3)
# Wall at X = 20.5:
# Glass wall from Master Bed 12 facing Second Courtyard (Y = 4.35 to 8.2):
create_sliding_glass_wall("GlassDoor_Master_Courtyard2", 20.5, 4.35, 20.5, 8.2, height=WIN_H, panels=4)
# Outdoor bathtub courtyard privacy wall (Y = 2.05 to 4.35):
create_wall("Wall_Tub_Courtyard_Divider", 20.5, 4.35, 22.8, 4.35, thickness=T_IN)
create_sliding_glass_wall("GlassDoor_MasterBath_OutdoorTub", 20.5, 2.05, 20.5, 4.35, height=WIN_H, panels=2)
# Master bath south solid wall (Y = 0.0 to 2.05):
create_wall("Wall_MasterBath_East", 20.5, 0.0, 20.5, 2.05, thickness=T_IN)

# Outdoor Bathtub 15 east screen wall:
create_wall("Wall_Tub_East", 22.8, 2.05, 22.8, 4.35, thickness=T_IN)

# Family / Guest Bathroom 14 (X = 20.5 to 25.3, Y = 0.0 to 2.05):
create_wall("Wall_FamBath_Divider", 23.0, 0.0, 23.0, 2.05, thickness=T_IN)
create_door_assembly("Door_FamBath", 23.2, 2.05, 0.0, 0.8, T_IN, is_open=True, angle_deg=30)
create_box("Door_FamBath_Lintel", 23.2, 2.05 - T_IN/2, DOOR_H, 0.8, T_IN, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_FamBath_N", 24.0, 2.05, 25.3, 2.05, thickness=T_IN)

# Study / Learning space 16 (X = 23.0 to 25.3, Y = 4.35 to 8.2):
# Glass wall overlooking courtyard 2:
create_sliding_glass_wall("GlassWall_Study_Courtyard2", 23.0, 4.35, 23.0, 8.2, height=WIN_H, panels=2)

# G. Children's Bedrooms 18 & Laundry 17 (X = 25.3 to 28.7)
# West wall of Child Bedrooms at X = 25.3:
# Bottom section to Bed 2 door:
create_wall("Wall_Bed2_West_B", 25.3, 0.0, 25.3, 2.2, thickness=T_IN)
create_door_assembly("Door_ChildBed2", 25.3, 2.2, 0.0, 0.9, T_IN, is_open=True, angle_deg=35)
create_box("Door_ChildBed2_Lintel", 25.3 - T_IN/2, 2.2, DOOR_H, T_IN, 0.9, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_BedDivider_West_M", 25.3, 3.1, 25.3, 4.8, thickness=T_IN)
create_door_assembly("Door_ChildBed1", 25.3, 4.8, 0.0, 0.9, T_IN, is_open=True, angle_deg=35)
create_box("Door_ChildBed1_Lintel", 25.3 - T_IN/2, 4.8, DOOR_H, T_IN, 0.9, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_BedLaundry_West_M", 25.3, 5.7, 25.3, 8.6, thickness=T_IN)
create_door_assembly("Door_Laundry", 25.3, 8.6, 0.0, 0.8, T_IN, is_open=False)
create_box("Door_Laundry_Lintel", 25.3 - T_IN/2, 8.6, DOOR_H, T_IN, 0.8, WALL_H - DOOR_H, mat_wall, col_walls)
create_wall("Wall_Laundry_West_T", 25.3, 9.4, 25.3, 10.2, thickness=T_IN)

# Partition wall between Child Bed 1 and Child Bed 2 (Y = 4.35, X = 25.3 to 28.7):
create_wall("Wall_ChildBed_Partition", 25.3, 4.35, 28.7, 4.35, thickness=T_IN)

# Partition wall between Child Bed 1 and Laundry 17 (Y = 8.2, X = 25.3 to 28.7):
create_wall("Wall_Laundry_Bed1_Partition", 25.3, 8.2, 28.7, 8.2, thickness=T_IN)

# East wall of Bedrooms facing Rear Garden 10 (X = 28.7):
# Child Bed 2 large window / sliding door (Y = 0.6 to 3.8):
create_wall("Wall_Bed2_East_B", 28.7, 0.0, 28.7, 0.6, thickness=T_IN)
create_window("Window_ChildBed2", 28.7, 0.6, 28.7, 3.8, sill=0.5, height=1.9)
create_wall("Wall_BedEast_M", 28.7, 3.8, 28.7, 4.9, thickness=T_IN)
# Child Bed 1 large window / sliding door (Y = 4.9 to 7.6):
create_window("Window_ChildBed1", 28.7, 4.9, 28.7, 7.6, sill=0.5, height=1.9)
create_wall("Wall_BedEast_T", 28.7, 7.6, 28.7, 8.2, thickness=T_IN)
# Laundry window / door (Y = 8.5 to 9.8):
create_window("Window_Laundry", 28.7, 8.5, 28.7, 9.8, sill=0.9, height=1.3)
create_wall("Wall_Laundry_East_T", 28.7, 9.8, 28.7, 10.2, thickness=T_IN)

# Corridor 09 Ribbon Windows along North Outer Wall:
create_window("Window_Corridor_1", 12.5, 10.2, 15.5, 10.2, sill=1.2, height=1.0)
create_window("Window_Corridor_2", 17.0, 10.2, 20.0, 10.2, sill=1.2, height=1.0)
create_window("Window_Corridor_3", 21.0, 10.2, 24.5, 10.2, sill=1.2, height=1.0)

# Outdoor Bathtub 15 - Luxury Oval Tub in Courtyard
tub_mesh = bpy.data.meshes.new("Outdoor_Bathtub")
tub_obj = bpy.data.objects.new("Outdoor_Bathtub", tub_mesh)
bm_tub = bmesh.new()
bmesh.ops.create_cone(bm_tub, cap_ends=True, cap_tris=False, segments=24, radius1=0.85, radius2=0.75, depth=0.6)
bm_tub.to_mesh(tub_mesh)
bm_tub.free()
tub_obj.location = (21.6, 3.2, 0.3)
tub_obj.scale = (0.7, 1.1, 1.0)
tub_obj.data.materials.append(mat_tub)
col_fixtures.objects.link(tub_obj)

print("All walls, doors, windows, and outdoor tub created.")

# -------------------------------------------------------------
# 5. FLOORS & PLATFORMS (Distinct slabs for each zone)
# -------------------------------------------------------------
FL_TH = 0.08   # Floor slab thickness
FL_Z = -FL_TH  # Top of floor at Z = 0.0

# 1. Foundation Ground Plinth
create_box("Floor_Ground_Plinth", -0.5, -0.5, -0.30, 31.7, 11.2, 0.22, mat_plinth, col_floors)

# 2. Parking 02 (Dark concrete pavers)
create_box("Floor_02_Parking", 0.0, 0.0, FL_Z, 7.1, 4.8, FL_TH, mat_floor_parking, col_floors)

# 3. Front Patio Deck 03 (Teak timber decking)
create_box("Floor_03_FrontDeck", 0.0, 4.8, FL_Z + 0.02, 7.1, 5.4, FL_TH, mat_floor_deck, col_floors)

# 4. Storage Rooms 08 (Utility tile)
create_box("Floor_08_Storage", 7.1, 0.0, FL_Z, 5.1, 1.25, FL_TH, mat_floor_parking, col_floors)

# 5. Living & Dining 06 & Kitchen 07 & Lobby 04 (Polished Terrazzo/Porcelain)
create_box("Floor_06_07_DiningKitchen", 7.1, 1.25, FL_Z, 5.1, 7.55, FL_TH, mat_floor_living, col_floors)
create_box("Floor_04_Lobby", 7.1, 8.8, FL_Z, 3.4, 1.4, FL_TH, mat_floor_living, col_floors)
create_box("Floor_05_GuestWC", 10.5, 8.8, FL_Z, 1.7, 1.4, FL_TH, mat_floor_bath, col_floors)

# 6. Central Courtyard 10 (Gravel bed with stone stepping slabs)
create_box("Floor_10_Courtyard1_Gravel", 12.2, 2.3, FL_Z, 3.9, 5.9, FL_TH * 0.8, mat_floor_gravel, col_floors)
# Stepping stones across courtyard:
for i in range(4):
    create_box(f"Step_Court1_{i}", 12.8 + i*0.7, 3.5 + (i%2)*0.6, 0.01, 0.6, 0.9, 0.03, mat_floor_living, col_floors)

# 7. Workspace 11 (Warm oak wood floor)
create_box("Floor_11_Workspace", 12.2, 0.0, FL_Z, 3.9, 2.3, FL_TH, mat_floor_wood, col_floors)

# 8. Corridor 09 (North passage connecting all zones)
create_box("Floor_09_Corridor_Mid", 12.2, 8.2, FL_Z, 13.1, 2.0, FL_TH, mat_floor_living, col_floors)

# 9. Master Suite (Master Bed 12, Dressing 13, Bath 14)
create_box("Floor_12_MasterBed", 16.1, 4.35, FL_Z, 4.4, 3.85, FL_TH, mat_floor_wood, col_floors)
create_box("Floor_13_DressingRoom", 16.1, 2.05, FL_Z, 4.4, 2.3, FL_TH, mat_floor_wood, col_floors)
create_box("Floor_14_MasterBath", 16.1, 0.0, FL_Z, 4.4, 2.05, FL_TH, mat_floor_bath, col_floors)

# 10. Second Courtyard 10 & Outdoor Bathtub 15 & Bath 14
create_box("Floor_10_Courtyard2_Gravel", 20.5, 4.35, FL_Z, 2.5, 3.85, FL_TH * 0.8, mat_floor_gravel, col_floors)
create_box("Floor_15_OutdoorTubDeck", 20.5, 2.05, FL_Z + 0.01, 2.3, 2.3, FL_TH, mat_floor_deck, col_floors)
create_box("Floor_14_FamilyBath", 20.5, 0.0, FL_Z, 4.8, 2.05, FL_TH, mat_floor_bath, col_floors)

# 11. Study 16
create_box("Floor_16_Study", 23.0, 4.35, FL_Z, 2.3, 3.85, FL_TH, mat_floor_wood, col_floors)

# 12. Children's Bedrooms 18 & Laundry 17
create_box("Floor_18_ChildBed1", 25.3, 4.35, FL_Z, 3.4, 3.85, FL_TH, mat_floor_wood, col_floors)
create_box("Floor_18_ChildBed2", 25.3, 0.0, FL_Z, 3.4, 4.35, FL_TH, mat_floor_wood, col_floors)
create_box("Floor_17_Laundry", 25.3, 8.2, FL_Z, 3.4, 2.0, FL_TH, mat_floor_bath, col_floors)

# 13. Rear Garden 10
create_box("Floor_10_RearGarden_Gravel", 28.7, 0.0, FL_Z, 2.0, 10.2, FL_TH * 0.8, mat_floor_gravel, col_floors)
for i in range(5):
    create_box(f"Step_RearGarden_{i}", 29.3, 1.0 + i*1.8, 0.01, 0.8, 0.6, 0.03, mat_floor_living, col_floors)

print("All floors created.")

# -------------------------------------------------------------
# 6. LIGHTING SETUP
# -------------------------------------------------------------
# Sun Light (Warm architectural sunlight)
sun_data = bpy.data.lights.new(name="Sun_Main", type='SUN')
sun_data.energy = 4.5
sun_data.color = (1.0, 0.96, 0.90)
sun_data.angle = math.radians(8.0)
sun_obj = bpy.data.objects.new(name="Sun_Main", object_data=sun_data)
sun_obj.location = (15.0, 5.0, 25.0)
sun_obj.rotation_euler = (math.radians(45.0), math.radians(20.0), math.radians(-55.0))
col_staging.objects.link(sun_obj)

# Soft Sky Fill Light
fill_data = bpy.data.lights.new(name="Sun_Fill", type='SUN')
fill_data.energy = 1.8
fill_data.color = (0.85, 0.92, 1.0)
fill_data.angle = math.radians(30.0)
fill_obj = bpy.data.objects.new(name="Sun_Fill", object_data=fill_data)
fill_obj.location = (15.0, 5.0, 25.0)
fill_obj.rotation_euler = (math.radians(-30.0), math.radians(-15.0), math.radians(125.0))
col_staging.objects.link(fill_obj)

# World background color
world = bpy.data.worlds.new("ArchWorld")
world.use_nodes = True
bg_node = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg_node.inputs['Color'].default_value = (0.92, 0.94, 0.97, 1.0)
bg_node.inputs['Strength'].default_value = 0.85
scene.world = world

# -------------------------------------------------------------
# 7. CAMERAS (Multiple Architectural Angles with Precise Look-At)
# -------------------------------------------------------------
def set_camera_look_at(cam_obj, target):
    direction = Vector(target) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

center_target = Vector((15.35, 5.1, 1.2))

# Camera 1: Master Isometric 3D (South-West to North-East)
cam1_data = bpy.data.cameras.new("Cam_Isometric_SW")
cam1_data.type = 'ORTHO'
cam1_data.ortho_scale = 36.0
cam1_data.clip_start = 0.1
cam1_data.clip_end = 200.0
cam1_obj = bpy.data.objects.new("Cam_Isometric_SW", cam1_data)
cam1_obj.location = Vector((15.35 - 22.0, 5.1 - 25.0, 24.0))
set_camera_look_at(cam1_obj, center_target)
col_staging.objects.link(cam1_obj)

# Camera 2: Isometric 3D (South-East to North-West - Rear View)
cam2_data = bpy.data.cameras.new("Cam_Isometric_SE")
cam2_data.type = 'ORTHO'
cam2_data.ortho_scale = 36.0
cam2_data.clip_start = 0.1
cam2_data.clip_end = 200.0
cam2_obj = bpy.data.objects.new("Cam_Isometric_SE", cam2_data)
cam2_obj.location = Vector((15.35 + 22.0, 5.1 - 25.0, 24.0))
set_camera_look_at(cam2_obj, center_target)
col_staging.objects.link(cam2_obj)

# Camera 3: Top-Down Axonometric (3D Plan View)
cam3_data = bpy.data.cameras.new("Cam_TopDown_3D")
cam3_data.type = 'ORTHO'
cam3_data.ortho_scale = 34.0
cam3_data.clip_start = 0.1
cam3_data.clip_end = 200.0
cam3_obj = bpy.data.objects.new("Cam_TopDown_3D", cam3_data)
cam3_obj.location = Vector((15.35, 5.1, 40.0))
cam3_obj.rotation_euler = (0, 0, 0)
col_staging.objects.link(cam3_obj)

# Camera 4: Perspective 3D Cutaway (Elevated Cinematic View)
cam4_data = bpy.data.cameras.new("Cam_Perspective_Cutaway")
cam4_data.type = 'PERSP'
cam4_data.lens = 28
cam4_data.clip_start = 0.1
cam4_data.clip_end = 200.0
cam4_obj = bpy.data.objects.new("Cam_Perspective_Cutaway", cam4_data)
cam4_obj.location = Vector((-4.0, -12.0, 15.0))
set_camera_look_at(cam4_obj, Vector((13.0, 5.0, 1.0)))
col_staging.objects.link(cam4_obj)

# Camera 5: Courtyard & Living Detail Close-Up
cam5_data = bpy.data.cameras.new("Cam_Courtyard_Detail")
cam5_data.type = 'PERSP'
cam5_data.lens = 40
cam5_obj = bpy.data.objects.new("Cam_Courtyard_Detail", cam5_data)
cam5_obj.location = Vector((7.0, -4.5, 9.5))
set_camera_look_at(cam5_obj, Vector((14.0, 4.5, 1.0)))
col_staging.objects.link(cam5_obj)

print("Cameras and lights created.")

# -------------------------------------------------------------
# 8. SAVE FILE AND RENDER PREVIEWS
# -------------------------------------------------------------
out_blend = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/house_floorplan_3d.blend"
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("Saved blend file to:", out_blend)

# 1. Render Isometric SW
scene.camera = cam1_obj
render_path1 = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/render_isometric_sw.png"
scene.render.filepath = render_path1
bpy.ops.render.render(write_still=True)
print("Rendered isometric SW to:", render_path1)

# 2. Render Isometric SE
scene.camera = cam2_obj
render_path2 = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/render_isometric_se.png"
scene.render.filepath = render_path2
bpy.ops.render.render(write_still=True)
print("Rendered isometric SE to:", render_path2)

# 3. Render Top-Down 3D
scene.camera = cam3_obj
render_path3 = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/render_topdown.png"
scene.render.filepath = render_path3
bpy.ops.render.render(write_still=True)
print("Rendered topdown to:", render_path3)

# 4. Render Perspective Cutaway
scene.camera = cam4_obj
render_path4 = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/render_perspective.png"
scene.render.filepath = render_path4
bpy.ops.render.render(write_still=True)
print("Rendered perspective to:", render_path4)

# 5. Render Courtyard Detail
scene.camera = cam5_obj
render_path5 = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/render_courtyard.png"
scene.render.filepath = render_path5
bpy.ops.render.render(write_still=True)
print("Rendered courtyard detail to:", render_path5)

# Export GLB / GLTF
glb_path = r"C:/Users/Ust. Udin/.gemini/antigravity/scratch/floorplan_3d/house_floorplan_3d.glb"
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')
print("Exported GLB to:", glb_path)
print("ALL DONE SUCCESSFULLY!")
