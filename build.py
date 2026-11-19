#!/usr/bin/env python3
"""Validate changes.toml and build the public page (index.html).

    build.py            validate + write index.html
    build.py --check    validate only

Validation: unique ids, known kinds/statuses/repos/devices, every reference (part_of, depends, must) resolves,
and nothing private: build fails on IP addresses, LAN host names, local paths or the Forgejo host.
Standard library only (Python 3.11+ for tomllib).
"""
from __future__ import annotations

import html
import json
import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = ["goal", "feature", "fix", "issue"]
STATUSES = ["active", "local", "in-pr", "unfixed", "parked", "dropped"]  # merged items are removed
PRIVATE = [
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "an IP address"),
    (re.compile(r"\.lan\b", re.I), "a .lan host name"),
    (re.compile(r"/Volumes/|/srv/|/home/|/Users/"), "a local path"),
    (re.compile(r"forgejo", re.I), "the Forgejo host"),
]


def fail(msg: str):
    print(f"build: {msg}", file=sys.stderr)
    sys.exit(1)


def load() -> dict:
    raw = (HERE / "changes.toml").read_text()
    body = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
    for rx, what in PRIVATE:
        m = rx.search(body)
        if m:
            fail(f"changes.toml contains {what} ({m.group(0)!r}); the page is public")
    return tomllib.loads(raw)


def validate(d: dict):
    repos = {r["id"] for r in d.get("repos", [])}
    devices = {x["id"] for x in d.get("devices", [])}
    ids = [i["id"] for i in d["items"]]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        fail(f"duplicate ids: {', '.join(sorted(dup))}")
    known = set(ids)
    for i in d["items"]:
        where = i["id"]
        for f in ("kind", "title", "why", "status"):
            if f not in i:
                fail(f"{where}: missing {f}")
        if i["kind"] not in KINDS:
            fail(f"{where}: kind {i['kind']!r} not in {KINDS}")
        if i["status"] not in STATUSES:
            fail(f"{where}: status {i['status']!r} not in {STATUSES}")
        prefix = {"goal": "GOAL-", "feature": "FEAT-", "fix": "FIX-", "issue": "ISSUE-"}[i["kind"]]
        if not where.startswith(prefix):
            fail(f"{where}: a {i['kind']} id starts with {prefix}")
        for ref in i.get("part_of", []):
            if ref not in known or not ref.startswith("GOAL-"):
                fail(f"{where}: part_of {ref} is not a goal")
        for ref in i.get("depends", []):
            if ref not in known:
                fail(f"{where}: depends on unknown {ref}")
        for dv in i.get("devices", []):
            if dv not in devices:
                fail(f"{where}: unknown device {dv}")
        for b in i.get("repos", []):
            if b["repo"] not in repos:
                fail(f"{where}: unknown repo {b['repo']}")
    for dv in d.get("devices", []):
        for ref in dv.get("must", []):
            if ref not in known:
                fail(f"device {dv['id']}: must-have {ref} unknown")


def build(d: dict) -> str:
    tpl = (HERE / "template.html").read_text()
    data = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    meta = d["meta"]
    return (tpl.replace("{{TITLE}}", html.escape(meta["title"]))
               .replace("{{INTRO}}", html.escape(meta.get("intro", "")))
               .replace("{{DATA}}", data))


def main():
    d = load()
    validate(d)
    n = {k: sum(1 for i in d["items"] if i["kind"] == k) for k in KINDS}
    plural = {"goal": "goals", "feature": "features", "fix": "fixes", "issue": "issues"}
    print("build: ok — " + ", ".join(f"{v} {plural[k]}" for k, v in n.items()) + f", {len(d['devices'])} devices")
    if "--check" in sys.argv:
        return
    (HERE / "index.html").write_text(build(d))
    print("build: wrote index.html")


if __name__ == "__main__":
    main()
