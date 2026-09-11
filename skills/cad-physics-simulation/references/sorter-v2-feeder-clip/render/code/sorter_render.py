"""Blender pipeline for the sorter V2 master assembly renders.

Run with Blender in background mode:

  /Applications/Blender.app/Contents/MacOS/Blender -b --python sorter_render.py -- \
      --gltf /path/to/sorter.gltf --out /path/to/outdir --stage preview

Stages:
  preview    low-res contact strip of azimuths, to pick the hero angle
  stills     the named views, RGBA with a shadow catcher floor
  turntable  RGBA PNG sequence of one full rotation (encode with ffmpeg after)
  clip       a feeder clip replayed from a physics log (sorter-v2-sim's sim.clip): rotors
             turned and pieces placed per frame, filmed from the log's camera.json
  blend      just import + materials + scene, save the .blend

The glTF is Onshape's assembly export (instance names as node names, one
material per face appearance). Materials are assigned by part name and by the
sub-assembly the part sits in, per Spencer's spec (2026-09-10).
"""

import argparse
import math
import os
import re
import sys

import bpy
import mathutils
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ldraw_parts import LDraw  # noqa: E402

# --------------------------------------------------------------------------- args

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--gltf", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--stage", default="preview",
                choices=["preview", "stills", "turntable", "clip", "blend"])
ap.add_argument("--traj", default="", help="clip stage: a sim clip dir (traj.npz, meta.json, camera.json)")
ap.add_argument("--look", default="photo", choices=["photo", "cad"],
                help="clip stage: photo = the approved Cycles look, cad = Onshape's (Workbench)")
ap.add_argument("--limit", type=int, default=0, help="clip stage: render only the first N frames")
ap.add_argument("--samples", type=int, default=0)
ap.add_argument("--scale", type=float, default=1.0, help="resolution multiplier")
ap.add_argument("--views", default="", help="comma list of still view names")
ap.add_argument("--frames", type=int, default=240)
ap.add_argument("--frame-start", type=int, default=1)
ap.add_argument("--frame-end", type=int, default=0)
ap.add_argument("--hero-az", type=float, default=290.0)
ap.add_argument("--blend", default="", help="save .blend here after setup")
ap.add_argument("--piles", default="", help="piles.json from fill_bins.py: LEGO pieces to place in the bins")
ap.add_argument("--ldraw", default="/Users/spencer/Documents/ldraw")
ap.add_argument("--photo-stage", action="store_true",
                help="light the floor with the studio lights and let it bounce onto the machine, like a real "
                     "white stage; the shadow is then rebuilt from the --occlusion pass")
ap.add_argument("--occlusion", action="store_true",
                help="render the floor occlusion pass: within --ao-short in red, --ao-long in green")
ap.add_argument("--ao-short", type=float, default=0.08, help="metres: where the machine touches the floor")
ap.add_argument("--ao-long", type=float, default=0.6, help="metres: the soft pool under the machine")
ap.add_argument("--mask", action="store_true",
                help="render object coverage only (flat white, no floor) for stage_shadow.py")
ap.add_argument("--shadow-key", type=float, default=3200.0,
                help="watts of the shadowed overhead floor-only light; more = tighter pool, whiter floor")
ap.add_argument("--shadow-fill", type=float, default=2400.0,
                help="watts of the unshadowed floor-only light that lifts the pool's core; 0 = full density")
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)

# ----------------------------------------------------------------- materials

