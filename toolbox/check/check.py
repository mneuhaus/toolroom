"""Hints for a SolidCraft design before printing: thin spots, tiny gaps, overlaps, parts too big for the bed.

It opens the design headless (read-only), measures the printed bodies and lists what looks risky, each with a place
and a number. Nothing here is a rule and nothing blocks: a hint can be fine (looks only, a designed flexure, a
deliberate press fit). Whoever designs the part decides.

What it looks at:
  thin       places with less material than two print lines (the profile's hard wall minimum), measured straight
             through; walls at a planned three-line thickness are not listed
  gap        slots inside a body, and distances between two printed bodies, too narrow to print as a gap
  overlap    a printed body that shares volume with another body
  bed        a printed body that does not fit the printer
  mesh       a body that is not closed, or whose mesh export has open edges or fails
  print face a printed body without a print face (only a reminder)

Usage: toolbox/check/check design.sc [--printed "Base,Lid"] [--json hints.json]
  Without --printed every body counts as printed except those named like a reference ("Ref ...", "... (Referenz)").
  A file check.json next to the design may hold {"printed": [...], "reference": [...]} instead.
The numbers come from profiles/manufacturing/fdm-bambu-a1-0.4.yaml (walls, clearances, build volume).
"""
import argparse
import fnmatch
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh
import yaml

TOOLROOM = Path(__file__).resolve().parents[2]
CLI = "/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli"
PROFILE = TOOLROOM / "profiles/manufacturing/fdm-bambu-a1-0.4.yaml"
REFERENCE_NAMES = ("Ref *", "*(Referenz)*", "*(Reference)*", "*(ref)*")
SAMPLES_PER_MM2 = 2.0
CELL = 3.0                # mm: neighbouring samples within this distance count as one place
MAX_PLACES = 5


def solidcraft(design, commands, work, label):
    """Runs the commands on the design; returns (results, None) or (None, error line)."""
    script, out = work / f"{label}.json", work / f"{label}.results.json"
    script.write_text(json.dumps({"commands": commands}))
    run = subprocess.run([CLI, "run", str(script), "--in", str(design), "--results", "--json-out", str(out)],
                         capture_output=True, text=True, cwd=work)
    if run.returncode != 0:
        return None, (run.stderr.strip().splitlines() or ["no output"])[-1][:240]
    return json.loads(out.read_text()), None


def places(points, values):
    """Groups nearby samples into places: (smallest value, its point, sample count, median), thinnest first."""
    cells = {}
    for i, cell in enumerate(map(tuple, np.floor(points / CELL).astype(int))):
        cells.setdefault(cell, []).append(i)
    found, seen = [], set()
    for start in cells:
        if start in seen:
            continue
        seen.add(start)
        stack, members = [start], []
        while stack:
            cell = stack.pop()
            members += cells[cell]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        other = (cell[0] + dx, cell[1] + dy, cell[2] + dz)
                        if other in cells and other not in seen:
                            seen.add(other)
                            stack.append(other)
        if len(members) >= 3:
            worst = min(members, key=lambda i: values[i])
            found.append((float(values[worst]), points[worst], len(members), float(np.median(values[members]))))
    return sorted(found, key=lambda place: place[0])


def through(mesh, points, normals, inward, limit):
    """Distance from each surface sample to the next surface of the same body, straight into the material (inward)
    or straight out of it. Only roughly opposite faces count, so a corner is not mistaken for a wall or a slot."""
    direction = -normals if inward else normals
    origins = points + direction * 1e-3
    hits, ray, tri = mesh.ray.intersects_location(origins, direction, multiple_hits=False)
    distance = np.full(len(points), np.inf)
    if not len(ray):
        return distance
    reached =np.linalg.norm(hits - origins[ray], axis=1)
    facing = np.einsum("ij,ij->i", mesh.face_normals[tri], normals[ray]) < -0.5
    keep = facing & (reached < limit) & (reached > 0.02)
    distance[ray[keep]] = reached[keep]
    return distance


