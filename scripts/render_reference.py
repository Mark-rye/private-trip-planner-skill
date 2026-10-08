#!/usr/bin/env python3
"""Preserve a user's full HTML guide, adding mobile reading and explicit annotations.

Input is private source material, never a bundled/public sample. CSP blocks remote
scripts and resources; all original body content remains in the output unchanged.
"""
import argparse
import hashlib
import json
import re
import secrets
from pathlib import Path


def render(source, notes, asset):
    if "</head>" not in source or "</body>" not in source:
        raise ValueError("reference must be a complete HTML document")
    payload = json.dumps(notes, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    nonce = secrets.token_hex(24)
    enhancement = asset.replace("__REFERENCE_NOTES__", payload).replace("<script>", f'<script nonce="{nonce}">')
    # Keep original lines and body bytes: insert additions at tag boundaries only.
    policy = f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'nonce-{nonce}\'; style-src \'unsafe-inline\'; img-src data:; font-src \'none\'; base-uri \'none\'; form-action \'none\'">'
    source = re.sub(r"<head\b[^>]*>", lambda match: match.group(0) + policy, source, count=1, flags=re.I)
    return source.replace("</body>", enhancement + "</body>", 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--enhancements", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    raw = a.input.read_text(encoding="utf-8")
    notes = json.loads(a.enhancements.read_text(encoding="utf-8"))
    if not isinstance(notes.get("days"), list):
        raise ValueError("enhancements.days must be an array")
    asset = Path(__file__).resolve().parent.parent / "assets" / "reference-enhancement.html"
    result = render(raw, notes, asset.read_text(encoding="utf-8"))
    a.output.write_text(result, encoding="utf-8")
    print(json.dumps({"output": str(a.output), "source_sha256": hashlib.sha256(raw.encode()).hexdigest(), "original_body_preserved": raw.split("<body", 1)[1].split("</body>", 1)[0] in result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