def _principled(name, color, rough=0.7, metal=0.0, spec=0.5, emit=None, emit_str=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Specular IOR Level"].default_value = spec
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_str
    return m


def _cardboard(name):
    """Kraft board: an even tan liner with faint cm-scale mottling and a fine fibre speckle
    and bump. Own-object coordinates, so the pattern rides along on the turntable."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    L = nt.links.new
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mottle = nt.nodes.new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value = 30.0
    mottle.inputs["Detail"].default_value = 4.0
    mottle.inputs["Roughness"].default_value = 0.55
    tone = nt.nodes.new("ShaderNodeValToRGB")
    tone.color_ramp.elements[0].position = 0.30
    tone.color_ramp.elements[0].color = (0.43, 0.255, 0.115, 1.0)
    tone.color_ramp.elements[1].position = 0.70
    tone.color_ramp.elements[1].color = (0.53, 0.325, 0.150, 1.0)
    fibre = nt.nodes.new("ShaderNodeTexNoise")
    fibre.inputs["Scale"].default_value = 1400.0
    fibre.inputs["Detail"].default_value = 2.0
    speck = nt.nodes.new("ShaderNodeValToRGB")
    speck.color_ramp.elements[0].position = 0.3
    speck.color_ramp.elements[0].color = (0.92, 0.92, 0.92, 1.0)
    speck.color_ramp.elements[1].position = 0.7
    speck.color_ramp.elements[1].color = (1.05, 1.05, 1.05, 1.0)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    fbump = nt.nodes.new("ShaderNodeBump")
    fbump.inputs["Strength"].default_value = 0.15
    fbump.inputs["Distance"].default_value = 0.0002
    L(coord.outputs["Object"], mottle.inputs["Vector"])
    L(coord.outputs["Object"], fibre.inputs["Vector"])
    L(mottle.outputs["Fac"], tone.inputs["Fac"])
    L(fibre.outputs["Fac"], speck.inputs["Fac"])
    L(tone.outputs["Color"], mul.inputs[6])
    L(speck.outputs["Color"], mul.inputs[7])
    L(mul.outputs[2], bsdf.inputs["Base Color"])
    L(fibre.outputs["Fac"], fbump.inputs["Height"])
    L(fbump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.88
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    bsdf.inputs["Sheen Weight"].default_value = 0.25
    return m


def _plywood(name, frame_obj):
    """Birch plywood: a pale face veneer with long, low-contrast streaks along the grain and
    soft broad figure; the edges show the ply stack with a dark glue line at each boundary.
    Root-local coordinates (X and Z span the plate, Y is world up) so the grain runs one way
    across the top and stays put on the turntable."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    L = nt.links.new
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.object = frame_obj
    # face: noise stretched 20x along X reads as grain lines
    stretch = nt.nodes.new("ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (0.05, 1.0, 1.0)
    streak = nt.nodes.new("ShaderNodeTexNoise")
    streak.inputs["Scale"].default_value = 120.0
    streak.inputs["Detail"].default_value = 4.0
    streak.inputs["Roughness"].default_value = 0.45
    face = nt.nodes.new("ShaderNodeValToRGB")
    face.color_ramp.elements[0].position = 0.32
    face.color_ramp.elements[0].color = (0.64, 0.47, 0.27, 1.0)
    face.color_ramp.elements[1].position = 0.68
    face.color_ramp.elements[1].color = (0.80, 0.63, 0.41, 1.0)
    fig_map = nt.nodes.new("ShaderNodeMapping")
    fig_map.inputs["Scale"].default_value = (0.2, 1.0, 1.0)
    figure = nt.nodes.new("ShaderNodeTexNoise")
    figure.inputs["Scale"].default_value = 9.0
    figure.inputs["Detail"].default_value = 2.0
    fig = nt.nodes.new("ShaderNodeValToRGB")
    fig.color_ramp.elements[0].position = 0.35
    fig.color_ramp.elements[0].color = (0.90, 0.88, 0.86, 1.0)
    fig.color_ramp.elements[1].position = 0.65
    fig.color_ramp.elements[1].color = (1.05, 1.05, 1.04, 1.0)
    fmul = nt.nodes.new("ShaderNodeMix")
    fmul.data_type = "RGBA"
    fmul.blend_type = "MULTIPLY"
    fmul.inputs[0].default_value = 1.0
    # edges: plies stacked along Y (~1.8 mm each), boundaries wobbled a little
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    wobble = nt.nodes.new("ShaderNodeTexNoise")
    wobble.inputs["Scale"].default_value = 150.0
    wobble.inputs["Detail"].default_value = 1.0
    wob = nt.nodes.new("ShaderNodeMath")
    wob.operation = "MULTIPLY"
    wob.inputs[1].default_value = 0.35
    stack = nt.nodes.new("ShaderNodeMath")
    stack.operation = "MULTIPLY_ADD"
    stack.inputs[1].default_value = 560.0
    frac = nt.nodes.new("ShaderNodeMath")
    frac.operation = "FRACT"
    plies = nt.nodes.new("ShaderNodeValToRGB")
    cr = plies.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.28, 0.17, 0.08, 1.0)      # glue line
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.50, 0.34, 0.18, 1.0)
    e = cr.elements.new(0.08); e.color = (0.78, 0.60, 0.38, 1.0)   # long-grain ply
    e = cr.elements.new(0.50); e.color = (0.74, 0.56, 0.34, 1.0)
    e = cr.elements.new(0.56); e.color = (0.56, 0.39, 0.21, 1.0)   # cross ply, end grain
    # face where the normal is vertical, plies elsewhere
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nsep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nabs = nt.nodes.new("ShaderNodeMath")
    nabs.operation = "ABSOLUTE"
    ngt = nt.nodes.new("ShaderNodeMath")
    ngt.operation = "GREATER_THAN"
    ngt.inputs[1].default_value = 0.6
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.0002
    L(coord.outputs["Object"], stretch.inputs["Vector"])
    L(stretch.outputs["Vector"], streak.inputs["Vector"])
    L(streak.outputs["Fac"], face.inputs["Fac"])
    L(coord.outputs["Object"], fig_map.inputs["Vector"])
    L(fig_map.outputs["Vector"], figure.inputs["Vector"])
    L(figure.outputs["Fac"], fig.inputs["Fac"])
    L(face.outputs["Color"], fmul.inputs[6])
    L(fig.outputs["Color"], fmul.inputs[7])
    L(coord.outputs["Object"], sep.inputs["Vector"])
    L(coord.outputs["Object"], wobble.inputs["Vector"])
    L(wobble.outputs["Fac"], wob.inputs[0])
    L(sep.outputs["Y"], stack.inputs[0])
    L(wob.outputs["Value"], stack.inputs[2])
    L(stack.outputs["Value"], frac.inputs[0])
    L(frac.outputs["Value"], plies.inputs["Fac"])
    L(geo.outputs["Normal"], nsep.inputs["Vector"])
    L(nsep.outputs["Z"], nabs.inputs[0])
    L(nabs.outputs["Value"], ngt.inputs[0])
    L(ngt.outputs["Value"], mix.inputs[0])
    L(plies.outputs["Color"], mix.inputs[6])   # A: edges
    L(fmul.outputs[2], mix.inputs[7])          # B: face
    L(mix.outputs[2], bsdf.inputs["Base Color"])
    L(streak.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Specular IOR Level"].default_value = 0.4
    return m


MATS = {}


def make_mats(frame_obj):
    return {
    "plywood": _plywood("Plywood", frame_obj),
    "pla_black": _principled("PLA matte black", (0.012, 0.012, 0.012), rough=0.72, spec=0.45),
    "pla_white": _principled("PLA matte white", (0.86, 0.86, 0.85), rough=0.68, spec=0.45),
    "pla_gray": _principled("PLA matte gray", (0.20, 0.20, 0.20), rough=0.70, spec=0.45),
    "alu_black": _principled("Anodized black aluminum", (0.02, 0.02, 0.022), rough=0.42, metal=0.75, spec=0.6),
    "chrome": _principled("Chrome fastener", (0.82, 0.82, 0.82), rough=0.28, metal=1.0),
    "cardboard": _cardboard("Cardboard"),
    "reflector": _principled("Lamp reflector (emissive)", (0.92, 0.92, 0.92), rough=0.55, spec=0.4,
                             emit=(1.0, 0.96, 0.90), emit_str=6.0),
    }


def add_lamp_lights(mesh_objs):
    """One small warm point light inside each lamp reflector, since the emissive
    surface itself is excluded from light sampling."""
    MATS["reflector"].cycles.emission_sampling = "NONE"
    n = 0
    for o in mesh_objs:
        if part_name(o) != "lamp inner reflector":
            continue
        lo_, hi_ = bbox_of([o])
        c = (lo_ + hi_) / 2
        ld = bpy.data.lights.new(f"LampLight.{n}", "POINT")
        ld.energy = 2.0
        ld.color = (1.0, 0.95, 0.88)
        ld.shadow_soft_size = 0.02
        lo = bpy.data.objects.new(ld.name, ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.parent = o
        lo.matrix_parent_inverse = o.matrix_world.inverted()
        lo.location = c
        n += 1
    return n

# ---------------------------------------------------------- classification

FASTENER = re.compile(
    r"(screw|washer|\bnut\b|hex nut|flange nut|slot nut|insert|ruthex|rivet|parallel pin|"
    r"t-slot|set screw|boss)", re.I)
BIN = re.compile(r"^bin_(half|third)_", re.I)
FUNNEL = re.compile(r"funnel", re.I)
PROFILE = re.compile(r"(2020 guide profile|vertical_beam|top_beam)", re.I)
KEEP = re.compile(
    r"(caster|servo|mg995|wires-1|wire boot|"
    r"06247695|pcb|conductor ribbon|ribbon wire|idc|jst|pin ?header|socket$|capacitor|"
    r"orange pi 5 |usb|hdmi|rj45|tmc2209|pico|rp2040|heatsink|label|led|selector|"
    r"terminal block|voltage trim|mean well|psu internal|psu cooling fan|psu fan hub|"
    r"acridine|waveshare|converter|receptacle|stub|mock-|_0603_|c1_actual|"
    r"conn_|pca9|25mhz|tactile|bootsel|adapter-populated|envelope|foot connector|"
    r"2020 m6)", re.I)
CHUTE_WHITE = re.compile(
    r"(gen4_core|gen3_bearing|gen3_flap|gen3_servo_(cover|side_connector|housing)|"
    r"gen3_side_arm|gen3_lower_arm|gen3_chute_flap|gen3 connector|gen3 top connector|"
    r"gen3_left_bearing)", re.I)
ELEC_BOX = re.compile(
    r"^(base|wall-(west|east|north|south)|roof|duct|antenna-clamp-(backer|base|cap)|hub-clamp|"
    r"buck-clamp|plunger(-retainer|-cap)?|cover|retainer|shell front module|shell rear tray|"
    r"front panel|lid front|lid rear)$", re.I)
LED_HOOK = re.compile(r"inner reflector led hook", re.I)


def part_name(obj):
    return re.sub(r"\.\d{3}$", "", obj.name)


def ancestors(obj):
    out = []
    p = obj.parent
    while p is not None:
        out.append(p.name)
        p = p.parent
    return " / ".join(out)


def classify(obj):
    n = part_name(obj)
    anc = ancestors(obj)
    if BIN.search(n):
        return "cardboard"
    if n == "lamp inner reflector":
        return "reflector"
    if LED_HOOK.search(n):
        return "pla_white"
    if n.startswith("Top plate"):
        return "plywood"
    if n == "cage_bracket_ribbon":
        return "pla_black"
    if re.search(r"(dummy camera|nema17|nema23|stepper|mg995|mock-)", n, re.I):
        return "pla_black"
    if re.search(r"(lazy_susan|lazy suzan|shaft-1)", n, re.I):
        return "chrome"
    if n == "Servomotor arm":
        return "pla_white"
    if FASTENER.search(n):
        return "chrome"
    if FUNNEL.search(n):
        return "pla_gray"
    if PROFILE.search(n):
        return "alu_black"
    if "0002_Chute" in anc and CHUTE_WHITE.search(n):
        return "pla_white"
    if re.search(r"(Orange Pi assembly|Basically board assembly|PSU assembly)", anc) and ELEC_BOX.search(n):
        return "pla_black"
    if KEEP.search(n):
        return None
    if "0002_Chute" in anc:
        return None
    if "full feeder assembly" in anc:
        return "pla_gray"
    if re.search(r"(Orange Pi assembly|Basically board assembly|PSU assembly)", anc):
        return None
    # frame layers, interface layer, bottom interface: printed structure
    return "pla_black"


def assign_materials(mesh_objs):
    report = {}
    for o in mesh_objs:
        key = classify(o)
        label = part_name(o)
        if key is None:
            cols = []
            for slot in o.material_slots:
                m = slot.material
                if m and m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
                    cols.append(tuple(round(v, 2) for v in m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3]))
            label = f"{label}  {cols[:3]}  [{ancestors(o).split(' / ')[0]}]"
        report.setdefault(key, set()).add(label)
        if key is None:
            continue
        mat = MATS[key]
        if not o.material_slots:
            o.data.materials.append(mat)
        for slot in o.material_slots:
            slot.link = "OBJECT"
            slot.material = mat
    # kept Onshape appearances come in at roughness 1.0; make them plastic-ish
    mine = set(MATS.values())
    for m in bpy.data.materials:
        if m not in mine and m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
            m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
    return report


# ------------------------------------------------------------------- scene

def bbox_of(objs):
    lo = mathutils.Vector((1e9, 1e9, 1e9))
    hi = mathutils.Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            v = o.matrix_world @ mathutils.Vector(c)
            lo.x, lo.y, lo.z = min(lo.x, v.x), min(lo.y, v.y), min(lo.z, v.z)
            hi.x, hi.y, hi.z = max(hi.x, v.x), max(hi.y, v.y), max(hi.z, v.z)
    return lo, hi


def corners(lo, hi):
    return [mathutils.Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]


def subtree(root):
    out = [root]
    for c in root.children:
        out.extend(subtree(c))
    return out


def look_at(obj, target):
    d = target - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_area(name, loc, target, size, power, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size = size[0]
    ld.size_y = size[1]
    ld.energy = power
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    return o


def sph(az_deg, el_deg, r, center):
    """Position on a sphere: az 0 = on -Y side (front), increasing counter-clockwise from above."""
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    return center + mathutils.Vector((
        r * math.cos(el) * math.sin(az),
        -r * math.cos(el) * math.cos(az),
        r * math.sin(el)))


def setup_world():
    w = bpy.data.worlds.new("Studio")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, math.radians(-90.0), 0.0)
    grad = nt.nodes.new("ShaderNodeTexGradient")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.18, 0.18, 0.19, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.75, 0.76, 0.78, 1)
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.45
    # camera rays don't see the world (film is transparent anyway); keep it for lighting
    return w