def check(design, printed_arg, work):
    profile = yaml.safe_load(PROFILE.read_text())
    thin_limit = profile["walls"]["hard_min"]
    gap_limit, tight, volume = profile["clearances"]["print_in_place"], profile["clearances"]["tight"], profile["build_volume"]
    hints, notes = [], []

    def hint(kind, body, text, where=None):
        hints.append({"kind": kind, "body": body, "text": text,
                      "where": None if where is None else [round(float(c), 1) for c in where]})

    first, error = solidcraft(design, [{"command": "inspect.measure", "params": {}}], work, "bodies")
    if error:
        sys.exit(f"SolidCraft could not open the design: {error}")
    bodies = {b["name"]: b for b in first[0]["bodies"]}
    project = design.parent / "check.json"
    listed = json.loads(project.read_text()) if project.exists() else {}
    reference_patterns = listed.get("reference", REFERENCE_NAMES)
    wanted = printed_arg or listed.get("printed")
    if wanted:
        printed = [n for n in bodies if any(fnmatch.fnmatchcase(n, p) for p in wanted)]
        notes.append(f"printed bodies: {', '.join(printed)}")
    else:
        printed = [n for n in bodies if not any(fnmatch.fnmatchcase(n, p) for p in reference_patterns)]
        notes.append(f"printed bodies (guessed from the names, pass --printed to say which): {', '.join(printed)}")
    others = [n for n in bodies if n not in printed]
    if others:
        notes.append(f"not printed, only looked at for overlaps: {', '.join(others)}")

    # overlaps between all bodies, distances between the printed ones
    commands = [{"command": "inspect.interference", "params": {"budget_s": 240}}]
    if len(printed) > 1:
        commands.append({"command": "inspect.clearance", "params": {"bodies": printed, "clearance": gap_limit}})
    measured, error = solidcraft(design, commands, work, "pairs")
    if error:
        notes.append(f"overlaps and distances between bodies could not be measured: {error}")
    else:
        for hit in measured[0].get("interferences", []):
            if hit["a"] not in printed and hit["b"] not in printed:
                continue                  # two reference parts modelled into each other: not our part's problem
            hint("overlap", f"{hit['a']} / {hit['b']}", f"share {hit['volume_mm3']:.2f} mm3", hit.get("center"))
        skipped = measured[0].get("unchecked", [])
        if skipped:
            notes.append(f"{len(skipped)} body pairs were not looked at for overlaps (mesh bodies, or the time ran out)")
        for near in (measured[1].get("near", []) if len(measured) > 1 else []):
            if near["distance_mm"] > 1e-4:
                how = "will probably fuse or jam" if near["distance_mm"] < tight else "tight"
                hint("gap", f"{near['a']} / {near['b']}", f"{near['distance_mm']:.2f} mm apart ({how}; a printable gap is "
                     f"about {gap_limit} mm, a tight fit {tight})", near.get("from"))

    # mesh exports: all bodies in one run; if that fails, one run per body so one bad body does not hide the others
    def exports_for(number, body):
        return [{"command": "file.export", "params": {"path": str(work / f"body{number}.stl"), "bodies": [body], "quality": "fine"}},
                {"command": "file.export", "params": {"path": str(work / f"body{number}.laid.stl"), "bodies": [body],
                                                      "quality": "fine", "lay_on_print_faces": True}}]

    solids = [(number, body) for number, body in enumerate(printed) if bodies[body].get("closed")]
    export_replies, failed_exports = {}, {}
    result, error = solidcraft(design, [c for number, body in solids for c in exports_for(number, body)], work, "exports")
    if not error:
        export_replies = {body: result[2 * i + 1] for i, (_, body) in enumerate(solids)}
    else:
        for number, body in solids:
            result, error = solidcraft(design, exports_for(number, body), work, f"export{number}")
            if error:
                failed_exports[body] = error
            else:
                export_replies[body] = result[1]

    no_face = []
    for number, body in enumerate(printed):
        if not bodies[body].get("closed"):
            hint("mesh", body, "is not a closed solid")
            continue
        as_built, laid = work / f"body{number}.stl", work / f"body{number}.laid.stl"
        if body in failed_exports:
            hint("mesh", body, f"SolidCraft could not export it as a mesh: {failed_exports[body]}")
            continue
        laid_reply = export_replies[body]
        mesh = trimesh.load(as_built)
        if not mesh.is_watertight:
            hint("mesh", body, "the mesh export has open edges")
        has_face = body in (laid_reply.get("print_faces") or [])
        size = trimesh.load(laid).extents
        if has_face:
            fits = size[2] <= volume[2] and max(size[:2]) <= max(volume[:2]) and min(size[:2]) <= min(volume[:2])
        else:
            no_face.append(body)
            fits = all(a <= b for a, b in zip(sorted(size), sorted(volume)))
        if not fits:
            hint("bed", body, f"is {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm" + (" laid on its print face" if has_face else "")
                 + f", the printer takes {volume[0]} x {volume[1]} x {volume[2]}")

        count = int(np.clip(mesh.area * SAMPLES_PER_MM2, 4000, 120000))
        points, faces = trimesh.sample.sample_surface(mesh, count, seed=1)
        normals = mesh.face_normals[faces]
        per_sample = mesh.area / count
        thickness = through(mesh, points, normals, True, 0.95 * thin_limit)     # not what is only just under the limit
        thin = np.isfinite(thickness)
        found = places(points[thin], thickness[thin])
        for value, where, samples, typical in found[:MAX_PLACES]:
            hint("thin", body, f"{value:.2f} mm of material at the thinnest point, around {typical:.2f} over about "
                 f"{samples * per_sample:.0f} mm2 (two print lines are {thin_limit} mm)", where)
        if len(found) > MAX_PLACES:
            notes.append(f"{body}: {len(found) - MAX_PLACES} more thin places not listed")
        slot = through(mesh, points, normals, False, gap_limit)
        narrow = np.isfinite(slot)
        found = places(points[narrow], slot[narrow])
        for value, where, samples, typical in found[:MAX_PLACES]:
            hint("gap", body, f"a slot only {value:.2f} mm wide inside the body (below about {gap_limit} mm it tends to close up)", where)
    if no_face:
        hint("print face", ", ".join(no_face), "no print face set (body.print_face), so the print orientation is not in the design")
    return notes, hints


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("design")
    parser.add_argument("--printed", help="comma-separated body names or patterns")
    parser.add_argument("--json")
    args = parser.parse_args()
    design = Path(args.design).resolve()
    with tempfile.TemporaryDirectory(prefix="toolroom-check.") as temp:
        notes, hints = check(design, args.printed.split(",") if args.printed else None, Path(temp))
    print(f"Hints for {design}")
    for note in notes:
        print(f"  {note}")
    print()
    for kind in ("mesh", "overlap", "gap", "thin", "bed", "print face"):
        for h in [h for h in hints if h["kind"] == kind]:
            print(f"  {kind:<10} {h['body']}: {h['text']}" + (f", at {h['where']}" if h["where"] else ""))
    print(f"\n{len(hints)} hints. They are places to look at, not errors: decide for each whether it matters." if hints
          else "nothing to point at.")
    if args.json:
        Path(args.json).write_text(json.dumps({"design": str(design), "notes": notes, "hints": hints}, indent=1))


if __name__ == "__main__":
    main()
