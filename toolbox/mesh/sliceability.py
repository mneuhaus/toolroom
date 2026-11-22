# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "trimesh", "scipy", "matplotlib"]
# ///
"""sliceability — Druckbarkeits-Report via OrcaSlicer-CLI.

STLs headless mit echten Drucker-Profilen slicen und harte Metriken ziehen:
Druckzeit, Gewicht, Supportvolumen/-anteil, Bridge-Spannweite, Bettauflage.
Der Slicer ist das Orakel — keine eigenen Overhang-Heuristiken.

  uv run tools/sliceability.py out/cff12-v7/*.stl
  uv run tools/sliceability.py --compare teil.stl    # as-is vs flip vs auto
  uv run tools/sliceability.py --map out/maps *.stl  # Overhang-PNG je Teil

Grundregel ("Druckebene zuerst"): pro Teil bewusst die Ebene waehlen,
die aufs Bett kommt — nichts darf darunter herausstehen, sonst schwebt die
Basis und alles braucht Support. Der Bettauflage-Check macht das messbar.

Presets: Name eines User- oder System-Presets; User-Diffs werden ueber die
inherits-Kette der system/-Profile geflattet (Orca-CLI verlangt vollstaendige
JSONs mit "type").
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ORCA = "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
DATA = Path.home() / "Library/Application Support/OrcaSlicer"
KIND_DIRS = {"machine": "machine", "process": "process", "filament": "filament"}
FIL_AREA = math.pi * (1.75 / 2) ** 2  # mm^2


def build_index(kind):
    """name -> Pfad ueber user/ + system/-Baeume (Marken-Unterordner wie
    OrcaFilamentLibrary/filament/<Marke>/ inklusive)."""
    idx = {}
    for base in [DATA / "system", DATA / "user"]:
        for p in base.rglob("*.json"):
            if KIND_DIRS[kind] not in p.parts:
                continue
            try:
                d = json.loads(p.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            idx.setdefault(d.get("name", p.stem), p)
            idx.setdefault(p.stem, p)
    return idx


def flatten(kind, name, overrides=None, compatible_with=None):
    idx = build_index(kind)
    chain = []
    cur = name
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        p = idx.get(cur)
        if p is None:
            if not chain:
                raise SystemExit(f"{kind}-Preset '{cur}' nicht gefunden")
            # verwaiste Vererbung (Preset aus alter Orca-Version): Kette
            # hier kappen, das bereits Gesammelte muss tragen
            print(f"  ! {kind}: Basis '{cur}' fehlt (alte Orca-Version?) — "
                  f"Kette gekappt", file=sys.stderr)
            break
        d = json.loads(p.read_text())
        chain.append(d)
        cur = d.get("inherits")
    merged = {}
    for d in reversed(chain):
        merged.update(d)
    # System-Anker: erstes Kettenglied mit from=system. Die Orca-CLI leitet
    # den Printer-"system_name" bei from=User aus `inherits` ab und prueft
    # compatible_printers des Prozesses GEGEN DIESEN Namen (OrcaSlicer.cpp
    # ~2058/2595).
    sys_anchor = next((d["name"] for d in chain if d.get("from") == "system"),
                      chain[0].get("name", name))
    merged.pop("inherits", None)
    merged["type"] = kind
    merged["name"] = name + " (flat)"
    merged["from"] = "User"
    if kind == "machine":
        merged["inherits"] = sys_anchor
    for gate in ("compatible_printers", "compatible_printers_condition",
                 "compatible_prints", "compatible_prints_condition"):
        merged.pop(gate, None)
    if compatible_with:
        merged["compatible_printers"] = [compatible_with]
    if overrides:
        merged.update(overrides)
    return merged, sys_anchor


def write_json(tmp, data, fname):
    p = Path(tmp) / fname
    p.write_text(json.dumps(data, indent=1))
    return p


def parse_gcode_features(gcode_text):
    """Extrusionsvolumen (mm^3) je FEATURE-Typ + max. Bridge-Spannweite (mm).

    Nur der Typ "Bridge" (Ueber-Luft) zaehlt fuer die Spannweite —
    "Internal Bridge" (ueber Infill) ist druckbar-harmlos."""
    vol = {}
    bridge_len = 0.0
    feature = "?"
    relative_e = False
    last = {"X": 0.0, "Y": 0.0, "E": 0.0}
    for line in gcode_text.splitlines():
        # Bambu-Flavor: "; FEATURE:", Klipper/Marlin-Flavor: ";TYPE:"
        if line.startswith("; FEATURE:") or line.startswith(";TYPE:"):
            feature = line.split(":", 1)[1].strip()
            continue
        if line.startswith("M83"):
            relative_e = True
            continue
        if line.startswith("M82"):
            relative_e = False
            continue
        if line.startswith("G92"):
            m = re.search(r"E([-\d.]+)", line)
            if m:
                last["E"] = float(m.group(1))
            continue
        if not (line.startswith("G1") or line.startswith("G2")
                or line.startswith("G3")):
            continue
        parts = dict(re.findall(r"([XYE])([-\d.]+)", line))
        e = float(parts["E"]) if "E" in parts else None
        x = float(parts.get("X", last["X"]))
        y = float(parts.get("Y", last["Y"]))
        if e is not None:
            de = e if relative_e else e - last["E"]
            if not relative_e:
                last["E"] = e
            if de > 0:
                vol[feature] = vol.get(feature, 0.0) + de * FIL_AREA
                if feature.lower() == "bridge":
                    bridge_len = max(bridge_len,
                                     math.hypot(x - last["X"], y - last["Y"]))
        last["X"], last["Y"] = x, y
    return vol, bridge_len


def read_3mf(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        info = {}
        for n in names:
            if n.endswith("slice_info.config"):
                root = ET.fromstring(z.read(n))
                for md in root.iter("metadata"):
                    info[md.get("key")] = md.get("value")
        gcode = ""
        for n in names:
            if re.search(r"plate_\d+\.gcode$", n):
                gcode = z.read(n).decode(errors="replace")
                break
    return info, gcode


def fmt_time(sec):
    sec = int(float(sec))
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m" if sec >= 3600 \
        else f"{sec // 60}m{sec % 60:02d}s"


def mesh_stats(stl, flip=False):
    """Bettauflage + Overhang-Flaechen aus dem Mesh (orientierungsbewusst).
    Rueckgabe: dict + (mesh, faces_data) fuer die Map-Renderung."""
    import numpy as np
    import trimesh
    from scipy.spatial import ConvexHull
    m = trimesh.load(stl, force="mesh")
    if m.bounds[1].max() < 1.0:
        m.apply_scale(1000.0)
    if flip:
        m.apply_transform(trimesh.transformations.rotation_matrix(
            math.pi, [1, 0, 0]))
    zmin = m.bounds[0][2]
    n = m.face_normals
    ctr = m.triangles_center
    areas = m.area_faces
    down = n[:, 2] < -0.02
    contact = down & (n[:, 2] < -0.999) & (ctr[:, 2] < zmin + 0.05)
    # Overhang-Winkel: 0 deg = flach haengend (kritisch), 90 = senkrechte Wand
    theta = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
    over45 = down & ~contact & (theta < 45)
    hull = ConvexHull(m.vertices[:, :2])
    return {"contact_cm2": areas[contact].sum() / 100.0,
            "hull_cm2": hull.volume / 100.0,  # 2D-Hull: volume == Flaeche
            "contact_pct": 100 * areas[contact].sum() / max(hull.volume, 1e-9),
            "overhang45_cm2": areas[over45].sum() / 100.0,
            }, (m, zmin, n, ctr, theta, contact)


def render_map(stl, out_png, flip=False):
    """Overhang-Map als Unteransicht-PNG: blau = Bettkontakt, gruen->rot =
    Ueberhangwinkel (rot = flach haengend)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import numpy as np
    stats, (m, zmin, n, ctr, theta, contact) = mesh_stats(stl, flip)
    down = n[:, 2] < -0.02
    tris = m.triangles[down][:, :, :2]
    th = theta[down]
    co = contact[down]
    order = np.argsort(ctr[down][:, 2])[::-1]  # tiefste zuletzt = sichtbar
    colors = np.empty((len(th), 4))
    for i, (t, c) in enumerate(zip(th, co)):
        if c:
            colors[i] = (0.25, 0.45, 0.95, 1)
        elif t < 30:
            colors[i] = (0.85, 0.15, 0.1, 1)
        elif t < 45:
            colors[i] = (0.95, 0.55, 0.1, 1)
        elif t < 60:
            colors[i] = (0.95, 0.85, 0.2, 1)
        else:
            colors[i] = (0.35, 0.7, 0.35, 1)
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.add_collection(PolyCollection(tris[order], facecolors=colors[order],
                                     edgecolors="none"))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.invert_xaxis()  # Unteransicht = von unten gespiegelt
    ax.set_title(f"{Path(stl).name}{' (geflippt)' if flip else ''} — "
                 f"Auflage {stats['contact_cm2']:.0f} cm2 "
                 f"({stats['contact_pct']:.0f}%), "
                 f"Overhang<45 {stats['overhang45_cm2']:.0f} cm2\n"
                 "blau=Bett  gruen=steil/ok  gelb=45-60  orange=30-45  "
                 "rot=flach haengend")
    ax.set_xlabel("x (Blick von unten)")
    fig.savefig(out_png, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return stats


def flipped_copy(stl, tmp):
    """Um X gedrehte, auf z0 gelegte Temp-STL. Die Rotation macht trimesh —
    Orcas --rotate-x/--ensure-on-bed-Codepath CRASHT mit manchen Profilen
    (calc_exclude_triangles) und hinterlaesst macOS-Absturzdialoge."""
    import trimesh
    m = trimesh.load(stl, force="mesh")
    if m.bounds[1].max() < 1.0:
        m.apply_scale(1000.0)
    m.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi, [1, 0, 0]))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    p = Path(tmp) / (Path(stl).stem + "-flip.stl")
    m.export(p)
    return p