def setup_lights(center, height):
    r = height * 2.3
    add_area("Key", sph(-40, 45, r, center), center, (2.2, 2.2), 170)
    add_area("Fill", sph(70, 20, r, center), center, (3.0, 3.0), 60, (0.96, 0.97, 1.0))
    add_area("Rim", sph(180 - 25, 55, r, center), center, (1.5, 3.0), 140, (1.0, 0.98, 0.95))
    # the overhead softbox is the one studio light that shades the floor (setup_shadow):
    # big and centred, so its shadow is a soft pool under the machine, not a cast one
    add_area("Top", center + mathutils.Vector((0, 0, height * 1.6)), center, (4.0, 4.0), 55)


def setup_floor(z, size=30.0):
    # big enough that its far edge sits where the faint shadow tail has died out
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    f = bpy.context.active_object
    f.name = "Floor"
    f.is_shadow_catcher = True
    m = _principled("Floor", (0.8, 0.8, 0.8), rough=0.9)
    f.data.materials.append(m)
    f.visible_glossy = False
    f.visible_diffuse = args.photo_stage
    return f


def setup_shadow(floor, center, key_watts, fill_watts):
    """Shape the shadow-catcher shadow. Key, fill and rim light the machine but not the
    floor. The floor gets its own pair of overhead lights, centred on the machine so the
    turntable orbit leaves them alone: a shadowed floor key that makes a compact pool at the
    base and drowns out the sky's broad falloff across the floor, and an unshadowed floor
    fill that lifts the pool's core. Neither touches the machine."""
    if args.photo_stage:
        return   # the studio lights reach the floor too; the shadow comes from the occlusion pass
    no_floor = bpy.data.collections.new("NoFloor")
    no_floor.objects.link(floor)
    no_floor.collection_objects[0].light_linking.link_state = "EXCLUDE"
    for name in ("Key", "Fill", "Rim"):
        bpy.data.objects[name].light_linking.receiver_collection = no_floor
    floor_only = bpy.data.collections.new("FloorOnly")
    floor_only.objects.link(floor)
    base = mathutils.Vector((center.x, center.y, floor.location.z))
    for name, up, size, watts, shadow in (("FloorKey", 5.0, 1.2, key_watts, True),
                                          ("FloorFill", 3.5, 6.0, fill_watts, False)):
        if watts <= 0:
            continue
        o = add_area(name, base + mathutils.Vector((0, 0, up)), base, (size, size), watts)
        o.data.use_shadow = shadow
        o.visible_camera = False
        o.light_linking.receiver_collection = floor_only


