"""Consolidated story: both pairs, full 30-test runs.

Pair A: single_agent (baseline, 18 tools, monolithic instructions)
        vs single_agent_skills (routed, skill-scoped tools & instructions)
        dataset: eval_dataset.json (30 tests), repeats=1
Pair B: reflection_agent (imperative Primary->Reviewer->Refine loop)
        vs reflection_workflow_agent (declarative workflow graph, same skills)
        dataset: eval_dataset.json (30 tests), repeats=3

Only KPIs valid under the 30-test runs are reported (context/latency/cost/success).
Tool-level KPIs for baselines in these runs are unreliable due to a tracking bug
present at run time, so they are excluded from this comparison.
"""
import json
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).parent / "eval_results"
A = json.loads((ROOT / "comparison_single_full.json").read_text())
B = json.loads((ROOT / "comparison_reflection_determinism.json").read_text())

CONTEXT_KPIS = [
    ("instruction_size_tokens", "Instruction tokens", "{:.0f}"),
    ("tools_exposed_count", "Tools exposed", "{:.1f}"),
    ("tool_schema_tokens", "Tool schema tokens", "{:.0f}"),
    ("input_tokens", "Input tokens", "{:.1f}"),
    ("response_tokens", "Response tokens", "{:.1f}"),
    ("latency_ms", "Latency (ms)", "{:.0f}"),
    ("cost_estimate_usd", "Cost USD", "${:.5f}"),
]


def avg(xs, k):
    return mean(float(x[k]) for x in xs)


def sd(xs, k):
    vals = [float(x[k]) for x in xs]
    return pstdev(vals) if len(vals) > 1 else 0.0


def flatten(section, side):
    """Collect per-test averaged snapshots (over repeats if present)."""
    out = []
    runs_key = f"{side}_runs"
    snap_key = side  # 'baseline' or 'skills'
    for r in section["results"]:
        if runs_key in r and r[runs_key]:
            agg = {}
            for k, _, _ in CONTEXT_KPIS:
                agg[k] = mean(float(rr[k]) for rr in r[runs_key])
            agg["success"] = all(rr["success"] for rr in r[runs_key])
            agg["latency_runs"] = [float(rr["latency_ms"]) for rr in r[runs_key]]
            agg["test_id"] = r["test_id"]
        else:
            s = r[snap_key]
            agg = {k: float(s[k]) for k, _, _ in CONTEXT_KPIS}
            agg["success"] = bool(s["success"])
            agg["latency_runs"] = [float(s["latency_ms"])]
            agg["test_id"] = r["test_id"]
        out.append(agg)
    return out


def report_pair(title, pair, baseline_label, variant_label):
    print("\n" + "#" * 84)
    print(f"#  {title}")
    print("#" * 84)
    for sec_name, sec_key in [("SINGLE-TURN", "single_turn"), ("MULTI-TURN", "multi_turn")]:
        sec = pair[sec_key]
        b = flatten(sec, "baseline")
        v = flatten(sec, "skills")
        n = len(b)
        repeats = sec.get("repeats", 1)
        print(f"\n{sec_name}  (n={n} tests, repeats={repeats})")
        print("-" * 84)
        print(f"{'KPI':<26}{baseline_label:>18}{variant_label:>18}{'Delta':>16}")
        print("-" * 84)
        for k, label, fmt in CONTEXT_KPIS:
            ab, av_ = avg(b, k), avg(v, k)
            delta = f"{(av_-ab)/ab*100:+.1f}%" if ab else f"{av_-ab:+.2f}"
            print(f"{label:<26}{fmt.format(ab):>18}{fmt.format(av_):>18}{delta:>16}")
        # latency stdev aggregated across all runs (not just means)
        all_b_lat = [x for r in b for x in r["latency_runs"]]
        all_v_lat = [x for r in v for x in r["latency_runs"]]
        bsd, vsd = pstdev(all_b_lat), pstdev(all_v_lat)
        delta_sd = (vsd - bsd) / bsd * 100 if bsd else 0
        print(f"{'Latency stdev (ms)':<26}{bsd:>18.0f}{vsd:>18.0f}{delta_sd:>+15.1f}%")
        # success
        bs = sum(1 for x in b if x["success"])
        vs = sum(1 for x in v if x["success"])
        print(f"{'Success (pass / tests)':<26}{bs}/{n:<16}{vs}/{n:<16}"
              f"{(vs-bs)*100/n:>+15.1f} pp")
        # totals
        tb_in = sum(x["input_tokens"] for x in b)
        tv_in = sum(x["input_tokens"] for x in v)
        tb_cost = sum(x["cost_estimate_usd"] for x in b)
        tv_cost = sum(x["cost_estimate_usd"] for x in v)
        tb_lat = sum(x["latency_ms"] for x in b)
        tv_lat = sum(x["latency_ms"] for x in v)
        print(f"  -- Section totals (avg-per-test across repeats) --")
        print(f"     Input tokens:  {tb_in:,.0f}  ->  {tv_in:,.0f}   "
              f"({(tv_in-tb_in)/tb_in*100:+.1f}%)")
        print(f"     Cost USD:      ${tb_cost:.4f}  ->  ${tv_cost:.4f}   "
              f"({(tv_cost-tb_cost)/tb_cost*100:+.1f}%)")
        print(f"     Wall-clock:    {tb_lat/1000:.1f}s  ->  {tv_lat/1000:.1f}s   "
              f"({(tv_lat-tb_lat)/tb_lat*100:+.1f}%)")


report_pair(
    "PAIR A  -  single_agent  vs  single_agent_skills   (30 tests, 1 repeat)",
    A, "Baseline", "Skills",
)
report_pair(
    "PAIR B  -  reflection_agent  vs  reflection_workflow_agent   (30 tests, 3 repeats)",
    B, "Reflection", "Workflow",
)

# Cross-pair headline
print("\n" + "=" * 84)
print("HEADLINE TAKEAWAYS")
print("=" * 84)


def headline(pair, label):
    for key in ("single_turn", "multi_turn"):
        sec = pair[key]
        b = flatten(sec, "baseline")
        v = flatten(sec, "skills")
        in_d = (avg(v, "input_tokens") - avg(b, "input_tokens")) / avg(b, "input_tokens") * 100
        cost_d = (avg(v, "cost_estimate_usd") - avg(b, "cost_estimate_usd")) / avg(b, "cost_estimate_usd") * 100
        lat_d = (avg(v, "latency_ms") - avg(b, "latency_ms")) / avg(b, "latency_ms") * 100
        all_b = [x for r in b for x in r["latency_runs"]]
        all_v = [x for r in v for x in r["latency_runs"]]
        sd_d = (pstdev(all_v) - pstdev(all_b)) / pstdev(all_b) * 100 if pstdev(all_b) else 0
        bs = sum(1 for x in b if x["success"])
        vs = sum(1 for x in v if x["success"])
        print(f"{label:<10} {key:<12} input {in_d:+6.1f}%  "
              f"cost {cost_d:+6.1f}%  lat {lat_d:+6.1f}%  "
              f"lat-stdev {sd_d:+7.1f}%  success {bs}->{vs}")


headline(A, "PAIR A")
headline(B, "PAIR B")
