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
    "README.md", "docs/architecture.md", "docs/history.md", "docs/scope.md", "profiles/README.md",
    *(a["path"] for a in DATA["knowledge"]["articles"]),
    *(m["document"] for m in DATA["modules"]),
    *(l["document"] for l in DATA["labs"]),
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
    anchor = ' id="mosey"' if path == "knowledge/design/mosey.md" else (' id="joints"' if path == "labs/printed-joints/README.md" else "")
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
    brand = '<a class="brand" href="#overview"><svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3 35 12v17l-15 9L5 29V12Z M5 12l15 9 15-9 M20 21v17" fill="none" stroke="currentColor" stroke-width="2.2"/></svg><span>tool<span class="brand-dot">\u00b7</span><br>room</span></a>'
    sections = [("overview", "Overview"), ("architecture", "Architecture"), ("skills", "Skills"), ("profiles", "Profiles"), ("labs", "Labs"), ("knowledge", "Knowledge base"), ("next", "Development")]
    nav = '<nav>' + "".join(f'<a href="#{key}"><span class="nav-number">{i:02}</span>{label}</a>' for i, (key, label) in enumerate(sections, 1)) + '</nav>'
    hero = picture("site/assets/joints-J06-assembled.png", "Two printed parts joined by the J06 echo-lock principle", "PRINTED JOINTS LAB / J06 \u00b7 NATIVE CAD GEOMETRY", "hero-figure")
    stats = f'<div class="stats-line"><div class="stat"><strong>{len(DATA["modules"]):02}</strong><span>composable skills</span></div><div class="stat"><strong>{len(DATA["knowledge"]["articles"]):02}</strong><span>knowledge articles</span></div><div class="stat"><strong>{len(DATA["labs"]):02}</strong><span>reproducible labs</span></div></div>'
    content = [f'<section id="overview" class="chapter first"><div class="page-meta"><span class="pill warm">READING EDITION / 10 SEPTEMBER 2026</span><span class="eyebrow">A CAD KNOWLEDGE BASE AND SKILL FRAMEWORK</span></div><div class="hero"><div class="hero-copy"><span class="eyebrow accent">TOOLROOM</span><h1>From idea<br>to part<span class="accent-dot">.</span></h1><p>CAD knowledge that fits together. Construction, manufacturing and design, connected through traceable checks and reproducible labs.</p><a class="button" href="#architecture">Explore the framework \u2197</a></div>{hero}</div>{stats}<p class="edition-note">This reading edition brings together the architecture, skill entrypoints, knowledge base and labs for discussion. Chapters and details open without JavaScript. The complete local edition also includes the interactive workbench, full-text search, note export and all technical references.</p>' + article("README.md", "Read me: what Toolroom is") + '</section>']

    content.append('<section id="architecture" class="chapter">' + heading("02 / CONNECTIONS", "Five layers. One shared workflow.", "Combine the building blocks to suit the task.") + f'<div class="article" id="{doc_id("docs/architecture.md")}">{fragment("docs/architecture.md")}</div></section>')

    skills = "".join(article(m["document"], m["title"]) for m in DATA["modules"])
    content.append('<section id="skills" class="chapter">' + heading("03 / SKILLS", "An entrypoint for every task.", "Ten short entrypoints. Open a skill to read its purpose and working method. All documentation uses English; detailed technical references are included in the complete local edition.") + skills + '</section>')

    manufacturing = '<div class="table-wrap"><table><thead><tr><th>Process</th><th>Key parameters</th><th>Status in the collection</th></tr></thead><tbody><tr><td>FDM</td><td>Print pose, material, layers, fit and support</td><td>Most extensively documented branch</td></tr><tr><td>Laser cutting</td><td>Material thickness, kerf and assembly sequence</td><td>Worked export example</td></tr><tr><td>CNC</td><td>Tool access, internal radii and workholding</td><td>References; general CAM workflow remains open</td></tr><tr><td>SLA / MSLA</td><td>Orientation, supports, finishing and resin</td><td>Uncalibrated starting profiles</td></tr></tbody></table></div>'
    content.append('<section id="profiles" class="chapter">' + heading("04 / PROFILES", "One language. Several manufacturing paths.", "Design language, manufacturing process and protected interfaces each have their own role.") + profiles() + manufacturing + article("profiles/README.md", "How to use the profiles") + '</section>')

    rows = []
    for case in DATA["lab"]:
        report = DATA["reports"][case["report"]]
        SOURCES[case["report"]] = hashlib.sha256((ROOT / case["report"]).read_bytes()).hexdigest()
        findings = "<ul>" + "".join(f'<li>{esc(p)}</li>' for p in report["problems"]) + "</ul>" if report["problems"] else "No findings within the configured check scope."
        rows.append(f'<tr><td><strong>{esc(case["title"])}</strong></td><td><code>{esc(report["status"])}</code></td><td>{findings}</td></tr>')
    checker_table = '<div class="table-wrap"><table><thead><tr><th>Test body</th><th>Result</th><th>Actual raw finding</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
    labs = []
    for i, lab in enumerate(DATA["labs"], 1):
        gallery = picture(lab["image"], lab["title"], lab["kind"]) if Path(lab["image"]).suffix == ".png" else ""
        extra = checker_table if lab["id"] == "checker-lab" else ""
        labs.append(f'<article class="lab-report" id="{doc_id(lab["document"])}-intro"><span class="eyebrow accent">{i:02} / {esc(lab["tag"])}</span><h3>{esc(lab["title"])}</h3><p class="lab-intro">{esc(lab["summary"])}</p>{gallery}{extra}<p class="edition-note">Run: <code>{esc(lab["runnable"])}</code></p>' + article(lab["document"]) + '</article>')
    content.append('<section id="labs" class="chapter">' + heading("05 / LABS", "Reproducible experiments with their own evidence.", "A lab is a small, non-personal experiment that can be rebuilt from the repository. A lab result is evidence about geometry or a helper; it is never a physical acceptance.") + "".join(labs) + '</section>')

    knowledge = []
    for section in DATA["knowledge"]["sections"]:
        articles = [a for a in DATA["knowledge"]["articles"] if a["section"] == section["id"]]
        if not articles:
            continue
        knowledge.append(f'<h3 class="knowledge-section">{esc(section["title"])}</h3><p class="edition-note">{esc(section["summary"])}</p>' + "".join(article(a["path"], a["title"]) for a in articles))
    content.append('<section id="knowledge" class="chapter">' + heading("06 / KNOWLEDGE BASE", "The shared rules.", "Backend-independent knowledge in six sections. Skills link into it instead of repeating it.") + "".join(knowledge) + '</section>')

    content.append('<section id="next" class="chapter">' + heading("07 / DEVELOPMENT", "A concrete foundation. Useful next questions.", "Use this foundation to discuss maintenance boundaries and the first complete pilot case.") + article("docs/history.md", "How the repository got its current shape") + article("docs/scope.md", "Scope, runtimes and maturity") + '<div class="closing"><h3>A starting point for discussion</h3><p>Start with the architecture and the Printed Joints Lab. Then define maintenance boundaries, desired design languages and a small end-to-end CAD, FDM and manual pilot.</p><p>The local repository remains the maintained source. This page is a generated reading edition; it does not establish a public open-source licence.</p><a class="text-link" href="#overview">\u2191 Back to overview</a></div></section>')

    css = (ROOT / "site/src/style.css").read_text() + (ROOT / "site/src/postplan.css").read_text()
    result = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Toolroom: a CAD knowledge base and skill framework for AI-assisted design."><title>Toolroom \u2014 Reading edition</title><style>' + css + '</style></head><body><a class="skip-link" href="#main">Skip to content</a><aside class="sidebar">' + brand + '<div class="edition"><span class="status-dot"></span> TOOLROOM / 01</div>' + nav + '<div class="sidebar-bottom">READ \u00b7 UNDERSTAND \u00b7 DISCUSS<br>Working edition 0.1 / 10 September 2026</div></aside><div class="shell"><header class="topbar"><span class="breadcrumb">Toolroom <span class="slash">/</span> Reading edition</span><span class="search-hint">Find: \u2318 F / Ctrl F</span></header><details class="mobile-nav"><summary>Open chapters</summary>' + nav + '</details><main id="main">' + "".join(content) + '</main><footer class="footer"><span>TOOLROOM \u00b7 10 September 2026</span><span>A CAD knowledge base and skill framework.</span></footer></div></body></html>'
    validate(result)
    OUTPUT.write_text(result)
    report = {"status": "passed", "format": "script-free HTML with inline CSS, WebP images and own SVG illustration", "bytes": len(result.encode()), "max_bytes": MAX_BYTES,
              "selected_documents": len(SELECTED), "skills": len(DATA["modules"]),
              "knowledge_articles": len(DATA["knowledge"]["articles"]), "labs": len(DATA["labs"]),
              "sha256": hashlib.sha256(result.encode()).hexdigest(),
              "sources_sha256": SOURCES, "images": IMAGE_RECORDS}
    (ROOT / "validation/postplan-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"sources_sha256", "images"}}, indent=2))


def validate(document: str):
    if len(document.encode()) > MAX_BYTES:
        raise ValueError("Postplan HTML exceeds 512 KiB")
    if re.search(r"/Users/|/home/", document):
        raise ValueError("Machine-specific absolute path in publication")
    prose = re.sub(r"<(code|pre)\b[^>]*>.*?</\1>", "", document, flags=re.S)
    if re.search(r"~/|https?://(?:localhost|127\.0\.0\.1)", prose):
        raise ValueError("Home-relative path or local server URL outside a code example")

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
                        allowed |= source.netloc == "www.youtube.com" and ((source.path == "/watch" and parse_qs(source.query).get("v", [""])[0] in {"fSISiR5XIbk", "zI8OgRRF5d8", "WY8yd191qVE", "E6BHts_ii8s", "7aJ4dDyyf20"}) or source.path in {"/shorts/UUiE-b5xlbo", "/shorts/JXoMlPqsxLQ", "/shorts/ER19yHpgT30"})
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
