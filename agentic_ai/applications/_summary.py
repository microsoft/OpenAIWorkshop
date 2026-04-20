"""Print summary of comparison_reflection_full.json"""
import json, sys
from pathlib import Path

p = Path(sys.argv[1] if len(sys.argv) > 1 else "../evaluations/eval_results/comparison_reflection_full.json")
data = json.loads(p.read_text())

for group in ("single_turn", "multi_turn"):
    if group not in data:
        continue
    g = data[group]
    print(f"\n{'='*80}")
    print(f"{group.upper().replace('_', '-')} ({g['num_tests']} tests)")
    print(f"{'='*80}")
    h = g["headline"]
    print(f"  Input Token Delta:    {h['avg_input_tokens_delta_pct']:+.2f}%")
    print(f"  Cross-Domain Delta:   {h['irrelevant_tool_calls_delta']:+d} calls")
    print(f"  Success-Rate Delta:   {h['success_rate_delta_pct']:+.2f} pp")

    # Aggregate per-test stats
    bs_succ = sum(1 for r in g["results"] if r["baseline"]["success"])
    sk_succ = sum(1 for r in g["results"] if r["skills"]["success"])
    bs_lat = sum(r["baseline"]["latency_ms"] for r in g["results"]) / max(1, len(g["results"]))
    sk_lat = sum(r["skills"]["latency_ms"] for r in g["results"]) / max(1, len(g["results"]))
    bs_tok = sum(r["baseline"]["total_request_tokens"] for r in g["results"]) / max(1, len(g["results"]))
    sk_tok = sum(r["skills"]["total_request_tokens"] for r in g["results"]) / max(1, len(g["results"]))
    bs_inst = sum(r["baseline"]["instruction_size_tokens"] for r in g["results"]) / max(1, len(g["results"]))
    sk_inst = sum(r["skills"]["instruction_size_tokens"] for r in g["results"]) / max(1, len(g["results"]))
    bs_xd = sum(r["baseline"]["irrelevant_tool_calls_count"] for r in g["results"])
    sk_xd = sum(r["skills"]["irrelevant_tool_calls_count"] for r in g["results"])
    bs_cost = sum(r["baseline"]["cost_estimate_usd"] for r in g["results"])
    sk_cost = sum(r["skills"]["cost_estimate_usd"] for r in g["results"])

    print(f"\n  {'Metric':<28} {'Baseline':>12} {'Skills':>12} {'Delta':>10}")
    print(f"  {'-'*64}")
    print(f"  {'Success rate':<28} {bs_succ}/{g['num_tests']:<10} {sk_succ}/{g['num_tests']:<10}")
    print(f"  {'Avg latency (ms)':<28} {bs_lat:>12.0f} {sk_lat:>12.0f} {(sk_lat-bs_lat)/max(1,bs_lat)*100:>+9.1f}%")
    print(f"  {'Avg total tokens':<28} {bs_tok:>12.0f} {sk_tok:>12.0f} {(sk_tok-bs_tok)/max(1,bs_tok)*100:>+9.1f}%")
    print(f"  {'Avg instruction tokens':<28} {bs_inst:>12.0f} {sk_inst:>12.0f} {(sk_inst-bs_inst)/max(1,bs_inst)*100:>+9.1f}%")
    print(f"  {'Total cross-domain calls':<28} {bs_xd:>12d} {sk_xd:>12d} {sk_xd-bs_xd:>+10d}")
    print(f"  {'Total cost ($)':<28} {bs_cost:>12.4f} {sk_cost:>12.4f} {(sk_cost-bs_cost)/max(0.0001,bs_cost)*100:>+9.1f}%")

    # Skill routing breakdown
    skills_used = {}
    for r in g["results"]:
        s = r["skills"].get("domain_detected") or "unknown"
        skills_used[s] = skills_used.get(s, 0) + 1
    print(f"\n  Skill routing distribution:")
    for s, n in sorted(skills_used.items(), key=lambda x: -x[1]):
        print(f"    {s:<20} {n} test(s)")
