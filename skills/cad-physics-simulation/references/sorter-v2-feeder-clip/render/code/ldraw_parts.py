"""Minimal LDraw part loader for Blender: one .dat -> one mesh, LDraw colours -> materials.

Used inside Blender (bpy). Parses the part file recursively (subfile lines, tris,
quads), applies the LDraw transforms, converts LDU (0.4 mm, Y down) to metres
Z up, recalculates normals, and shades smooth by angle. Colour code 16 inherits
the instance colour; anything else is baked as its own material slot.

    from ldraw_parts import LDraw
    lib = LDraw("/Users/spencer/Documents/ldraw")
    mesh = lib.mesh("3001")          # shared mesh, colour-16 faces in slot 0
    mat = lib.material(4)            # LDraw colour 4 = red, ABS look
"""

import math
import os
import re

import bpy
import mathutils

LDU = 0.0004  # metres per LDraw unit
LD_TO_BL = mathutils.Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))  # Y-down -> Z-up


class LDraw:
    def __init__(self, root):
        self.root = root
        self.dirs = [os.path.join(root, d) for d in ("parts", "p", "parts/s", "p/48", "p/8")]
        self._index = None
        self._meshes = {}
        self._mats = {}
        self.colours = self._load_colours(os.path.join(root, "LDConfig.ldr"))

    # ---------------------------------------------------------------- files
    def _find(self, name):
        name = name.replace("\\", "/").lower()
        if self._index is None:
            self._index = {}
            for d in self.dirs:
                if not os.path.isdir(d):
                    continue
                rel = os.path.relpath(d, self.root).replace("parts/", "").replace("p/", "")
                for f in os.listdir(d):
                    if f.lower().endswith(".dat"):
                        key = f.lower() if rel in ("parts", "p") else f"{os.path.basename(d)}/{f.lower()}"
                        self._index.setdefault(key, os.path.join(d, f))
                        self._index.setdefault(f.lower(), os.path.join(d, f))
        return self._index.get(name) or self._index.get(os.path.basename(name))

    def title(self, part):
        """Description line, following '~Moved to' aliases."""
        for _ in range(5):
            path = self._find(part + ".dat")
            if not path:
                return None
            with open(path, encoding="utf-8", errors="replace") as fh:
                first = fh.readline().strip()
            t = first[2:].strip() if first.startswith("0") else first
            m = re.match(r"~Moved to (\S+)", t)
            if not m:
                return t
            part = m.group(1)
        return t

    @staticmethod
    def _load_colours(path):
        cols = {}
        rx = re.compile(r"!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})\s+EDGE\s+#?([0-9A-Fa-f]{6}|\d+)(.*)")
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = rx.search(line)
                if not m:
                    continue
                name, code, val, _edge, rest = m.groups()
                rgb = tuple(int(val[i:i + 2], 16) / 255 for i in (0, 2, 4))
                alpha = 1.0
                am = re.search(r"ALPHA\s+(\d+)", rest)
                if am:
                    alpha = int(am.group(1)) / 255
                finish = "abs"
                for key in ("CHROME", "PEARLESCENT", "METAL", "RUBBER", "MATTE_METALLIC"):
                    if key in rest:
                        finish = key.lower()
                cols[int(code)] = {"name": name, "rgb": rgb, "alpha": alpha, "finish": finish}
        return cols

    # ------------------------------------------------------------- geometry
    def _parse(self, path, matrix, colour, tris, depth=0):
        if depth > 12:
            return
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if not parts:
                    continue
                t = parts[0]
                if t == "1" and len(parts) >= 15:
                    c = int(parts[1])
                    c = colour if c == 16 else c
                    x, y, z = (float(v) for v in parts[2:5])
                    a, b, cc, d, e, f, g, h, i = (float(v) for v in parts[5:14])
                    sub = mathutils.Matrix(((a, b, cc, x), (d, e, f, y), (g, h, i, z), (0, 0, 0, 1)))
                    subpath = self._find(" ".join(parts[14:]))
                    if subpath:
                        self._parse(subpath, matrix @ sub, c, tris, depth + 1)
                elif t in ("3", "4") and len(parts) >= (11 if t == "3" else 14):
                    c = int(parts[1])
                    c = colour if c in (16, 24) else c
                    n = 3 if t == "3" else 4
                    pts = [matrix @ mathutils.Vector((float(parts[2 + 3 * k]), float(parts[3 + 3 * k]), float(parts[4 + 3 * k]))) for k in range(n)]
                    if n == 3:
                        tris.append((c, pts))
                    else:
                        tris.append((c, [pts[0], pts[1], pts[2]]))
                        tris.append((c, [pts[0], pts[2], pts[3]]))

    def mesh(self, part):
        """Blender mesh for an LDraw part number (e.g. '3001'). Faces in colour 16 land in
        material slot 0 (left empty, assign per instance); fixed colours get their own slots."""
        if part in self._meshes:
            return self._meshes[part]
        path = self._find(part + ".dat")
        if not path:
            raise FileNotFoundError(part)
        tris = []
        self._parse(path, mathutils.Matrix.Identity(4), 16, tris)
        verts, faces, slots, slot_of = [], [], [16], {16: 0}
        for c, pts in tris:
            if c not in slot_of:
                slot_of[c] = len(slots)
                slots.append(c)
            base = len(verts)
            verts.extend((LD_TO_BL @ p) * LDU for p in pts)
            faces.append(((base, base + 1, base + 2), slot_of[c]))
        me = bpy.data.meshes.new(f"ld_{part}")
        me.from_pydata([tuple(v) for v in verts], [], [f for f, _ in faces])
        me.validate(clean_customdata=False)
        for i, (_, s) in enumerate(faces):
            if i < len(me.polygons):
                me.polygons[i].material_index = s
        me.materials.append(None)
        for c in slots[1:]:
            me.materials.append(self.material(c))
        # merge duplicate verts, fix winding, smooth the round bits
        ob = bpy.data.objects.new("_ldtmp", me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.ops.object.select_all(action="DESELECT")     # the ops below act on the whole selection
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=LDU * 0.5)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35.0))
        bpy.data.objects.remove(ob, do_unlink=True)
        self._meshes[part] = me
        return me

    # ------------------------------------------------------------- materials
    def material(self, code):
        if code in self._mats:
            return self._mats[code]
        c = self.colours.get(code) or {"name": f"c{code}", "rgb": (0.5, 0.5, 0.5), "alpha": 1.0, "finish": "abs"}
        m = bpy.data.materials.new(f"lego_{code}_{c['name']}")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        rgb = tuple(ch ** 2.2 for ch in c["rgb"])  # LDConfig values are sRGB
        b.inputs["Base Color"].default_value = (*rgb, 1.0)
        b.inputs["Roughness"].default_value = 0.32
        b.inputs["Specular IOR Level"].default_value = 0.5
        b.inputs["Coat Weight"].default_value = 0.15
        b.inputs["Coat Roughness"].default_value = 0.12
        f = c["finish"]
        if f == "chrome":
            b.inputs["Metallic"].default_value = 1.0
            b.inputs["Roughness"].default_value = 0.08
        elif f in ("metal", "matte_metallic"):
            b.inputs["Metallic"].default_value = 0.9
            b.inputs["Roughness"].default_value = 0.35
        elif f == "pearlescent":
            b.inputs["Metallic"].default_value = 0.35
            b.inputs["Roughness"].default_value = 0.25
        elif f == "rubber":
            b.inputs["Roughness"].default_value = 0.8
            b.inputs["Coat Weight"].default_value = 0.0
        if c["alpha"] < 1.0:
            b.inputs["Transmission Weight"].default_value = 1.0
            b.inputs["Roughness"].default_value = 0.08
            b.inputs["IOR"].default_value = 1.54
            b.inputs["Coat Weight"].default_value = 0.0
        self._mats[code] = m
        return m
