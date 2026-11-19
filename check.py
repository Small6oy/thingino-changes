#!/usr/bin/env python3
"""Check that source trees contain every change a camera's builds must have (changes.toml [[devices]] must).

    check.py <device> <repo>=<path> [<repo>=<path> ...] [--host user@host] [--binary rvd]

<device>  a [[devices]] id, or a short alias: v3, v4
<path>    the tree the binary was built from; with --host, a path on that host (git/grep run there over ssh)
--binary  only check blocks that apply to this binary (blocks without `binaries` always apply)

For each must-have item with a block for one of the given repos, the tree passes if any listed commit is an
ancestor of its HEAD, or every listed marker text is in the working tree (covers cherry-picks and uncommitted
test patches). Exit 0 when all pass, 1 when something is missing (printed with why it matters), 2 on usage
errors. Items whose repo isn't among the given trees are skipped, so `xb raptor` checks raptor + raptor-hal
and `xb rhkd` checks thingino-homekit. Override for a deliberate test: XB_ALLOW_MISSING=1 (tools/xb).
"""
from __future__ import annotations

import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALIASES = {"v3": "wyze-cam-v3", "v4": "wyze-cam-v4"}


def load():
    with open(HERE / "changes.toml", "rb") as f:
        return tomllib.load(f)


def run(host: str | None, cmd: list[str]) -> subprocess.CompletedProcess:
    if host:
        return subprocess.run(["ssh", "-o", "BatchMode=yes", host, " ".join(shlex.quote(c) for c in cmd)],
                              capture_output=True, text=True)
    return subprocess.run(cmd, capture_output=True, text=True)


def has_commit(host, path, sha) -> bool:
    return run(host, ["git", "-C", path, "merge-base", "--is-ancestor", sha, "HEAD"]).returncode == 0


def has_marker(host, path, m) -> bool:
    return run(host, ["grep", "-qF", "--", m["text"], f"{path}/{m['file']}"]).returncode == 0


def main(argv: list[str]) -> int:
    host = binary = None
    if "--binary" in argv:
        i = argv.index("--binary")
        binary = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if "--host" in argv:
        i = argv.index("--host")
        host = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    data = load()
    dev_id = ALIASES.get(argv[0], argv[0])
    dev = next((d for d in data["devices"] if d["id"] == dev_id), None)
    if not dev:
        print(f"check: unknown device {argv[0]}", file=sys.stderr)
        return 2
    trees = dict(a.split("=", 1) for a in argv[1:])
    items = {i["id"]: i for i in data["items"]}
    missing, ok, unchecked = [], [], []
    for iid in dev.get("must", []):
        item = items.get(iid)
        if not item:
            print(f"check: {dev_id} must-have {iid} is not in changes.toml", file=sys.stderr)
            return 2
        for blk in item.get("repos", []):
            path = trees.get(blk["repo"])
            if not path or (binary and blk.get("binaries") and binary not in blk["binaries"]):
                continue
            commits, markers = blk.get("commits", []), blk.get("markers", [])
            if not commits and not markers:
                unchecked.append((iid, blk["repo"]))
                continue
            found = any(has_commit(host, path, c) for c in commits) or \
                (markers and all(has_marker(host, path, m) for m in markers))
            (ok if found else missing).append((item, blk))
    name = dev.get("name", dev_id)
    for item, blk in ok:
        print(f"  ok       {item['id']} ({blk['repo']})")
    for iid, repo in unchecked:
        print(f"  unchecked {iid} ({repo}: no commits or markers listed)")
    for item, blk in missing:
        print(f"  MISSING  {item['id']} ({blk['repo']}, e.g. branch {blk.get('branch', '?')} "
              f"{' / '.join(blk.get('commits', []))}): {item['title']}")
        print(f"           why: {item['why']}")
    if missing:
        print(f"check: the tree lacks {len(missing)} change(s) every {name} build must have.", file=sys.stderr)
        return 1
    print(f"check: {name}: all {len(ok)} must-have change(s) for these trees present.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
