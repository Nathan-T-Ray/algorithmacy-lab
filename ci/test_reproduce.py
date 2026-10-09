#!/usr/bin/env python3
"""Unit tests for ci/reproduce.py selection and sharding. No PyPhi; no registered numbers."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("reproduce_gate", os.path.join(HERE, "reproduce.py"))
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


def _fake_checks(n, prefix="c", study=None):
    """n checks. study is a callable(i) -> study dir, or a string, or None to use unique dirs."""
    out = []
    for i in range(n):
        if callable(study):
            d = study(i)
        elif study is None:
            d = f"org_frontier/s{i}"
        else:
            d = study
        mod = d.replace("/", ".")
        out.append({
            "name": f"{prefix}{i}",
            "cmd": f"python -m {mod}.probe",
            "expect": ["ok"],
        })
    return out


class ParseShardTests(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(R.parse_shard("1/16"), (1, 16))
        self.assertEqual(R.parse_shard("16/16"), (16, 16))

    def test_bad(self):
        for spec in ("0/4", "5/4", "a/b", "3", "1/0", "-1/4", "1/", "/4", "1/4/5"):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    R.parse_shard(spec)


class PartitionTests(unittest.TestCase):
    def test_real_manifest_shards_partition(self):
        checks = R.load_checks()
        names = [c["name"] for c in checks]
        for n in (1, 2, 7, 16):
            parts = [R.apply_shard(checks, i, n) for i in range(1, n + 1)]
            union = [c["name"] for part in parts for c in part]
            self.assertEqual(sorted(union), sorted(names), f"N={n} union mismatch")
            self.assertEqual(len(union), len(set(union)), f"N={n} overlap")
            self.assertEqual(len(union), len(names), f"N={n} dropped a check")

    def test_same_study_stays_together(self):
        checks = (
            _fake_checks(3, prefix="a", study="org_frontier/alpha")
            + _fake_checks(2, prefix="b", study="org_frontier/beta")
            + _fake_checks(1, prefix="c", study="org_frontier/gamma")
        )
        for n in (2, 3, 4):
            for i in range(1, n + 1):
                part = R.apply_shard(checks, i, n)
                names = {c["name"] for c in part}
                # all-or-nothing per study
                a = {f"a{k}" for k in range(3)}
                b = {f"b{k}" for k in range(2)}
                self.assertTrue(a.issubset(names) or names.isdisjoint(a), f"alpha split in shard {i}/{n}")
                self.assertTrue(b.issubset(names) or names.isdisjoint(b), f"beta split in shard {i}/{n}")


class ComposeTests(unittest.TestCase):
    def test_shard_after_names(self):
        from io import StringIO
        checks = R.load_checks()
        wanted = [c["name"] for c in checks[:20]]
        buf = StringIO()
        with mock.patch("sys.stdout", buf):
            code = R.main(["--shard", "1/2", "--list", *wanted])
        self.assertEqual(code, 0)
        listed = [ln for ln in buf.getvalue().splitlines() if ln]
        self.assertTrue(listed)
        self.assertTrue(set(listed).issubset(set(wanted)))

    def test_changed_file_then_shard(self):
        from io import StringIO
        checks = R.load_checks()
        target = next(c for c in checks if not c.get("core") and not c.get("slow") and R.study_dir_of(c))
        d = R.study_dir_of(target)
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(d + "/probe.py\n")
            path = f.name
        try:
            buf_all = StringIO()
            with mock.patch("sys.stdout", buf_all):
                self.assertEqual(R.main(["--changed-file", path, "--list"]), 0)
            all_names = [ln for ln in buf_all.getvalue().splitlines() if ln]
            buf_sh = StringIO()
            with mock.patch("sys.stdout", buf_sh):
                self.assertEqual(R.main(["--changed-file", path, "--shard", "1/4", "--list"]), 0)
            sharded = [ln for ln in buf_sh.getvalue().splitlines() if ln]
            self.assertTrue(set(sharded).issubset(set(all_names)))
        finally:
            os.unlink(path)

    def test_bad_shard_exits_2(self):
        from io import StringIO
        for spec in ("0/4", "5/4", "a/b", "3"):
            with self.subTest(spec=spec):
                with mock.patch("sys.stdout", StringIO()):
                    self.assertEqual(R.main(["--shard", spec, "--list"]), 2)


class JsonOutTests(unittest.TestCase):
    def test_json_out_one_record_per_check(self):
        checks = _fake_checks(4, prefix="j", study=lambda i: f"org_frontier/g{i}")
        with mock.patch.object(R, "load_checks", return_value=checks):
            with mock.patch.object(R, "run_check", return_value=(True, "ok")):
                with tempfile.NamedTemporaryFile("w", delete=False) as f:
                    path = f.name
                try:
                    from io import StringIO
                    with mock.patch("sys.stdout", StringIO()):
                        code = R.main(["--json-out", path])
                    self.assertEqual(code, 0)
                    with open(path) as fh:
                        recs = json.load(fh)
                    self.assertEqual([r["name"] for r in recs], [c["name"] for c in checks])
                    for r in recs:
                        self.assertTrue(r["passed"])
                        self.assertIn("seconds", r)
                        self.assertEqual(r["detail"], "ok")
                finally:
                    os.unlink(path)


class DefaultListTests(unittest.TestCase):
    def test_list_full_matches_manifest_order(self):
        checks = R.load_checks()
        # Capture stdout of --list with no other flags
        from io import StringIO
        buf = StringIO()
        with mock.patch("sys.stdout", buf):
            code = R.main(["--list"])
        self.assertEqual(code, 0)
        names = [ln for ln in buf.getvalue().splitlines() if ln]
        self.assertEqual(names, [c["name"] for c in checks])

    def test_shard_1_of_1_is_identity(self):
        checks = R.load_checks()
        # Grouping concatenates same-study checks, so order can change; membership must not.
        self.assertEqual(
            sorted(c["name"] for c in R.apply_shard(checks, 1, 1)),
            sorted(c["name"] for c in checks),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
