"""Resolve installed Bambu Studio presets, including machine G-code includes.

Independent of Orca settings. No GUI state, user presets, or installed files are
modified. Missing parents/includes fail rather than silently shortening a chain.
"""
from pathlib import Path
import hashlib
import json
import zipfile

DATA = Path.home() / 'Library/Application Support/BambuStudio'
EXECUTABLE = '/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'


def _index(kind):
    result = {}
    for base in [DATA / 'system', DATA / 'user']:
        for path in sorted(base.rglob('*.json')):
            if kind not in path.parts:
                continue
            try:
                row = json.loads(path.read_text())
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            result.setdefault(row.get('name', path.stem), path)
            result.setdefault(path.stem, path)
    return result


def flatten(kind, name, overrides=None, compatible_with=None):
    index = _index(kind)
    sources = {}

    def resolve(preset, active=()):
        if preset in active:
            raise ValueError(('cyclic preset inheritance/include', preset, active))
        path = index[preset]
        data = json.loads(path.read_text())
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        merged = resolve(data['inherits'], (*active, preset)) if data.get('inherits') else {}
        for included in data.get('include', []):
            merged.update(resolve(included, (*active, preset)))
        merged.update(data)
        return merged

    merged = resolve(name)
    anchor = name
    current = name
    while current:
        row = json.loads(index[current].read_text())
        if row.get('from') == 'system':
            anchor = row.get('name', current)
            break
        current = row.get('inherits')
    for key in ['inherits', 'include', 'compatible_printers',
                'compatible_printers_condition', 'compatible_prints',
                'compatible_prints_condition']:
        merged.pop(key, None)
    merged.update(type=kind, name=name + ' (native flat)', **{'from': 'User'})
    if kind == 'machine':
        merged['inherits'] = anchor
    if compatible_with:
        merged['compatible_printers'] = [compatible_with]
    merged.update(overrides or {})
    return merged, anchor, sources


def write_profile(directory, kind, profile):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (kind + '.json')
    path.write_text(json.dumps(profile, indent=2) + '\n')
    return path


def audit_project(path, machine):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        config = json.loads(archive.read('Metadata/project_settings.config'))
        assert any(n.endswith('.gcode') for n in archive.namelist())
    checked = {}
    for key in ['machine_start_gcode', 'machine_end_gcode', 'layer_change_gcode',
                'time_lapse_gcode', 'change_filament_gcode']:
        assert machine.get(key), ('unresolved native machine routine', key)
        assert config[key] == machine[key], ('machine routine differs', key)
        checked[key] = hashlib.sha256(config[key].encode()).hexdigest()
    # Bambu fields that cannot inherit Orca's relative-width strings.
    widths = {}
    for key in ['skin_infill_line_width', 'skeleton_infill_line_width']:
        value = float(config[key])
        assert 0 < value < 1.0, (key, config[key])
        widths[key] = value
    return {'nativeMachineRoutinesSha256': checked, 'absoluteLineWidthsMm': widths,
            'printerModel': config['printer_model'],
            'projectSha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