def setup_render(samples, res, transparent=True):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    # first backend that has a device wins: OptiX (RTX), CUDA, Metal (Apple)
    for backend in ("OPTIX", "CUDA", "METAL"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.refresh_devices()
        if any(d.type == backend for d in prefs.devices):
            break
    for d in prefs.devices:
        d.use = d.type == prefs.compute_device_type
    print("CYCLES DEVICE", prefs.compute_device_type, [d.name for d in prefs.devices if d.use])
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.01
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.denoising_use_gpu = True
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.use_persistent_data = True
    sc.render.film_transparent = transparent
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 50
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.dither_intensity = 1.0
    if args.occlusion:
        sc.cycles.samples = 32               # the floor's occlusion is smooth: few samples, denoised
        sc.cycles.use_adaptive_sampling = False
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 0
        sc.view_settings.view_transform = "Standard"   # linear values, only sRGB-encoded
        sc.view_settings.look = "None"
    if args.mask:
        sc.cycles.samples = 128
        sc.cycles.use_adaptive_sampling = False
        sc.cycles.use_denoising = False
        sc.cycles.max_bounces = 0


def cad_look(res):
    """Onshape's look: every part in the appearance colour the export carries, flat studio
    light, dark outlines and creases. Workbench rasterises it on the GPU in well under a
    second a frame."""
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.name.startswith("piece_"):
            for slot in o.material_slots:
                slot.link = "DATA"                 # back to the export's own materials
    for m in bpy.data.materials:
        if m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
            base = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
            if not base.is_linked:
                m.diffuse_color = base.default_value   # Workbench draws the viewport colour
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = True
    sh.object_outline_color = (0.08, 0.08, 0.08)
    sh.show_specular_highlight = True
    sc.display.render_aa = "16"
    sc.world.color = (1.0, 1.0, 1.0)
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 15


def fit_camera(cam, corner_pts, az, el, focal, margin=0.06, center=None, zoom=1.0):
    """Place cam on the sphere at (az, el) around `center` and back it off until every
    corner projects inside the frame with `margin`."""
    sc = bpy.context.scene
    cam.data.lens = focal
    cam.data.sensor_fit = "AUTO"
    lo, hi = 0.05, 50.0
    for _ in range(40):
        r = (lo + hi) / 2
        cam.location = sph(az, el, r, center)
        look_at(cam, center)
        bpy.context.view_layer.update()
        ok = True
        for p in corner_pts:
            v = world_to_camera_view(sc, cam, p)
            if v.x < margin or v.x > 1 - margin or v.y < margin or v.y > 1 - margin or v.z <= 0:
                ok = False
                break
        if ok:
            hi = r
        else:
            lo = r
    cam.location = sph(az, el, hi * zoom, center)
    look_at(cam, center)
    bpy.context.view_layer.update()
    return hi * zoom


# --------------------------------------------------------------------- main

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args.gltf)
root = bpy.data.objects["0001_Main"]
root.rotation_mode = "XYZ"
root.rotation_euler = (math.radians(-90.0), 0.0, 0.0)
bpy.context.view_layer.update()

