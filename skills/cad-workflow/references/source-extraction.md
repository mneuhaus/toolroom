# Bounded source extraction

Use this helper when a research worker needs to hand an authoritative CAD worker short, inspectable evidence instead of a whole page. The worker finds candidate sources with its native search tool, creates a local snapshot, and sends focused excerpts with the source URL and hashes. The CAD worker interprets the evidence and retains that interpretation in the relevant rule or project record.

```sh
python skills/cad-workflow/scripts/source_extract.py snapshot \
  --url 'https://example.org/specification' --out evidence/source-01
python skills/cad-workflow/scripts/source_extract.py excerpt \
  --snapshot evidence/source-01 --query 'clearance' --out evidence/clearance.json
```

For an already acquired local document, use `snapshot --file INPUT --origin-url URL --out DIR`. The snapshot directory contains immutable `raw.bin`, a normalized readable `text.txt`, and `source.json`. It records the URL, retrieval time, content type, byte count, and SHA-256 hashes. Text offsets in excerpt JSON are Unicode character offsets into `text.txt`.

The helper accepts only HTTP(S) URLs, does not authenticate, render a browser, execute JavaScript, or run arbitrary source code. It accepts readable HTML, plain text, Markdown, CSV, JSON, and XML inputs; PDFs and other binary formats are explicitly unsupported. Downloads and input files are capped at 2 MiB by default. The 15-second default is a socket-operation timeout, not a whole-download deadline. Unsupported URLs and failed, oversized, JavaScript-only (dynamic-content-suspected), empty, or otherwise incomplete retrievals have an explicit non-complete state in `source.json`; do not treat them as evidence.

`excerpt` verifies both stored hashes before it reads text. Its JSON only copies matching source windows and their offsets; a miss is reported as `incomplete` with `query_not_found`. It does not infer facts. A quoted passage proves that the passage occurs in that recorded snapshot, not that the passage is accurate, current, applicable to a part, or sufficient to validate a CAD decision.