def analyze(stl, machine, process, filament, support, keep=None,
            flip=False, auto_orient=False):
    tmp = tempfile.mkdtemp(prefix="sliceability-")
    try:
        ov = {"enable_support": "1" if support else "0",
              "support_type": "tree(auto)"}
        mflat, anchor = flatten("machine", machine)
        mp = write_json(tmp, mflat, "machine.json")
        pflat, _ = flatten("process", process, ov, compatible_with=anchor)
        pp = write_json(tmp, pflat, "process.json")
        fflat, _ = flatten("filament", filament, compatible_with=anchor)
        fp = write_json(tmp, fflat, "filament.json")
        out3mf = Path(tmp) / "out.3mf"
        src = flipped_copy(stl, tmp) if flip else Path(stl)
        cmd = [ORCA, "--load-settings", f"{mp};{pp}",
               "--load-filaments", str(fp),
               "--arrange", "1", "--orient", "1" if auto_orient else "0",
               "--slice", "0", "--export-3mf", str(out3mf), str(src)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if not out3mf.exists():
            tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
            sig = f" (Signal {-r.returncode})" if r.returncode < 0 else ""
            raise SystemExit(f"Slice fehlgeschlagen fuer {stl}{sig}:\n  "
                             + "\n  ".join(tail))
        info, gcode = read_3mf(out3mf)
        vol, bridge = parse_gcode_features(gcode)
        if keep:
            shutil.copy(out3mf, keep)
        total = sum(vol.values())
        supp = sum(v for k, v in vol.items() if "support" in k.lower())
        m = re.search(r"total filament weight \[g\] : ([\d.]+)", gcode)
        if m:
            weight = float(m.group(1))
        elif (info.get("weight") or "").strip():
            weight = float(info["weight"])
        else:
            dens = float((fflat.get("filament_density") or ["1.05"])[0])
            weight = total / 1000.0 * dens
        r = {"stl": Path(stl).name, "time": info.get("prediction", "0"),
             "weight": weight, "total_mm3": total, "support_mm3": supp,
             "support_pct": 100 * supp / total if total else 0,
             "bridge_mm": bridge, "features": vol}
        if not auto_orient:
            r.update(mesh_stats(stl, flip)[0])
        return r
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def verdict(r):
    v = []
    if r["support_pct"] < 0.5:
        v.append("supportfrei")
    elif r["support_pct"] < 5:
        v.append(f"wenig Support ({r['support_pct']:.1f}%)")
    else:
        v.append(f"VIEL Support ({r['support_pct']:.1f}%)")
    if r["bridge_mm"] > 40:
        v.append(f"KRITISCHE Bruecke {r['bridge_mm']:.0f} mm Spannweite")
    elif r["bridge_mm"] > 15:
        v.append(f"Bruecke bis {r['bridge_mm']:.0f} mm (ok fuer Voron)")
    if "contact_pct" in r and r["contact_pct"] < 10:
        v.append(f"LIEGT NICHT SATT ({r['contact_pct']:.0f}% Auflage — "
                 "Druckebene pruefen!)")
    return ", ".join(v)


def line(r, label=""):
    base = (f"{fmt_time(r['time'])}  {r['weight']:.0f} g  "
            f"Support {r['support_mm3'] / 1000:.1f} cm3 "
            f"({r['support_pct']:.1f}%)  Bridge max {r['bridge_mm']:.0f} mm")
    if "contact_cm2" in r:
        base += (f"  Auflage {r['contact_cm2']:.0f} cm2 "
                 f"({r['contact_pct']:.0f}%)")
    return f"{label}{base}  -> {verdict(r)}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stls", nargs="+")
    ap.add_argument("--machine", default="trident.local - 0.4mm")
    ap.add_argument("--process", default="0.20mm Bambu A1M Specs")
    ap.add_argument("--filament", default="DevilDesign ASA - Trident")
    ap.add_argument("--no-support", action="store_true",
                    help="Support-Generierung aus (Vergleichslauf)")
    ap.add_argument("--compare", action="store_true",
                    help="Orientierungen vergleichen: as-is / flip-x180")
    ap.add_argument("--auto-orient", action="store_true",
                    help="zusaetzlich Orcas Auto-Orient als Kandidat "
                         "(VORSICHT: CLI-Codepath kann crashen)")
    ap.add_argument("--map", metavar="DIR",
                    help="Overhang-Map-PNG je Teil in DIR schreiben")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true",
                    help="Feature-Aufschluesselung mit ausgeben")
    args = ap.parse_args()

    results = []
    for stl in args.stls:
        stem = Path(stl).stem
        if args.map:
            Path(args.map).mkdir(parents=True, exist_ok=True)
            render_map(stl, f"{args.map}/{stem}.png")
        if args.compare:
            cands = [("as-is     ", {}), ("flip-x180 ", {"flip": True})]
            if args.auto_orient:
                cands.append(("auto-orient", {"auto_orient": True}))
            rows = []
            print(f"{Path(stl).name}:")
            for label, kw in cands:
                r = analyze(stl, args.machine, args.process, args.filament,
                            support=not args.no_support, **kw)
                r["orientation"] = label.strip()
                rows.append(r)
                print("  " + line(r, f"{label} "))
                if args.map and kw.get("flip"):
                    render_map(stl, f"{args.map}/{stem}-flip.png", flip=True)
            best = min(rows, key=lambda r: (round(r["support_mm3"], 1),
                                            float(r["time"])))
            print(f"  => beste Orientierung: {best['orientation']}")
            results.extend(rows)
        else:
            r = analyze(stl, args.machine, args.process, args.filament,
                        support=not args.no_support)
            results.append(r)
            if not args.json:
                print(f"{r['stl']}: " + line(r))
                if args.verbose:
                    for k, v in sorted(r["features"].items(),
                                       key=lambda t: -t[1]):
                        print(f"    {k}: {v / 1000:.2f} cm3")
    if args.json:
        print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
