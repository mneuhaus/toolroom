import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__
from .syntax import FSError, parse


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate a FeatureScript subset with local OpenCascade"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Parse syntax only; does not establish API compatibility")
    check.add_argument("source", type=Path)
    snapshot = sub.add_parser("snapshot", help="Freeze named Part Studio STEP solids for imports")
    snapshot.add_argument("source", type=Path)
    snapshot.add_argument("--output", type=Path, required=True, help="New JSON manifest path")
    batch = sub.add_parser("batch", help="Evaluate a frozen compatibility corpus")
    batch.add_argument("manifest", type=Path)
    batch.add_argument("--output", type=Path, required=True)
    batch.add_argument("--timeout", type=float, default=120)
    batch.add_argument("--case", action="append", default=[])
    build = sub.add_parser("run", help="Execute an exported feature and optionally export solids")
    build.add_argument("source", type=Path)
    build.add_argument("--feature")
    build.add_argument("--param", action="append", default=[], metavar="NAME=EXPRESSION")
    build.add_argument(
        "--imports", type=Path, help="JSON path[@version] to local .fs or snapshot mapping"
    )
    build.add_argument("--step", type=Path)
    build.add_argument("--stl", type=Path)
    build.add_argument("--fonts", type=Path, help="JSON font-name to exact local font-file mapping")
    build.add_argument("--report", type=Path)
    build.add_argument("--max-steps", type=int, default=1_000_000)
    build.add_argument("--max-depth", type=int, default=128)
    build.add_argument("--verbose", action="store_true", help="Show kernel operation progress")
    build.add_argument(
        "--mesh-tolerance", type=float, default=0.05, help="STL linear deflection in mm"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "batch":
            from .corpus import run_corpus

            result = run_corpus(args.manifest, args.output, args.timeout, args.case)
            print(
                f"{result['passed']}/{result['total']} cases passed; {result['recovered']} with caught operation failures"
            )
            return 0 if result["passed"] == result["total"] else 1
        if args.command == "snapshot":
            from .partstudio import create_snapshot

            result = create_snapshot(args.source, args.output)
            print(f"Frozen {len(result['parts'])} named solid(s): {args.output}")
            return 0
        if args.command == "check":
            nodes = parse(args.source.read_text(), str(args.source))
            print(
                f"Parsed {len(nodes)} top-level constructs. Geometry/API compatibility not checked."
            )
            return 0
        from .api import run

        params = {}
        for item in args.param:
            name, sep, expr = item.partition("=")
            if not sep or not name.isidentifier():
                raise FSError("--param must be NAME=EXPRESSION")
            params[name] = expr
        imports = {}
        fonts = {}
        if args.fonts:
            mapping = json.loads(args.fonts.read_text())
            if not isinstance(mapping, dict) or not all(
                isinstance(v, str) for v in mapping.values()
            ):
                raise FSError("--fonts must contain a JSON object of string paths")
            fonts = {k: str((args.fonts.parent / v).resolve()) for k, v in mapping.items()}
        if args.imports:
            mapping = json.loads(args.imports.read_text())
            if not isinstance(mapping, dict) or not all(
                isinstance(v, str) for v in mapping.values()
            ):
                raise FSError("--imports must contain a JSON object of string paths")
            imports = {k: str((args.imports.parent / v).resolve()) for k, v in mapping.items()}
        if args.max_steps < 1 or not 1 <= args.max_depth <= 128:
            raise FSError("Use positive --max-steps and --max-depth from 1 to 128")
        result = run(
            args.source,
            feature=args.feature,
            parameters=params,
            imports=imports,
            fonts=fonts,
            max_steps=args.max_steps,
            max_depth=args.max_depth,
            progress=(
                lambda event: print(
                    f"{event['operation']}: {'/'.join(event['id'])}", file=sys.stderr, flush=True
                )
            )
            if args.verbose
            else None,
        )
        report = result.report()
        # Stage every requested artifact before replacing any destination.
        destinations = [p.resolve() for p in (args.step, args.stl, args.report) if p]
        protected = {Path(source["path"]).resolve() for source in report["sources"]}
        if args.imports:
            protected.add(args.imports.resolve())
        if args.fonts:
            protected.add(args.fonts.resolve())
        if len(destinations) != len(set(destinations)) or protected.intersection(destinations):
            raise FSError("Artifact paths must be distinct and must not overwrite source")
        with tempfile.TemporaryDirectory(prefix="fsocct-") as folder:
            staged = []
            for kind in ("step", "stl", "report"):
                destination = getattr(args, kind)
                if destination:
                    temp = Path(folder) / kind
                    if kind == "step":
                        report.setdefault("exports", {})["step"] = result.step(temp)
                    elif kind == "stl":
                        result.stl(temp, args.mesh_tolerance)
                    else:
                        temp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
                    staged.append((temp, destination))
            for temp, destination in staged:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as f:
                    local = Path(f.name)
                    f.write(temp.read_bytes())
                local.replace(destination)
        print(
            f"{report['body_count']} solid(s), {report['volume_mm3']:.6f} mm³; "
            f"{len(report['operations'])} operations in {result.elapsed_seconds:.3f}s"
        )
        for warning in report["warnings"]:
            print("Note: " + warning, file=sys.stderr)
        if report["failed_operations"]:
            print(
                f"Note: FeatureScript caught {len(report['failed_operations'])} failed geometry operation(s); inspect failed_operations in the report",
                file=sys.stderr,
            )
        for line in report["console"]:
            print(line)
        if args.report:
            print(f"Report: {args.report}")
        return 0
    except (FSError, OSError, ValueError) as e:
        print(f"fsocct: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
