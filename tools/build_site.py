#!/usr/bin/env python3
"""Build the offline documentation from repository sources; no network or bundler."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIRS = ("skills", "knowledge", "profiles", "docs", "examples")
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".toml", ".fs", ".mjs"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "section"


def source_files() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "catalog.json", ROOT / "pyproject.toml"]
    for folder in (*CONTENT_DIRS, "provenance", "tools", "tests"):
        files.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and p.suffix in TEXT_SUFFIXES
                     and "__pycache__" not in p.parts and "originals" not in p.parts)
    return sorted(set(files))


def build_data() -> tuple[dict, list[dict]]:
    sources = {p.relative_to(ROOT).as_posix(): {"text": p.read_text(), "sha256": digest(p)}
               for p in source_files()}
    documents, links = {}, []
    md = MarkdownIt("commonmark", {"html": False}).enable("table")

    for path, source in sources.items():
        if not path.endswith(".md"):
            continue
        raw = source["text"]
        content = re.sub(r"\A---\n.*?\n---\n", "", raw, count=1, flags=re.S)
        tokens = md.parse(content)
        headings, used = [], {}
        first_title_end = 0
        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                title = tokens[i + 1].content
                base = slug(title)
                count = used.get(base, 0)
                used[base] = count + 1
                anchor = base + (f"-{count}" if count else "")
                token.attrSet("id", anchor)
                headings.append({"level": int(token.tag[1:]), "title": title, "id": anchor})
                if token.tag == "h1" and not first_title_end:
                    first_title_end = i + 3

        def rewrite(token):
            attr = "href" if token.type == "link_open" else "src" if token.type == "image" else None
            if attr:
                href = token.attrGet(attr) or ""
                url = urlsplit(href)
                if not url.scheme and not url.netloc:
                    target = ((ROOT / path).parent / unquote(url.path)).resolve() if url.path else ROOT / path
                    try:
                        dest = target.relative_to(ROOT).as_posix()
                    except ValueError:
                        raise ValueError(f"Link leaves framework: {path} -> {href}")
                    exists = target.is_file()
                    record = {"from": path, "href": href, "target": dest, "exists": exists}
                    if url.fragment:
                        record["anchor"] = unquote(url.fragment)
                    links.append(record)
                    if not exists:
                        raise ValueError(f"Missing local link: {path} -> {href}")
                    if attr == "href" and dest in sources:
                        rewritten = ("#read/" if dest.endswith(".md") else "#source/") + dest
                        if url.fragment and dest.endswith(".md"):
                            rewritten += "::" + unquote(url.fragment)
                    else:
                        rewritten = dest
                        if url.fragment:
                            rewritten += "#" + url.fragment
                    token.attrSet(attr, rewritten)
            for child in token.children or []:
                rewrite(child)

        for token in tokens:
            rewrite(token)
        title = next((h["title"] for h in headings if h["level"] == 1), Path(path).stem)
        documents[path] = {
            "title": title,
            "html": md.renderer.render(tokens, md.options, {}),
            "body": md.renderer.render(tokens[first_title_end:], md.options, {}),
            "plain": content.strip(),
            "headings": headings,
        }
    for link in links:
        if link.get("anchor") and link["target"] in documents:
            anchors = {h["id"] for h in documents[link["target"]]["headings"]}
            if link["anchor"] not in anchors:
                raise ValueError(f"Missing heading: {link['from']} -> {link['href']}")
    catalog = json.loads((ROOT / "catalog.json").read_text())
    lab = json.loads((ROOT / "examples/checker-lab/results/summary.json").read_text())
    return {
        "modules": catalog["modules"],
        "joints": json.loads((ROOT / "examples/printed-joints/catalog.json").read_text()),
        "cases": json.loads((ROOT / "examples/catalog.json").read_text()),
        "assets": json.loads((ROOT / "provenance/assets.json").read_text()),
        "documents": documents, "sources": sources, "lab": lab,
        "reports": {s["report"]: json.loads((ROOT / s["report"]).read_text()) for s in lab},
    }, links


def generated_files(data: dict) -> dict[str, str]:
    return {
        "index.html": (ROOT / "site/src/index.html").read_text(),
        "site/style.css": (ROOT / "site/src/style.css").read_text(),
        "site/app.js": (ROOT / "site/src/app.js").read_text(),
        "site/data.js": "/* Generated by tools/build_site.py. Edit the sources. */\nwindow.CAD_DATA = "
                        + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
    }


def main():
    (ROOT / "index.html").write_text((ROOT / "site/src/index.html").read_text())
    data, links = build_data()
    for name, content in generated_files(data).items():
        (ROOT / name).write_text(content)
    report = {"status": "passed", "documents": len(data["documents"]),
              "source_files": len(data["sources"]), "local_links": len(links),
              "modules": len(data["modules"]), "case_studies": len(data["cases"]),
              "lab_cases": len(data["lab"]), "network_required": False,
              "outputs": {name: digest(ROOT / name) for name in generated_files(data)}}
    (ROOT / "validation").mkdir(exist_ok=True)
    (ROOT / "validation/build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
