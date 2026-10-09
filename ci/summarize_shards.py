#!/usr/bin/env python3
"""Aggregate shard JSON from a sharded reproduce-all run.

Usage: python ci/summarize_shards.py SHARD_DIR [MANIFEST]

Exit 0 if every manifest check appears exactly once and all passed.
Exit 1 if any check failed, is missing, is duplicated, or is extra.
"""

import glob
import json
import os
import sys


def load_records(shard_dir):
    paths = sorted(glob.glob(os.path.join(shard_dir, "*.json")))
    paths += sorted(glob.glob(os.path.join(shard_dir, "**", "*.json"), recursive=True))
    # unique, keep order
    seen = set()
    ordered = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    records = []
    files = []
    for p in ordered:
        try:
            data = json.load(open(p))
        except (OSError, json.JSONDecodeError) as e:
            print(f"unreadable shard file {p}: {e}")
            continue
        if not isinstance(data, list):
            print(f"unreadable shard file {p}: not a list")
            continue
        files.append(p)
        for rec in data:
            rec = dict(rec)
            rec["_file"] = os.path.basename(p)
            records.append(rec)
    return files, records


def main(argv):
    if not argv:
        print("usage: python ci/summarize_shards.py SHARD_DIR [MANIFEST]")
        return 2
    shard_dir = argv[0]
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    manifest = argv[1] if len(argv) > 1 else os.path.join(repo, "ci", "reproduce.json")
    expected = [c["name"] for c in json.load(open(manifest))["checks"]]
    files, records = load_records(shard_dir)
    names = [r.get("name") for r in records]
    name_set = set(names)
    missing = [n for n in expected if n not in name_set]
    extra = sorted(name_set - set(expected))
    dups = sorted({n for n in names if n and names.count(n) > 1})
    failures = [r for r in records if not r.get("passed")]
    timed = [r for r in records if isinstance(r.get("seconds"), (int, float))]
    timed.sort(key=lambda r: r["seconds"], reverse=True)

    print(f"shards: {len(files)} files, {len(records)} records, manifest {len(expected)} checks")
    print(f"passed: {len(records) - len(failures)}  failed: {len(failures)}  "
          f"missing: {len(missing)}  extra: {len(extra)}  duplicate: {len(dups)}")
    if timed:
        total = sum(r["seconds"] for r in timed)
        print(f"check-seconds: {total:.1f}  ({total / 60:.1f} min)")
        print("slowest 20:")
        for r in timed[:20]:
            mark = "PASS" if r.get("passed") else "FAIL"
            print(f"  {mark}  {r['name']:<40} {r['seconds']:8.1f}s  {r.get('_file', '')}")
    if failures:
        print("failures:")
        for r in failures:
            print(f"  FAIL  {r.get('name')}  {r.get('detail', '')}")
    if missing:
        print("missing from all shards:")
        for n in missing:
            print(f"  {n}")
    if extra:
        print("extra (not in manifest):")
        for n in extra:
            print(f"  {n}")
    if dups:
        print("duplicated across shards:")
        for n in dups:
            print(f"  {n}")

    if missing or extra or dups or failures:
        print("summary: FAIL")
        return 1
    if len(records) != len(expected):
        print("summary: FAIL (record count mismatch)")
        return 1
    print("summary: all checks present once and passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
