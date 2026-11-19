# Thingino changes

A register of the fixes, features and goals carried on top of upstream
[Thingino](https://github.com/themactep/thingino-firmware), [raptor](https://github.com/gtxaspec/raptor),
[raptor-hal](https://github.com/gtxaspec/raptor-hal) and the
[HomeKit daemon](https://github.com/Small6oy/thingino-homekit): what each change is for, which repos, branches
and commits carry it, which cameras need it, and where it stands upstream.

**Page:** https://small6oy.github.io/thingino-changes/

## Kinds

| Kind | Id prefix | What it is |
|---|---|---|
| Goal | `GOAL-` | An outcome built from features and fixes, e.g. native HomeKit on Thingino |
| Feature | `FEAT-` | A capability that stands on its own, possibly across repos, e.g. faac 3.0 |
| Fix | `FIX-` | One bug, normally one repo and one commit |
| Issue | `ISSUE-` | A known bug without a fix yet |

Items link to each other with `part_of` (the goals they serve) and `depends` (what they need).

## Camera baselines

Each `[[devices]]` entry lists the changes (`must`) every build for that camera has to contain. `check.py`
tests a source tree against that list, using commits (any one being an ancestor of the tree's HEAD) or marker
texts (all present in the working tree, so cherry-picks and test patches count). The build tool runs it before
installing a binary on a camera and refuses a build that lacks one, naming the change and why it matters.

```sh
python3 check.py v4 raptor=<tree> raptor-hal=<tree> --binary rvd
```

## Updating

1. Edit `changes.toml`: add or update an item when a fix or feature is made, changes branch or commit, goes
   into a PR, merges, or is tested. Add it to a camera's `must` when every build for that camera needs it.
2. `python3 build.py` validates every reference and builds `index.html`. It refuses to build if the file
   contains anything private (IP addresses, LAN host names, local paths).
3. Commit and push; GitHub Actions publishes the page.
