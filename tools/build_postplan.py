#!/usr/bin/env python3
"""Generate a script-free, self-contained discussion edition for Postplan."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from PIL import Image
import yaml

from build_site import ROOT, build_data, slug

MAX_BYTES = 512 * 1024
OUTPUT = ROOT / "site/postplan.html"
esc = html.escape
DATA, _ = build_data()
SOURCES: dict[str, str] = {}
IMAGE_RECORDS: dict[str, dict] = {}


def doc_id(path: str) -> str:
    return "doc-" + slug(path)


SELECTED = {
    "docs/architecture.md", "docs/consolidation.md", "docs/scope.md",
    "profiles/README.md", "docs/design-languages/mosey.md", "knowledge/core.md", "knowledge/recipes.md",
    "knowledge/construction-patterns.md", "knowledge/verification.md", "knowledge/joints.md", "docs/joints/additional-references.md",
    *(m["document"] for m in DATA["modules"]),
    *(c["document"] for c in DATA["cases"]),
}


class Fragment(HTMLParser):
    """Keep selected Markdown links within this document and namespace IDs."""
    def __init__(self, path: str):
        super().__init__(convert_charrefs=False)
        self.path, self.output = path, []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            image_attrs = dict(attrs)
            self.output.append(image_markup(image_attrs["src"], image_attrs.get("alt", "")))
            return
        mapped = f"h{int(tag[1]) + 1}" if re.fullmatch("h[1-5]", tag) else tag
        attrs = dict(attrs)
        if "id" in attrs:
            attrs["id"] = doc_id(self.path) + "--" + attrs["id"]
        href = attrs.get("href", "")
        if tag == "a" and href.startswith(("#read/", "#source/")):
            target = href.split("/", 1)[1].split("::")[0]
            if target in SELECTED:
                attrs["href"] = "#" + doc_id(target)
            else:
                mapped, attrs = "span", {"class": "local-reference", "title": "Detailed reference in the complete local edition"}
        if tag == "a" and href and not href.startswith(("#", "https://")):
            mapped, attrs = "span", {"class": "local-reference", "title": "File in the complete local edition"}
        if tag not in {"br", "hr", "img", "input", "meta"}:
            self.tags.append((tag, mapped))
        attributes = "".join(f' {key}="{esc(value or "", quote=True)}"' for key, value in attrs.items())
        self.output.append(f"<{mapped}{attributes}>")

    def handle_endtag(self, tag):
        if tag in {"br", "hr", "img", "input", "meta"}:
            return
        original, mapped = self.tags.pop()
        if original != tag:
            raise ValueError(f"Unbalanced generated Markdown: {original}, {tag}")
        self.output.append(f"</{mapped}>")

    def handle_data(self, data):
        self.output.append(esc(data))

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")


def fragment(path: str) -> str:
    SOURCES[path] = DATA["sources"][path]["sha256"]
    parser = Fragment(path)
    parser.feed(DATA["documents"][path]["body"])
    return "".join(parser.output)


def image_markup(path: str, alt: str) -> str:
    original = (ROOT / path).read_bytes()
    if Path(path).suffix == ".svg":
        IMAGE_RECORDS[path] = {"source_sha256": hashlib.sha256(original).hexdigest(),
                              "embedded_sha256": hashlib.sha256(original).hexdigest(),
                              "bytes": len(original), "processing": "Own vector illustration, embedded unchanged as SVG"}
        return original.decode()
    with Image.open(BytesIO(original)) as im:
        im.thumbnail((540, 470) if path.startswith("site/assets/joints-") else (600, 520), Image.Resampling.LANCZOS)
        encoded = BytesIO()
        im.save(encoded, format="WEBP", quality=73, method=6)
        raw = encoded.getvalue()
        IMAGE_RECORDS[path] = {"source_sha256": hashlib.sha256(original).hexdigest(),
                              "embedded_sha256": hashlib.sha256(raw).hexdigest(),
                              "width": im.width, "height": im.height, "bytes": len(raw),
                              "processing": "Downsampled and compressed as WebP; no semantic editing"}
        return f'<img src="data:image/webp;base64,{base64.b64encode(raw).decode()}" alt="{esc(alt)}" width="{im.width}" height="{im.height}">'


def picture(path: str, alt: str, caption: str = "", cls: str = "") -> str:
    return f'<figure class="{cls}">{image_markup(path, alt)}' + (f'<figcaption>{esc(caption)}</figcaption>' if caption else "") + '</figure>'


def article(path: str, title: str | None = None) -> str:
    title = title or DATA["documents"][path]["title"]
    anchor = ' id="mosey"' if path == "docs/design-languages/mosey.md" else (' id="joints"' if path == "examples/printed-joints/README.md" else "")
    return f'<details class="reading" id="{doc_id(path)}"><summary>{esc(title)}</summary><div class="article"{anchor}>{fragment(path)}</div></details>'


def heading(number: str, title: str, intro: str = "") -> str:
    return f'<div class="section-heading"><span class="eyebrow accent">{esc(number)}</span><h2>{esc(title)}</h2>' + (f'<p>{esc(intro)}</p>' if intro else "") + '</div>'


def profiles() -> str:
    presets = [
        ("te-like", "Instrument", "Selective facets, visible hardware and restrained functional accents.", ["#cecdc7", "#535953", "#ed602f"], 3),
        ("soft-consumer", "Soft Consumer", "Soft transitions, calm surfaces and restrained labelling.", ["#dedfce", "#a4ae95", "#626b51"], 22),
        ("rugged-industrial", "Rugged Industrial", "Substantial structure, accessible connections and contrasting control areas.", ["#717866", "#313a31", "#e5b044"], 2),
        ("workshop-042", "Workshop 0.42", "Flush transitions and a distinct historical 0.42/4.2 edge family.", ["#dddcd2", "#6b7164", "#d66e43"], 10),
        ("mosey", "Mosey", "Calm sculptural bodies and large tactile controls. Soft volumes, broad facets and useful supporting shells.", ["#BDD1BA", "#F0EDDF", "#C6B6D7"], 22),
    ]
    cards = []
    for name, title, description, colors, radius in presets:
        path = f"profiles/design-language/{name}.yaml"
        raw = (ROOT / path).read_text()
        SOURCES[path] = hashlib.sha256(raw.encode()).hexdigest()
        yaml.safe_load(raw)
        holes = "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="#f4f3ef" stroke="#59664b"/>' for x, y in [(40, 35), (200, 35), (40, 125), (200, 125)])
        svg = f'<svg viewBox="0 0 240 160" role="img" aria-label="{title}: the same four mounting positions"><rect x="20" y="15" width="200" height="130" rx="{radius}" fill="{colors[0]}" stroke="#67705f"/>{holes}<rect x="67" y="57" width="105" height="44" rx="{min(radius, 8)}" fill="{colors[1]}"/><circle cx="146" cy="79" r="14" fill="{colors[2]}"/></svg>'
        reading = '<a class="text-link" href="#mosey">Interpretation with examples ↗</a>' if name == "mosey" else ""
        cards.append(f'<div class="profile-card">{svg}<h3>{title}</h3><p>{description}</p>{reading}<details><summary>View profile values</summary><pre>{esc(raw)}</pre></details></div>')
    return '<div class="profile-grid">' + "".join(cards) + '</div><p class="caption">Schematic colour and form examples. The four interfaces remain unchanged. Profile values are starting points, not physical calibration.</p>'


def main():
    brand = '<a class="brand" href="#overview"><svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3 35 12v17l-15 9L5 29V12Z M5 12l15 9 15-9 M20 21v17" fill="none" stroke="currentColor" stroke-width="2.2"/></svg><span>cad<span class="brand-dot">.</span><br>skills</span></a>'
    sections = [("overview", "Overview"), ("architecture", "Architecture"), ("skills", "Skill library"), ("profiles", "Profile"), ("examples", "In practice"), ("evidence", "Verification lab"), ("knowledge", "Knowledge base"), ("next", "Development")]
    nav = '<nav>' + "".join(f'<a href="#{key}"><span class="nav-number">{i:02}</span>{label}</a>' for i, (key, label) in enumerate(sections, 1)) + '</nav>'
    hero = picture("site/assets/sparky-after.png", "Sparky R14: rear view of the X/Z unit", "SPARKY / R14 · NATIVE CAD GEOMETRY", "hero-figure")
    content = [f'<section id="overview" class="chapter first"><div class="page-meta"><span class="pill warm">READING EDITION / 10 SEPTEMBER 2026</span><span class="eyebrow">FROM 27 PROJECT AND TOOL FOLDERS</span></div><div class="hero"><div class="hero-copy"><span class="eyebrow accent">A SHARED TOOLKIT</span><h1>From idea<br>to part<span class="accent-dot">.</span></h1><p>CAD knowledge that fits together. Construction, manufacturing and design, connected through traceable checks and real project examples.</p><a class="button" href="#architecture">Explore the framework ↗</a></div>{hero}</div><div class="stats-line"><div class="stat"><strong>10</strong><span>composable skills</span></div><div class="stat"><strong>08</strong><span>practical case studies</span></div><div class="stat"><strong>05</strong><span>shared layers</span></div></div><p class="edition-note">This reading edition brings together the architecture, skill entrypoints and project examples for discussion. Chapters and details open without JavaScript. The complete local edition also includes the interactive workbench, full-text search, note export and all technical references.</p></section>']

    content.append('<section id="architecture" class="chapter">' + heading("02 / CONNECTIONS", "Five layers. One shared workflow.", "Combine the building blocks to suit the task.") + f'<div class="article" id="{doc_id("docs/architecture.md")}">{fragment("docs/architecture.md")}</div></section>')

    skills = "".join(article(m["document"], m["title"]) for m in DATA["modules"])
    content.append('<section id="skills" class="chapter">' + heading("03 / SKILL LIBRARY", "The knowledge has a shared home.", "Ten short entrypoints. Open a skill to read its purpose and working method. All documentation uses English; detailed technical references are included in the complete local edition.") + skills + '</section>')

    manufacturing = '<div class="table-wrap"><table><thead><tr><th>Process</th><th>Key parameters</th><th>Status in the collection</th></tr></thead><tbody><tr><td>FDM</td><td>Print pose, material, layers, fit and support</td><td>Most extensively documented project branch</td></tr><tr><td>Laser cutting</td><td>Material thickness, kerf and assembly sequence</td><td>Concrete file trolley export</td></tr><tr><td>CNC</td><td>Tool access, internal radii and workholding</td><td>References; general CAM workflow remains open</td></tr><tr><td>SLA / MSLA</td><td>Orientation, supports, finishing and resin</td><td>Uncalibrated starting profiles</td></tr></tbody></table></div>'
    content.append('<section id="profiles" class="chapter">' + heading("04 / PROFILE", "One language. Several manufacturing paths.", "Design language, manufacturing process and protected interfaces each have their own role.") + profiles() + article("docs/design-languages/mosey.md", "Mosey — illustrated interpretation, references and CAD rules") + manufacturing + article("profiles/README.md", "How to use the profiles") + '</section>')

    cases = []
    for i, case in enumerate(DATA["cases"], 1):
        gallery = picture(case["image"], case["title"], case["project"])
        if case["id"] == "sparky":
            gallery = '<div class="comparison">' + picture("site/assets/sparky-before.png", "Sparky R13 rear view", "R13 / BEFORE") + picture(case["image"], "Sparky R14 rear view, same camera", "R14 / AFTER") + '</div>'
        extra = picture("site/assets/c2-page.png", "Page 4 of the C2 assembly guide", "FROM THE ACTUAL C2 MANUAL") if case["id"] == "c2" else ""
        anchor = ' id="joints"' if case["id"] == "printed-joints" else ""
        cases.append(f'<article class="case-study" id="{doc_id(case["document"])}"><span class="eyebrow accent">{i:02} / {esc(case["project"])}</span><h3{anchor}>{esc(case["title"])}</h3><p class="case-intro">{esc(case["summary"])}</p>{gallery}<div class="article">{fragment(case["document"])}</div>{extra}</article>')
    content.append('<section id="examples" class="chapter">' + heading("05 / IN PRACTICE", "Lessons that carry a project forward.", "Images come from the documented project revisions. They were downsampled and compressed for this compact reading edition.") + "".join(cases) + '</section>')

    rows = []
    for case in DATA["lab"]:
        report = DATA["reports"][case["report"]]
        SOURCES[case["report"]] = hashlib.sha256((ROOT / case["report"]).read_bytes()).hexdigest()
        findings = "<ul>" + "".join(f'<li>{esc(p)}</li>' for p in report["problems"]) + "</ul>" if report["problems"] else "No findings within the configured check scope."
        rows.append(f'<tr><td><strong>{esc(case["title"])}</strong></td><td><code>{esc(report["status"])}</code></td><td>{findings}</td></tr>')
    lab = '<div class="table-wrap"><table><thead><tr><th>Test body</th><th>Result</th><th>Actual raw finding</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
    content.append('<section id="evidence" class="chapter">' + heading("06 / VERIFICATION LAB", "What does a checker actually detect?", "Four locally generated test geometries with results from the consolidated mesh checker.") + lab + '<p class="edition-note">The helpers passed 31 regression tests. The checker combines Sparky body, orientation and failure checks with bounded rasterisation and edge-attachment checks from Distributor. These results establish neither physical fit nor load capacity.</p>' + article("knowledge/verification.md") + '</section>')

    content.append('<section id="knowledge" class="chapter">' + heading("07 / KNOWLEDGE BASE", "The shared rules.", "Source, task selection and reusable construction patterns connect the different tools.") + "".join(article(p) for p in ["knowledge/joints.md", "docs/joints/additional-references.md", "knowledge/core.md", "knowledge/recipes.md", "knowledge/construction-patterns.md"]) + '</section>')
    content.append('<section id="next" class="chapter">' + heading("08 / DEVELOPMENT", "A concrete foundation. Useful next questions.", "Use this foundation to discuss maintenance boundaries and the first complete pilot case.") + article("docs/consolidation.md", "What was consolidated and what we should decide") + article("docs/scope.md", "Scope, runtimes and maturity") + '<div class="closing"><h3>A starting point for discussion</h3><p>Start with the architecture and Sparky example. Then define maintenance boundaries, desired design languages and a small end-to-end CAD, FDM and manual pilot.</p><p>The local framework remains the maintained source. This page is a generated reading edition; it does not establish a public open-source licence.</p><a class="text-link" href="#overview">↑ Back to overview</a></div></section>')

    css = (ROOT / "site/src/style.css").read_text() + (ROOT / "site/src/postplan.css").read_text()
    result = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="CAD Skills Framework: architecture, ten skills and eight project examples."><title>CAD Skills Framework — Reading edition</title><style>' + css + '</style></head><body><a class="skip-link" href="#main">Skip to content</a><aside class="sidebar">' + brand + '<div class="edition"><span class="status-dot"></span> FRAMEWORK / 01</div>' + nav + '<div class="sidebar-bottom">READ · UNDERSTAND · DISCUSS<br>Working edition 0.1 / 10 September 2026</div></aside><div class="shell"><header class="topbar"><span class="breadcrumb">CAD Skills <span class="slash">/</span> Reading edition</span><span class="search-hint">Find: ⌘ F / Ctrl F</span></header><details class="mobile-nav"><summary>Open chapters</summary>' + nav + '</details><main id="main">' + "".join(content) + '</main><footer class="footer"><span>CAD SKILLS FRAMEWORK · 10 September 2026</span><span>Derived from real projects.</span></footer></div></body></html>'
    validate(result)
    OUTPUT.write_text(result)
    report = {"status": "passed", "format": "script-free HTML with inline CSS, WebP images and own SVG illustration", "bytes": len(result.encode()), "max_bytes": MAX_BYTES,
              "selected_documents": len(SELECTED), "skills": len(DATA["modules"]), "case_studies": len(DATA["cases"]), "sha256": hashlib.sha256(result.encode()).hexdigest(),
              "sources_sha256": SOURCES, "images": IMAGE_RECORDS}
    (ROOT / "validation/postplan-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"sources_sha256", "images"}}, indent=2))


def validate(document: str):
    if len(document.encode()) > MAX_BYTES:
        raise ValueError("Postplan HTML exceeds 512 KiB")
    if re.search(r"/Users/|/home/|~/|https?://(?:localhost|127\.0\.0\.1)", document):
        raise ValueError("Machine-specific path or private CAD URL in publication")

    class Audit(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids, self.anchors = [], []

        def handle_starttag(self, tag, attrs):
            if tag in {"script", "form", "iframe", "embed", "object", "applet", "base", "link"}:
                raise ValueError(f"Forbidden tag {tag}")
            for key, value in attrs:
                if key.startswith("on"):
                    raise ValueError(f"Event handler {key}")
                if key == "id":
                    self.ids.append(value)
                if key == "href":
                    if value.startswith("#"):
                        self.anchors.append(value[1:])
                    else:
                        source = urlsplit(value)
                        allowed = source.netloc == "mosey.camera"
                        allowed |= source.netloc == "www.youtube.com" and ((source.path == "/watch" and parse_qs(source.query).get("v", [""])[0] in {"fSISiR5XIbk", "zI8OgRRF5d8", "WY8yd191qVE", "E6BHts_ii8s"}) or source.path in {"/shorts/UUiE-b5xlbo", "/shorts/JXoMlPqsxLQ", "/shorts/ER19yHpgT30"})
                        allowed |= source.netloc == "cad.onshape.com" and source.path.startswith("/documents/e9f4df9ee8ab9bb13f4c372b/")
                        if source.scheme != "https" or not allowed:
                            raise ValueError(f"Unapproved external source reference: {value}")
                if key == "src" and not value.startswith("data:image/webp;base64,"):
                    raise ValueError("Non-embedded image")
    audit = Audit()
    audit.feed(document)
    if len(audit.ids) != len(set(audit.ids)):
        raise ValueError("Duplicate HTML ID")
    missing = set(audit.anchors) - set(audit.ids)
    if missing:
        raise ValueError(f"Missing local anchors: {missing}")


if __name__ == "__main__":
    main()