MATS.update(make_mats(root))
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
report = assign_materials(meshes)
with open(os.path.join(args.out, "material_report.txt"), "w") as fh:
    for key in sorted(report, key=lambda k: str(k)):
        fh.write(f"=== {key} ({len(report[key])} part names)\n")
        for n in sorted(report[key], key=str.lower):
            fh.write(f"    {n}\n")

lo, hi = bbox_of(meshes)
center = (lo + hi) / 2
height = hi.z - lo.z
print(f"BBOX lo={tuple(round(v,3) for v in lo)} hi={tuple(round(v,3) for v in hi)} height={height:.3f}")
casters = [o for o in meshes if part_name(o).startswith("Caster rubber tire")]
if casters:
    clo, chi = bbox_of(casters)
    print(f"CASTER z range {clo.z:.3f}..{chi.z:.3f} (should sit at bbox bottom {lo.z:.3f})")

setup_world()
setup_lights(center, height)
print("LAMP LIGHTS", add_lamp_lights(meshes))


def place_piles(path):
    """Instance the simulated LEGO pieces: shared mesh per part, colour per object,
    parented to the machine root so they ride the turntable."""
    import json
    lib = LDraw(args.ldraw)
    piles = json.load(open(path))
    inv = root.matrix_world.inverted()
    coll = bpy.data.collections.new("LEGO")
    bpy.context.scene.collection.children.link(coll)
    n = 0
    variants = {}       # (part, colour) -> mesh with the colour baked into slot 0, so Cycles instances it
    per_object = bool(os.environ.get("PILES_OBJECT_MATS"))
    for bin_name, entry in piles.items():
        for pc in entry["pieces"]:
            key = (pc["part"], pc["colour"])
            if per_object:
                me = lib.mesh(pc["part"])
            else:
                me = variants.get(key)
                if me is None:
                    me = lib.mesh(pc["part"]).copy()
                    me.name = f"ld_{pc['part']}_c{pc['colour']}"
                    if me.materials:
                        me.materials[0] = lib.material(pc["colour"])
                    variants[key] = me
            ob = bpy.data.objects.new(f"lego_{n}", me)
            coll.objects.link(ob)
            ob.matrix_world = mathutils.Matrix(pc["matrix"])
            ob.parent = root
            ob.matrix_parent_inverse = inv
            if per_object and ob.material_slots:
                ob.material_slots[0].link = "OBJECT"
                ob.material_slots[0].material = lib.material(pc["colour"])
            n += 1
    print(f"PILES {len(piles)} bins, {n} pieces, {len(lib._meshes)} part meshes, {len(variants)} part/colour variants")
    return n


