"""Compare two agent evaluation runs side-by-side.

Reads two eval_results_*.json files produced by run_agent_eval.py and prints
a side-by-side metric comparison. Used to generate the slide-15 style
"Single Agent vs Handoff" table from real data.

Usage:
    uv run python compare_agents.py \
        eval_results/baseline_single_30.json \
        eval_results/baseline_handoff_30.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cases(data: dict[str, Any]) -> list[dict]:
    """Return per-test-case results. Supports both legacy and current schemas."""
    return data.get("results") or data.get("test_case_results") or []


def metric_averages(data: dict[str, Any]) -> dict[str, float]:
    """Use the summary's pre-computed metric_averages when available,
    otherwise fall back to averaging across per-case metrics."""
    summary = data.get("summary") or {}
    pre = summary.get("metric_averages")
    if isinstance(pre, dict) and pre:
        return {k: float(v) for k, v in pre.items() if isinstance(v, (int, float))}
    totals: dict[str, list[float]] = {}
    for case in _cases(data):
        for m in case.get("metrics", []):
            name = m.get("metric_name")
            score = m.get("score")
            if name and score is not None:
                totals.setdefault(name, []).append(float(score))
    return {k: sum(v) / len(v) for k, v in totals.items() if v}


def split_by_turn(data: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Multi-turn cases are conventionally named `multi_*` in this dataset.
    Falls back to an explicit `is_multi_turn` field if present."""
    single, multi = [], []
    for case in _cases(data):
        is_multi = case.get("is_multi_turn")
        if is_multi is None:
            is_multi = str(case.get("test_case_id", "")).startswith("multi_")
        (multi if is_multi else single).append(case)
    return single, multi


def summarise(label: str, data: dict[str, Any]) -> dict[str, Any]:
    s = data.get("summary", {}) or {}
    cases = _cases(data)
    single, multi = split_by_turn(data)
    return {
        "label": label,
        "agent": data.get("agent_name") or s.get("agent_name") or "(see filename)",
        "total_tests": s.get("total_tests") or len(cases),
        "pass_rate": s.get("pass_rate"),
        "avg_score": s.get("average_score"),
        "single_turn": len(single),
        "multi_turn": len(multi),
        "metric_avgs": metric_averages(data),
    }


def render(left: dict[str, Any], right: dict[str, Any]) -> None:
    print("=" * 88)
    print(f"AGENT COMPARISON: {left['label']}  vs  {right['label']}")
    print("=" * 88)

    rows = [
        ("Agent module",   left["agent"],          right["agent"]),
        ("Total tests",    left["total_tests"],    right["total_tests"]),
        ("Single-turn",    left["single_turn"],    right["single_turn"]),
        ("Multi-turn",     left["multi_turn"],     right["multi_turn"]),
        ("Pass rate",      _fmt_pct(left["pass_rate"]),  _fmt_pct(right["pass_rate"])),
        ("Avg score (1-5)", _fmt_num(left["avg_score"]), _fmt_num(right["avg_score"])),
    ]
    _print_rows("Headline", rows)

    metric_keys = sorted(set(left["metric_avgs"]) | set(right["metric_avgs"]))
    metric_rows = []
    for k in metric_keys:
        l = left["metric_avgs"].get(k)
        r = right["metric_avgs"].get(k)
        delta = (r - l) if (l is not None and r is not None) else None
        metric_rows.append((
            k,
            _fmt_num(l),
            _fmt_num(r),
            _fmt_delta(delta),
        ))
    _print_metric_rows(metric_rows)


def _fmt_num(v):
    return f"{v:.2f}" if isinstance(v, (int, float)) else "-"


def _fmt_pct(v):
    if isinstance(v, (int, float)):
        return f"{v * 100:.1f}%" if v <= 1.0 else f"{v:.1f}%"
    return "-"


def _fmt_delta(v):
    if v is None:
        return ""
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}"


def _print_rows(title: str, rows: list[tuple]) -> None:
    print(f"\n{title}")
    print("-" * 88)
    for name, l, r in rows:
        print(f"  {name:<24}  {str(l):<28}  {str(r):<28}")


def _print_metric_rows(rows: list[tuple]) -> None:
    print("\nMetric averages (1-5 scale)")
    print("-" * 88)
    print(f"  {'metric':<28}  {'left':<10}  {'right':<10}  {'delta':<10}")
    for name, l, r, d in rows:
        print(f"  {name:<28}  {l:<10}  {r:<10}  {d:<10}")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    left_path, right_path = sys.argv[1], sys.argv[2]
    left = summarise(Path(left_path).stem, load(left_path))
    right = summarise(Path(right_path).stem, load(right_path))
    render(left, right)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
