"""Regenerate English labels from frozen CAD, using the recorded camera and renderer.

This optional provenance workflow reads the original review directory supplied by
--review-dir. It does not modify that project and is not part of the site build.
The CAD runtime must already be importable in the selected Python environment.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', type=Path, required=True)
    parser.add_argument('--font', type=Path, required=True)
    args = parser.parse_args()
    review = args.review_dir.resolve()
    manifest = json.loads((review / 'four-variant-review/source.json').read_text())
    frozen = review / 'snapshots/four-variant-render'
    for name, record in manifest['snapshot_inputs'].items():
        assert digest(frozen / name) == record['sha256'], f'Changed snapshot: {name}'
    load_module('hardware_refs', frozen / 'hardware_refs.py')
    family = load_module('family', frozen / 'family.py')

    # Reuse only the pure projection/rasterisation definitions from the renderer.
    # The original entrypoint refreshes its snapshots, so it must not be invoked.
    source = review / 'render_four_variants.py'
    tree = ast.parse(source.read_text())
    nodes = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in {'basis', 'meshes', 'view_prepared'}
    ) or (
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'COLORS' for t in node.targets)
    )]
    assert len(nodes) == 4
    renderer = {'np': np, 'Image': Image}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), renderer)
    order = ('kiesel', 'komet', 'hochkant', 'grille')
    configs = {name: family.Config(**manifest['configs'][name]) for name in order}
    camera = tuple(manifest['camera'])
    scenes = {name: renderer['meshes'](family.compose(configs[name])[1], camera) for name in order}
    all_xy = np.concatenate([m[3][:, :2] for scene in scenes.values() for m in scene])
    extent = (all_xy.min(axis=0), all_xy.max(axis=0))
    assert np.allclose(extent, manifest['shared_projected_extent'], atol=1e-7, rtol=0)

    font = lambda size: ImageFont.truetype(str(args.font), size)
    gallery = Image.new('RGB', (2200, 1850), (247, 246, 242))
    draw = ImageDraw.Draw(gallery)
    draw.text((55, 40), 'FOUR APPROACHES TO A VIBRATION ROBOT', font=font(44), fill=(31, 52, 59))
    draw.text((55, 101), 'Actual CAD · same camera and scale · front right', font=font(27), fill=(65, 77, 82))
    names = {'kiesel': 'PEBBLE', 'komet': 'COMET', 'hochkant': 'UPRIGHT', 'grille': 'CRICKET'}
    labels = {'kiesel': 'Coin motor flat beneath the PCB', 'komet': 'Coin motor upright ahead of the PCB',
              'hochkant': 'Coin motor upright beneath the PCB', 'grille': 'Miniature cylindrical motor, transverse'}
    for i, name in enumerate(order):
        p = configs[name]
        im = renderer['view_prepared'](scenes[name], camera, extent)
        draw = ImageDraw.Draw(im)
        draw.text((45, 22), names[name], font=font(34), fill=(31, 52, 59))
        draw.text((45, 67), labels[name], font=font(25), fill=(65, 77, 82))
        draw.text((45, 778), f'Body {p.length:g} × {p.body_width:g} × {p.height:g} mm · lid {p.lid_t:g} mm', font=font(25), fill=(65, 77, 82))
        gallery.paste(im, ((i % 2) * 1100, 150 + (i // 2) * 850))

    original = ROOT / 'site/assets/bristlebot-family.png'
    before = np.array(Image.open(original).convert('RGB'))
    after = np.array(gallery)
    assert before.shape == after.shape
    geometry_mask = np.ones(before.shape[:2], dtype=bool)
    geometry_mask[:150] = False
    for top in (150, 1000):
        geometry_mask[top:top+115] = False
        geometry_mask[top+770:top+820] = False
    changed = int(np.any(before != after, axis=2)[geometry_mask].sum())
    assert changed == 0, f'{changed} geometry pixels changed outside label bands'
    target = ROOT / 'site/assets/bristlebot-family-en.png'
    gallery.save(target)
    report = {'status': 'passed', 'method': 'Regenerated from frozen CAD with the original renderer; translated labels only',
              'original_sha256': digest(original), 'output_sha256': digest(target),
              'renderer_sha256': digest(source), 'script_sha256': digest(Path(__file__)),
              'snapshot_inputs_sha256': {k: v['sha256'] for k, v in manifest['snapshot_inputs'].items()},
              'camera': list(camera), 'shared_projected_extent': [a.tolist() for a in extent],
              'changed_pixels_outside_label_bands': changed, 'display_names': names}
    (ROOT / 'validation/bristlebot-english-figure.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'changed_geometry_pixels': changed, 'output': str(target.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