if args.piles:
    place_piles(args.piles)
floor = setup_floor(lo.z + 0.001)
setup_shadow(floor, center, args.shadow_key, args.shadow_fill)
if args.mask:
    # same cameras and pixel filter as the beauty pass, but only the machine's coverage
    floor.hide_render = True
    flat = bpy.data.materials.new("Mask")
    flat.use_nodes = True
    flat.node_tree.nodes.clear()
    em = flat.node_tree.nodes.new("ShaderNodeEmission")
    mo = flat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    flat.node_tree.links.new(em.outputs[0], mo.inputs["Surface"])
    bpy.context.view_layer.material_override = flat
if args.occlusion:
    # the floor's ambient occlusion as an opaque emissive floor: red within --ao-short (where the
    # machine touches it), green within --ao-long (the soft pool under it); no lights, machine black
    floor.is_shadow_catcher = False
    om = bpy.data.materials.new("Occlusion")
    om.use_nodes = True
    nt = om.node_tree
    nt.nodes.clear()
    near = nt.nodes.new("ShaderNodeAmbientOcclusion")
    near.samples = 8
    near.inputs["Distance"].default_value = args.ao_short
    far = nt.nodes.new("ShaderNodeAmbientOcclusion")
    far.samples = 8
    far.inputs["Distance"].default_value = args.ao_long
    rg = nt.nodes.new("ShaderNodeCombineColor")
    em = nt.nodes.new("ShaderNodeEmission")
    mo = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(near.outputs["AO"], rg.inputs["Red"])
    nt.links.new(far.outputs["AO"], rg.inputs["Green"])
    nt.links.new(rg.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], mo.inputs["Surface"])
    floor.data.materials.clear()
    floor.data.materials.append(om)
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

