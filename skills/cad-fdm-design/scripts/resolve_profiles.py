"""Resolve local slicer profile data without launching a slicer or machine.

Order: inherited values, includes in declared order, own values, explicit overrides.
Identity metadata belongs to the requested profile. This data helper does not
replace a slicer's compatibility rules or construct machine start/end routines.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class ProfileError(ValueError):
    pass


IDENTITY = {"name", "type", "from", "setting_id", "inherits", "include"}


def read_profile(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Cannot read profile {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"Profile {path.name} must contain an object")
    return data


def build_index(roots: list[Path]) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for root in roots:
        if not root.is_dir():
            raise ProfileError(f"Profile root does not exist: {root}")
        for path in sorted(root.rglob("*.json")):
            data = read_profile(path)
            names = {path.stem, data.get("name", path.stem)}
            for name in names:
                if not isinstance(name, str):
                    raise ProfileError(f"Invalid profile name in {path.name}")
                values = index.setdefault(name, [])
                if path.resolve() not in values:
                    values.append(path.resolve())
    return index


def locate(name: str, index: dict[str, list[Path]], parent: Path | None) -> Path:
    if not isinstance(name, str) or not name:
        raise ProfileError("Profile references must be nonempty strings")
    # A path reference is relative to the declaring file; names use the index.
    if parent is not None and ("/" in name or name.endswith(".json")):
        candidate = (parent.parent / name).resolve()
        if candidate.is_file():
            return candidate
    matches = index.get(name, [])
    if not matches:
        raise ProfileError(f"Missing profile reference: {name}")
    if len(matches) != 1:
        raise ProfileError(f"Ambiguous profile reference: {name} ({len(matches)} matches)")
    return matches[0]


def resolve(path: Path, index: dict[str, list[Path]], overrides: dict | None = None) -> dict:
    chain: list[str] = []

    def visit(current: Path, stack: tuple[Path, ...]) -> dict:
        current = current.resolve()
        if current in stack:
            names = " -> ".join(p.name for p in (*stack, current))
            raise ProfileError(f"Profile dependency cycle: {names}")
        data = read_profile(current)
        values: dict = {}
        if data.get("inherits"):
            values.update(visit(locate(data["inherits"], index, current), (*stack, current)))
        includes = data.get("include", [])
        if not isinstance(includes, list) or any(not isinstance(x, str) for x in includes):
            raise ProfileError(f"include must be an ordered list of names in {current.name}")
        for ref in includes:
            values.update(visit(locate(ref, index, current), (*stack, current)))
        values.update({k: v for k, v in data.items() if k not in IDENTITY})
        chain.append(data.get("name", current.stem))
        return values

    original = read_profile(path)
    values = visit(path, ())
    overrides = overrides or {}
    if not isinstance(overrides, dict):
        raise ProfileError("Overrides must be an object")
    if IDENTITY.intersection(overrides):
        raise ProfileError("Overrides may not silently change profile identity or dependency metadata")
    values.update(overrides)
    return {
        "profile": {k: original[k] for k in ("name", "type", "from", "setting_id") if k in original},
        "values": values,
        "resolution_order": chain,
        "overrides": overrides,
        "scope": "Resolved profile data only; validate identity, compatibility and machine routines in the actual slicer.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--root", action="append", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        overrides = read_profile(args.overrides) if args.overrides else None
        result = resolve(args.profile, build_index(args.root), overrides)
        encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(encoded)
        else:
            print(encoded, end="")
        return 0
    except ProfileError as exc:
        parser.exit(2, f"Profile resolution failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
