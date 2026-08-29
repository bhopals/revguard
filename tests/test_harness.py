"""Tests for RevGuard's own harness: scoring, dedupe, anchors.

Run from the repo root:  python3 -m pytest tests/ -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.run import dedupe  # noqa: E402
from eval.score import match_case  # noqa: E402
from tools.case_utils import ground_truth, list_cases, resolve_anchor  # noqa: E402


def gt_defect(did="d1", file="a.py", line=10, points=None):
    return {"id": did, "file": file, "line": line,
            "points": points or [(file, line)],
            "category": "correctness", "severity": "major",
            "description": "x"}


def finding(file="a.py", line=10, title="t"):
    return {"file": file, "line": line, "title": title,
            "category": "correctness", "severity": "major"}


class TestMatchCase:
    def test_exact_match(self):
        matched, fps = match_case([gt_defect()], [finding()])
        assert list(matched) == ["d1"] and fps == []

    def test_within_tolerance(self):
        matched, fps = match_case([gt_defect(line=10)], [finding(line=16)])
        assert list(matched) == ["d1"]

    def test_outside_tolerance_is_fp(self):
        matched, fps = match_case([gt_defect(line=10)], [finding(line=17)])
        assert matched == {} and len(fps) == 1

    def test_wrong_file_is_fp(self):
        matched, fps = match_case([gt_defect()], [finding(file="b.py")])
        assert matched == {} and len(fps) == 1

    def test_each_defect_matches_once_and_dup_not_fp(self):
        matched, fps = match_case(
            [gt_defect()], [finding(line=10), finding(line=11)])
        assert list(matched) == ["d1"] and fps == []

    def test_alt_anchor_point_matches(self):
        d = gt_defect(points=[("a.py", 10), ("b.py", 50)])
        matched, fps = match_case([d], [finding(file="b.py", line=52)])
        assert list(matched) == ["d1"]

    def test_two_close_defects_both_match(self):
        gts = [gt_defect("d1", line=10), gt_defect("d2", line=12)]
        matched, fps = match_case(gts, [finding(line=10), finding(line=12)])
        assert set(matched) == {"d1", "d2"} and fps == []

    def test_non_numeric_line_is_fp_not_crash(self):
        matched, fps = match_case([gt_defect()], [finding(line="abc")])
        assert matched == {} and len(fps) == 1


class TestDedupe:
    def test_merges_nearby_same_file(self):
        out = dedupe([finding(line=10), finding(line=12)])
        assert len(out) == 1

    def test_keeps_distinct(self):
        out = dedupe([finding(line=10), finding(line=20),
                      finding(file="b.py", line=10)])
        assert len(out) == 3

    def test_higher_severity_wins(self):
        low = dict(finding(line=10), severity="minor", title="low")
        high = dict(finding(line=11), severity="critical", title="high")
        out = dedupe([low, high])
        assert out[0]["title"] == "high"

    def test_missing_line_does_not_crash(self):
        f = {"file": "a.py", "title": "no line"}
        assert dedupe([f, finding()])


class TestBenchmarkIntegrity:
    def test_every_case_ground_truth_resolves(self):
        for case in list_cases():
            ground_truth(case)  # raises on broken/ambiguous anchors

    def test_ambiguous_anchor_rejected(self, tmp_path):
        (tmp_path / "changed").mkdir()
        (tmp_path / "changed" / "x.py").write_text("dup\ndup\n")
        with pytest.raises(ValueError):
            resolve_anchor(tmp_path, "x.py", "dup")