full_corners = corners(lo, hi)
feeder = bpy.data.objects.get("full feeder assembly <1>")
feeder_objs = [o for o in subtree(feeder) if o.type == "MESH"] if feeder else []
flo, fhi = bbox_of(feeder_objs) if feeder_objs else (lo, hi)
feeder_corners = corners(flo, fhi)
feeder_center = (flo + fhi) / 2

# a slightly lower aim point makes the tall machine sit better in portrait frames
def aim(lo_, hi_, frac=0.5):
    c = (lo_ + hi_) / 2
    c.z = lo_.z + (hi_.z - lo_.z) * frac
    return c

plate_objs = [o for o in meshes if part_name(o).startswith("Top plate")]
plo, phi = bbox_of(plate_objs) if plate_objs else (lo, hi)
feeder_aim = feeder_center.copy()
feeder_aim.z = flo.z + (fhi.z - flo.z) * 0.45
VIEWS = {
    # name: (corner set, center, az, el, focal, margin, resolution, zoom)
    "hero":      (full_corners, aim(lo, hi, 0.5), args.hero_az, 18, 60, 0.05, (2000, 2500), 1.0),
    "hero_b":    (full_corners, aim(lo, hi, 0.5), args.hero_az + 120, 18, 60, 0.05, (2000, 2500), 1.0),
    "front":     (full_corners, aim(lo, hi, 0.5), args.hero_az - 35, 8, 70, 0.05, (2000, 2500), 1.0),
    "low":       (full_corners, aim(lo, hi, 0.45), args.hero_az + 60, -4, 45, 0.04, (2000, 2500), 1.0),
    # zoomed out enough that the floor pool under the machine fits inside the frame
    "topdown":   (full_corners, aim(lo, hi, 0.5), args.hero_az + 20, 55, 60, 0.05, (2500, 2000), 0.9),
    "feeder":    (feeder_corners, feeder_aim, args.hero_az + 10, 32, 85, 0.03, (2500, 2000), 0.72),
    "feeder_b":  (feeder_corners, feeder_aim, args.hero_az - 80, 24, 85, 0.03, (2500, 2000), 0.72),
    # the bin stack on the hero side, close enough to read the piles
    "bins":      (corners(mathutils.Vector((lo.x, lo.y, lo.z + 0.03)), mathutils.Vector((hi.x, hi.y, lo.z + 0.70))),
                  mathutils.Vector((center.x, center.y, lo.z + 0.38)), args.hero_az - 20, 22, 85, 0.02, (2500, 2000), 0.62),
    # the plywood top and the feet of the feeder, close enough to judge the materials
    "plate":     (corners(plo - mathutils.Vector((0, 0, 0.05)), phi + mathutils.Vector((0, 0, 0.35))),
                  (plo + phi) / 2 + mathutils.Vector((0, 0, 0.12)), args.hero_az + 35, 28, 85, 0.03, (2500, 2000), 0.8),
}


def render_to(path):
    """Render the current camera to `path`, written whole: the file only appears once complete,
    so a job that dies mid-frame never leaves a truncated image for a resumed run to skip."""
    import time as _t
    t = _t.time()
    sc = bpy.context.scene
    sc.render.use_file_extension = False
    sc.render.filepath = path + ".part"
    bpy.ops.render.render(write_still=True)
    os.replace(path + ".part", path)
    print(f"RENDER {os.path.basename(path)} {_t.time() - t:.1f}s", flush=True)


if args.stage == "blend":
    bpy.ops.wm.save_as_mainfile(filepath=args.blend or os.path.join(args.out, "sorter.blend"))

elif args.stage == "preview":
    names = [v for v in args.views.split(",") if v] or ["hero", "feeder"]
    for name in names:
        pts, ctr, az, el, focal, margin, res, zoom = VIEWS[name]
        setup_render(args.samples or 48, (int(res[0] * 0.3 * args.scale), int(res[1] * 0.3 * args.scale)))
        fit_camera(cam, pts, az, el, focal, margin, center=ctr, zoom=zoom)
        render_to(os.path.join(args.out, f"preview_{name}.png"))
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.blend)

elif args.stage == "stills":
    names = [v for v in args.views.split(",") if v] or list(VIEWS)
    for name in names:
        path = os.path.join(args.out, f"sorter_{name}.png")
        if os.path.exists(path):          # resumable: delete a still to render it again
            print(f"SKIP {os.path.basename(path)} exists", flush=True)
            continue
        pts, ctr, az, el, focal, margin, res, zoom = VIEWS[name]
        setup_render(args.samples or 512, (int(res[0] * args.scale), int(res[1] * args.scale)))
        fit_camera(cam, pts, az, el, focal, margin, center=ctr, zoom=zoom)
        render_to(path)
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.blend)

