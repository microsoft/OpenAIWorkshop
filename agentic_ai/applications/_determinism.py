"""Determinism analysis from saved eval results.

Determinism = how close the agent's actual tool calls match the expected pipeline.
- For workflow agents we expect a deterministic sequence (skill-filtered tools only).
- For free-form agents we expect more variance.

Metrics:
1. Required-tool coverage: % of required_tools actually called
2. Tool-set match (Jaccard): overlap with expected_tools
3. Out-of-set tool calls: tools called that weren't in expected_tools (potential noise)
4. Pipeline conformance: did the workflow follow Primary -> Reviewer -> Refine?
"""
import json
from pathlib import Path
from statistics import mean

# Load the saved comparison + the original eval dataset (to recover expected_tools)
results = json.loads(Path("../evaluations/eval_results/comparison_reflection_full.json").read_text())
dataset = json.loads(Path("../evaluations/eval_dataset.json").read_text())
expected_by_id = {t["id"]: t for t in dataset["test_cases"]}


def jaccard(a, b):
    A, B = set(a), set(b)
    if not A and not B:
        return 1.0
    return len(A & B) / max(1, len(A | B))


def analyze(group_name, group_data):
    print(f"\n{'='*80}")
    print(f"DETERMINISM ANALYSIS — {group_name.upper()}")
    print(f"{'='*80}")

    rows = []
    for r in group_data["results"]:
        tid = r["test_id"]
        expected = expected_by_id.get(tid, {})
        exp_tools = set(expected.get("expected_tools", []))
        req_tools = set(expected.get("required_tools", []))

        for variant in ("baseline", "skills"):
            actual = r[variant]["tool_call_names"]
            actual_set = set(actual)

            # Required-tool coverage (% of required actually called)
            req_cov = len(actual_set & req_tools) / max(1, len(req_tools)) if req_tools else 1.0
            # Jaccard with expected
            j = jaccard(actual_set, exp_tools) if exp_tools else 1.0
            # Tools called that weren't in expected (noise / hallucinated tool use)
            noise = len(actual_set - exp_tools) if exp_tools else 0
            # Cross-domain (already computed)
            xd = r[variant]["irrelevant_tool_calls_count"]

            rows.append({
                "test_id": tid,
                "variant": variant,
                "tool_count": len(actual),
                "req_coverage": req_cov,
                "jaccard": j,
                "noise_count": noise,
                "cross_domain": xd,
            })

    # Aggregate per variant
    for variant in ("baseline", "skills"):
        v = [r for r in rows if r["variant"] == variant]
        print(f"\n  {variant.upper()}:")
        print(f"    Avg tools called per query : {mean(r['tool_count'] for r in v):.2f}")
        print(f"    Required-tool coverage     : {mean(r['req_coverage'] for r in v)*100:.1f}%")
        print(f"    Jaccard vs expected_tools  : {mean(r['jaccard'] for r in v):.2f}")
        print(f"    Avg out-of-expected tools  : {mean(r['noise_count'] for r in v):.2f}")
        print(f"    Total cross-domain calls   : {sum(r['cross_domain'] for r in v)}")

    # Show test cases where the two agents differ in tool sets
    diffs = []
    for r in group_data["results"]:
        b = set(r["baseline"]["tool_call_names"])
        s = set(r["skills"]["tool_call_names"])
        if b != s:
            diffs.append((r["test_id"], sorted(b - s), sorted(s - b)))
    print(f"\n  Cases where tool sets differ: {len(diffs)}/{len(group_data['results'])}")
    for tid, only_b, only_s in diffs[:5]:
        print(f"    {tid}")
        if only_b:
            print(f"      baseline-only tools: {only_b}")
        if only_s:
            print(f"      skills-only   tools: {only_s}")


for grp in ("single_turn", "multi_turn"):
    if grp in results:
        analyze(grp, results[grp])
