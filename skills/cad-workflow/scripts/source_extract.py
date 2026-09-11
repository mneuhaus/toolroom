#!/usr/bin/env python3
"""Create bounded, auditable source snapshots and focused text excerpts.

This utility deliberately records bytes and extracted text; it does not render a
page, execute page code, authenticate, or decide whether a source's claims are
true.  Offsets in excerpt output are Unicode character offsets into ``text.txt``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_CHARS = 4_000
METADATA_NAME = "source.json"
RAW_NAME = "raw.bin"
TEXT_NAME = "text.txt"
SKIP_TAGS = {"script", "style", "nav", "noscript", "template", "svg"}
SUPPORTED_CONTENT_TYPES = {
    "text/html", "text/plain", "text/markdown", "text/csv", "text/xml",
    "application/json", "application/xml",
}
LOCAL_CONTENT_TYPES = {
    ".html": "text/html", ".htm": "text/html", ".txt": "text/plain",
    ".md": "text/markdown", ".csv": "text/csv", ".json": "application/json",
    ".xml": "application/xml",
}


class SourceError(Exception):
    """A snapshot cannot be safely created or read."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in SKIP_TAGS:
            self.skip_depth += 1
        elif not self.skip_depth and tag.lower() in {"p", "br", "li", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag.lower() in {"p", "li", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalise_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[^\S\n]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_readable_text(raw: bytes, content_type: str = "") -> str:
    """Return a deterministic, best-effort readable representation of raw bytes."""
    encoding_match = re.search(r"charset\s*=\s*[\"']?([^;\"'\s]+)", content_type, re.I)
    encoding = encoding_match.group(1) if encoding_match else "utf-8"
    text = raw.decode(encoding, errors="replace")
    if "html" not in content_type.lower() and not re.search(r"<\s*html\b|<\s*body\b", text, re.I):
        return _normalise_text(text)
    parser = _TextExtractor()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        # HTMLParser is intentionally best effort; retain readable decoded text.
        return _normalise_text(re.sub(r"<[^>]*>", " ", text))
    return _normalise_text("".join(parser.parts))


def _prepare_out(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise SourceError(f"output directory must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)


def _write_metadata(out: Path, metadata: dict[str, Any]) -> None:
    (out / METADATA_NAME).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(out: Path, *, status: str, reason: str, source_url: str | None, retrieved_at: str) -> dict[str, Any]:
    result = {"format": 1, "status": status, "reason": reason, "source_url": source_url,
              "retrieved_at": retrieved_at, "raw_file": None, "raw_sha256": None,
              "text_file": None, "text_sha256": None}
    _write_metadata(out, result)
    return result


def _read_limited(stream: Any, max_bytes: int) -> tuple[bytes | None, bool]:
    data = stream.read(max_bytes + 1)
    return (None, True) if len(data) > max_bytes else (data, False)


def _media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _stored_state(out: Path, *, status: str, reason: str, source_url: str | None,
                  retrieved_at: str, content_type: str, raw: bytes) -> dict[str, Any]:
    """Record a retrieved but unusable body without pretending it was extracted."""
    metadata = {
        "format": 1, "status": status, "reason": reason, "source_url": source_url,
        "retrieved_at": retrieved_at, "content_type": content_type, "byte_count": len(raw),
        "raw_file": RAW_NAME, "raw_sha256": _sha256(raw), "text_file": None,
        "text_sha256": None,
    }
    _write_metadata(out, metadata)
    return metadata


def snapshot(*, url: str | None, file: str | Path | None, out: str | Path,
             origin_url: str | None = None, max_bytes: int = DEFAULT_MAX_BYTES,
             timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Snapshot one HTTP(S) URL or one local file into an initially empty directory."""
    if bool(url) == bool(file):
        raise SourceError("provide exactly one of url or file")
    if max_bytes < 1 or timeout < 1:
        raise SourceError("max_bytes and timeout must be positive")
    output = Path(out)
    _prepare_out(output)
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    source_url = url or origin_url or Path(file).resolve().as_uri()  # type: ignore[arg-type]
    content_type = "application/octet-stream"
    try:
        if url:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return _state(output, status="unsupported", reason="only_http_and_https_urls_are_supported",
                              source_url=url, retrieved_at=retrieved_at)
            request = urllib.request.Request(url, headers={"User-Agent": "toolroom-source-extract/1"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type") or "application/octet-stream"
                if _media_type(content_type) not in SUPPORTED_CONTENT_TYPES:
                    return _state(output, status="unsupported", reason="unsupported_content_type",
                                  source_url=response.geturl(), retrieved_at=retrieved_at)
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > max_bytes:
                    return _state(output, status="incomplete", reason="content_length_exceeds_max_bytes",
                                  source_url=response.geturl(), retrieved_at=retrieved_at)
                raw, oversized = _read_limited(response, max_bytes)
                source_url = response.geturl()
        else:
            source_file = Path(file)  # type: ignore[arg-type]
            if not source_file.is_file():
                raise SourceError(f"file does not exist or is not regular: {source_file}")
            content_type = LOCAL_CONTENT_TYPES.get(source_file.suffix.lower())
            if content_type is None:
                return _state(output, status="unsupported", reason="unsupported_local_file_type",
                              source_url=source_url, retrieved_at=retrieved_at)
            if source_file.stat().st_size > max_bytes:
                return _state(output, status="incomplete", reason="file_exceeds_max_bytes",
                              source_url=source_url, retrieved_at=retrieved_at)
            with source_file.open("rb") as handle:
                raw, oversized = _read_limited(handle, max_bytes)
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as error:
        return _state(output, status="incomplete", reason=f"retrieval_failed:{type(error).__name__}",
                      source_url=source_url, retrieved_at=retrieved_at)

    if oversized or raw is None:
        return _state(output, status="incomplete", reason="body_exceeds_max_bytes",
                      source_url=source_url, retrieved_at=retrieved_at)
    raw_path = output / RAW_NAME
    with raw_path.open("xb") as handle:
        handle.write(raw)
    try:
        readable = extract_readable_text(raw, content_type)
    except LookupError:
        return _stored_state(output, status="unsupported", reason="unsupported_charset", source_url=source_url,
                             retrieved_at=retrieved_at, content_type=content_type, raw=raw)
    text_bytes = readable.encode("utf-8")
    with (output / TEXT_NAME).open("xb") as handle:
        handle.write(text_bytes)
    dynamic_suspected = ("html" in _media_type(content_type) and not readable and
                         bool(re.search(r"<script\b", raw.decode("utf-8", errors="ignore"), re.I)))
    empty_source = not readable and not dynamic_suspected
    metadata = {
        "format": 1, "status": "incomplete" if (dynamic_suspected or empty_source) else "complete",
        "reason": "dynamic_content_suspected" if dynamic_suspected else ("empty_readable_text" if empty_source else None), "source_url": source_url,
        "retrieved_at": retrieved_at, "content_type": content_type, "byte_count": len(raw),
        "raw_file": RAW_NAME, "raw_sha256": _sha256(raw), "text_file": TEXT_NAME,
        "text_sha256": _sha256(text_bytes), "text_offset_unit": "unicode_code_points",
    }
    _write_metadata(output, metadata)
    return metadata


def _load_verified_snapshot(directory: str | Path) -> tuple[dict[str, Any], str]:
    root = Path(directory)
    try:
        metadata = json.loads((root / METADATA_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceError(f"invalid snapshot metadata: {error}") from error
    if metadata.get("status") != "complete":
        raise SourceError(f"snapshot is {metadata.get('status')}: {metadata.get('reason')}")
    if metadata.get("raw_file") != RAW_NAME or metadata.get("text_file") != TEXT_NAME:
        raise SourceError("snapshot metadata contains unsafe file paths")
    raw_path, text_path = root / RAW_NAME, root / TEXT_NAME
    if (raw_path.is_symlink() or text_path.is_symlink() or not raw_path.is_file() or not text_path.is_file() or
            raw_path.parent.resolve() != root.resolve() or text_path.parent.resolve() != root.resolve()):
        raise SourceError("snapshot files must be regular files within the snapshot")
    try:
        raw = raw_path.read_bytes()
        text_bytes = text_path.read_bytes()
    except OSError as error:
        raise SourceError(f"snapshot files unavailable: {error}") from error
    if _sha256(raw) != metadata.get("raw_sha256") or _sha256(text_bytes) != metadata.get("text_sha256"):
        raise SourceError("snapshot integrity check failed")
    try:
        return metadata, text_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceError("snapshot text is not UTF-8") from error


def excerpt(*, snapshot_dir: str | Path, query: str, out: str | Path,
            max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, Any]:
    """Write query-matching source text windows with verified source identity."""
    if not query.strip() or max_chars < 1:
        raise SourceError("query and max_chars must be non-empty")
    metadata, source_text = _load_verified_snapshot(snapshot_dir)
    # re.IGNORECASE reports offsets in the original Unicode string. Casefolding
    # a whole document can change its length (for example, ß -> ss).
    matcher = re.compile(re.escape(query), re.IGNORECASE)
    matches = list(matcher.finditer(source_text))
    if matches and max_chars < max(match.end() - match.start() for match in matches):
        result = {
            "format": 1, "status": "incomplete", "reason": "budget_too_small", "query": query,
            "source_url": metadata["source_url"], "raw_sha256": metadata["raw_sha256"],
            "text_sha256": metadata["text_sha256"], "text_offset_unit": "unicode_code_points",
            "max_chars": max_chars, "excerpt_char_count": 0, "excerpts": [],
        }
        output = Path(out)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        return result
    windows: list[dict[str, Any]] = []
    remaining = max_chars
    for match in matches:
        if remaining <= 0:
            break
        found, match_end = match.start(), match.end()
        context_before = min(300, (max_chars - (match_end - found)) // 2)
        start = max(0, found - context_before)
        end = min(len(source_text), match_end + min(500, max_chars - (match_end - found) - context_before))
        if windows and start <= windows[-1]["end"]:
            windows[-1]["end"] = max(windows[-1]["end"], end)
            windows[-1]["text"] = source_text[windows[-1]["start"]:windows[-1]["end"]]
            continue
        fragment = source_text[start:min(end, start + remaining)]
        windows.append({"start": start, "end": start + len(fragment), "text": fragment})
        remaining -= len(fragment)
    # Merging overlapping contexts can grow a previously bounded window. Apply
    # the caller's output budget after that merge as the final invariant.
    bounded_windows: list[dict[str, Any]] = []
    remaining = max_chars
    for window in windows:
        if remaining <= 0:
            break
        fragment = window["text"][:remaining]
        bounded_windows.append({"start": window["start"], "end": window["start"] + len(fragment), "text": fragment})
        remaining -= len(fragment)
    windows = bounded_windows
    result = {
        "format": 1, "status": "complete" if windows else "incomplete",
        "reason": None if windows else "query_not_found", "query": query,
        "source_url": metadata["source_url"], "raw_sha256": metadata["raw_sha256"],
        "text_sha256": metadata["text_sha256"], "text_offset_unit": "unicode_code_points",
        "max_chars": max_chars, "excerpt_char_count": sum(len(item["text"]) for item in windows),
        "excerpts": windows,
    }
    output = Path(out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = commands.add_parser("snapshot", help="create a bounded source snapshot")
    origin = snapshot_parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--url")
    origin.add_argument("--file")
    snapshot_parser.add_argument("--origin-url")
    snapshot_parser.add_argument("--out", required=True)
    snapshot_parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    snapshot_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    excerpt_parser = commands.add_parser("excerpt", help="write compact text windows from a verified snapshot")
    excerpt_parser.add_argument("--snapshot", required=True)
    excerpt_parser.add_argument("--query", required=True)
    excerpt_parser.add_argument("--out", required=True)
    excerpt_parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args(argv)
    try:
        result = snapshot(url=getattr(args, "url", None), file=getattr(args, "file", None), out=args.out,
                          origin_url=getattr(args, "origin_url", None), max_bytes=getattr(args, "max_bytes", DEFAULT_MAX_BYTES),
                          timeout=getattr(args, "timeout", DEFAULT_TIMEOUT_SECONDS)) if args.command == "snapshot" else excerpt(
                              snapshot_dir=args.snapshot, query=args.query, out=args.out, max_chars=args.max_chars)
    except SourceError as error:
        print(f"source-extract: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "out": args.out}, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