elif args.stage == "turntable":
    sc = bpy.context.scene
    setup_render(args.samples or 128, (int(1080 * args.scale), int(1350 * args.scale)))
    # orbit the camera and the studio lights around the machine's own axis: the world light is
    # symmetric about Z so it looks identical to spinning the model, and Cycles only has to
    # update a handful of transforms per frame instead of every LEGO piece
    orbit = bpy.data.objects.new("Orbit", None)
    orbit.location = (center.x, center.y, 0.0)
    sc.collection.objects.link(orbit)
    bpy.context.view_layer.update()
    for name in ("Cam", "Key", "Fill", "Rim", "Top"):
        o = bpy.data.objects[name]
        o.parent = orbit
        o.matrix_parent_inverse = orbit.matrix_world.inverted()
    # the fitted camera must hold every rotated pose; widen using the swept radius
    rad = max((c - center).xy.length for c in full_corners)
    swept_lo = mathutils.Vector((center.x - rad, center.y - rad, lo.z))
    swept_hi = mathutils.Vector((center.x + rad, center.y + rad, hi.z))
    fit_camera(cam, corners(swept_lo, swept_hi), args.hero_az, 16, 60, 0.05, center=aim(lo, hi, 0.5))
    frames_dir = os.path.join(args.out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    n = args.frames
    for f in range(args.frame_start, (args.frame_end or n) + 1):
        path = os.path.join(frames_dir, f"turn_{f:04d}.png")
        if os.path.exists(path):          # resumable: frames only appear once complete
            continue
        # exactly one revolution in n equal steps (frame n + 1 would repeat frame 1). The angle is
        # set directly, no keyframes, so there is no easing: the first web turntable's keys eased
        # in and out, which made it rush through the middle of the turn.
        orbit.rotation_euler = (0.0, 0.0, -2.0 * math.pi * (f - 1) / n)
        render_to(path)
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.blend)

elif args.stage == "clip":
    import json
    import numpy as np
    sc = bpy.context.scene
    meta = json.load(open(os.path.join(args.traj, "meta.json")))
    view = json.load(open(os.path.join(args.traj, "camera.json")))
    log = np.load(os.path.join(args.traj, "traj.npz"))
    # each station's rotor, cap and output gear turn about world Z through the rotor's origin
    pivots = {}
    for k, s in meta["stations"].items():
        p = bpy.data.objects.new(f"Pivot_C{k}", None)
        p.location = s
        sc.collection.objects.link(p)
        pivots[int(k)] = p
    bpy.context.view_layer.update()
    for o in meshes:
        if part_name(o) in ("Rotor - Faceted", "rotor cap", "Output gear (130 teeth)"):
            lo_, hi_ = bbox_of([o])
            c = (lo_ + hi_) / 2
            k = min(pivots, key=lambda k: (pivots[k].location.xy - c.xy).length)
            mw = o.matrix_world.copy()
            o.parent = pivots[k]
            o.matrix_world = mw
    # one object per simulated piece: a mesh per part and colour, as for the piles
    lib = LDraw(args.ldraw)
    coll = bpy.data.collections.new("Pieces")
    sc.collection.children.link(coll)
    variants, pieces = {}, []
    for pc in meta["pieces"]:
        key = (pc["part"], pc["colour"])
        if key not in variants:
            me = lib.mesh(pc["part"]).copy()
            me.name = f"ld_{pc['part']}_c{pc['colour']}"
            if me.materials:
                me.materials[0] = lib.material(pc["colour"])
            variants[key] = me
        ob = bpy.data.objects.new(pc["body"], variants[key])
        coll.objects.link(ob)
        pieces.append(ob)
    print(f"CLIP {len(pieces)} pieces, {len(variants)} part/colour meshes, stations {sorted(pivots)}")
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle_y = math.radians(view["fovy"])
    cam.data.clip_start = 0.01
    cam.location = view["pos"]
    look_at(cam, mathutils.Vector(view["target"]))
    res = (int(1280 * args.scale), int(924 * args.scale))
    if args.look == "cad":
        floor.hide_render = True
        cad_look(res)
    else:
        setup_render(args.samples or 32, res)
        sc.render.image_settings.compression = 15
    frames_dir = os.path.join(args.out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    span = range(view["start_frame"], view["end_frame"] + 1)
    for i, f in enumerate(span[:args.limit] if args.limit else span, 1):
        path = os.path.join(frames_dir, f"clip_{i:04d}.png")
        if os.path.exists(path):          # resumable: frames only appear once complete
            continue
        for k, p in pivots.items():
            p.rotation_euler = (0.0, 0.0, float(log["rotor"][f, k - 1]))
        for j, ob in enumerate(pieces):
            m = mathutils.Quaternion([float(v) for v in log["quat"][f, j]]).to_matrix().to_4x4()   # w x y z
            m.translation = mathutils.Vector([float(v) for v in log["pos"][f, j]])
            ob.matrix_world = m
        render_to(path)

print("DONE", args.stage)
