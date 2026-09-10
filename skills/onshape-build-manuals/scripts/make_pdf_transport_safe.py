#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pypdf>=6.18,<7"]
# ///
"""Losslessly prepare a generated manual PDF for a UTF-8-only upload bridge.

Use a distinct output path. This helper is for generated assembly manuals, not
signed originals. Binary-safe transports do not require this transformation.
"""

import argparse
import base64
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import tempfile

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, NullObject, StreamObject


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decoded_streams(writer):
    # The bound pypdf major version exposes streams through this object table.
    # Compare decoded bytes, including embedded fonts and image data, not just
    # extracted text or a page count.
    return Counter(
        sha256(obj.get_data())
        for obj in writer._objects
        if isinstance(obj, StreamObject)
    )


def document_snapshot(reader):
    pages = []
    for page in reader.pages:
        annotations = []
        for ref in page.get('/Annots', []):
            annotation = ref.get_object()
            action = annotation.get('/A', {})
            action = action.get_object() if hasattr(action, 'get_object') else action
            annotations.append({
                'subtype': str(annotation.get('/Subtype', '')),
                'rect': [float(v) for v in annotation.get('/Rect', [])],
                'action': str(action.get('/S', '')),
                'uri': str(action.get('/URI', '')),
            })
        resources = page.get('/Resources', {})
        resources = resources.get_object() if hasattr(resources, 'get_object') else resources
        ext = resources.get('/ExtGState', {})
        ext = ext.get_object() if hasattr(ext, 'get_object') else ext
        graphics_states = {
            str(name): {str(k): str(v) for k, v in state.get_object().items()}
            for name, state in ext.items()
        }
        contents = page.get_contents()
        pages.append({
            'mediaBox': [float(v) for v in page.mediabox],
            'cropBox': [float(v) for v in page.cropbox],
            'rotation': page.rotation,
            'contents': sha256(contents.get_data()) if contents else None,
            'text': page.extract_text(),
            'annotations': annotations,
            'graphicsStates': graphics_states,
        })

    def outlines(items):
        return [
            outlines(item) if isinstance(item, list) else {
                'title': item.title,
                'page': reader.get_destination_page_number(item),
                'fit': str(item.get('/Type', '')),
            }
            for item in items
        ]

    return {
        'pages': pages,
        'outlines': outlines(reader.outline),
        'title': str((reader.metadata or {}).get('/Title', '')),
        'author': str((reader.metadata or {}).get('/Author', '')),
    }


def prepare(source, destination, report_path=None):
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    require(source != destination, 'Use a distinct output path to preserve the generated source PDF.')
    original = source.read_bytes()
    reader = PdfReader(io.BytesIO(original), strict=True)
    require(not reader.is_encrypted, 'Provide the unencrypted generated manual PDF.')
    before = document_snapshot(reader)
    writer = PdfWriter(clone_from=reader)
    original_streams = decoded_streams(writer)
    wrapped = 0

    for obj in writer._objects:
        if not isinstance(obj, StreamObject) or obj._data.isascii():
            continue
        filters = obj.get('/Filter')
        filters = list(filters) if isinstance(filters, ArrayObject) else ([filters] if filters else [])
        params = obj.get('/DecodeParms')
        if params is not None:
            params = list(params) if isinstance(params, ArrayObject) else [params]
            obj[NameObject('/DecodeParms')] = ArrayObject([NullObject()] + params)
        obj._data = base64.a85encode(obj._data) + b'~>'
        obj[NameObject('/Filter')] = ArrayObject([NameObject('/ASCII85Decode')] + filters)
        wrapped += 1

    buffer = io.BytesIO()
    writer.write(buffer)
    # Replace only the binary header comment, using exactly the same byte length
    # so all cross-reference offsets remain correct.
    binary_comment, ascii_comment = b'%\xe2\xe3\xcf\xd3\n', b'%PDF!\n'
    raw = buffer.getvalue()
    header_end = raw.index(b'\n') + 1
    require(len(binary_comment) == len(ascii_comment), 'Header replacement length mismatch.')
    require(raw[header_end:header_end + len(binary_comment)] == binary_comment,
            'Unexpected pypdf header: inspect the writer before changing bytes.')
    raw = raw[:header_end] + ascii_comment + raw[header_end + len(binary_comment):]
    require(raw.isascii(), 'Non-stream binary content remains; do not upload through a UTF-8-only bridge.')

    check = PdfReader(io.BytesIO(raw), strict=True)
    require(document_snapshot(check) == before,
            'PDF page content, text, graphics states, links or outlines changed.')
    require(decoded_streams(PdfWriter(clone_from=check)) == original_streams,
            'Decoded PDF streams changed; preserve the source and inspect the filters.')

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.pdf', delete=False) as tmp:
        tmp.write(raw)
        temporary = Path(tmp.name)
    temporary.replace(destination)
    report = {
        'source': str(source), 'output': str(destination),
        'inputBytes': len(original), 'outputBytes': len(raw),
        'inputSha256': sha256(original), 'outputSha256': sha256(raw),
        'pages': len(check.pages), 'wrappedStreams': wrapped,
        'asciiTransportSafe': True, 'decodedStreamsUnchanged': True,
        'pageContentAndNavigationUnchanged': True,
    }
    if report_path:
        report_path = report_path.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.report), indent=2))


if __name__ == '__main__':
    main()
