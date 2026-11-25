# -*- coding: utf-8 -*-
"""Summarize retained execution outcomes for the 5,014-unit cohort.
The 10 daily-life SC-SYS units are excluded. This diagnostic includes follow-up outcomes;
recompute_final.py provides the paper's first-execution results. No API calls.
Inputs are the bundled artifacts extracted under data/_unpacked."""
import json, os, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JUDGED = ROOT / "pipeline/6_execution_judgment/per_env_judged_results"
DATA = Path(os.environ.get("KAST_DATA", ROOT / "data"))
UNPACK = DATA / "_unpacked"
AG = ["agentdojo_banking", "agentdojo_slack", "agentdojo_travel", "agentdojo_workspace", "agentdyn-dailylife",
      "agentdyn-github", "agentdyn-shopping", "appworld", "cline", "openhands"]
S7 = AG[:7]
TESTED = {"success", "attempted", "quoted_only", "criterion_insufficient", "no_effect", "not_target"}


def is_scsys_dl(r, a):
    return a == "agentdyn-dailylife" and any(s.split("+")[0] == "SC-SYS" for s in r.get("slots", []))


def load_scenario(a, sid):
    p = UNPACK / a / "scenarios" / f"{sid}.json"
    if not p.exists():
        raise SystemExit("data/_unpacked missing -- run `bash reproduce.sh` first.")
    return json.load(open(p))


rows = []
scsys_ids = []
for a in AG:
    for r in map(json.loads, open(JUDGED / f"{a}.jsonl")):
        if is_scsys_dl(r, a):
            scsys_ids.append(r["scenario_id"]); continue
        fx = load_scenario(a, r["scenario_id"]).get("fixed", {})
        r["_a"] = a; r["_tt"] = fx.get("target_tool"); r["_gid"] = fx.get("goal_id")
        r["_nmid"] = sum(1 for z in fx.get("middle_tools", []) if z.get("tool"))
        rows.append(r)

gkey = lambda r: (r["_a"], r["_tt"] if r["goal_kind"] == "tool" else "reply:" + r["end_node"])
tkey = lambda r: (r["_a"], r["_tt"])

print("### SC-SYS daily-life excluded (env==agentdyn-dailylife AND a slot is SC-SYS)")
print("excluded:", len(scsys_ids))
for i in scsys_ids:
    print("   ", i)

print("\n### Retained-outcome stages by environment")
print(f"{'env':22}{'selected':>9}{'gen_fail':>9}{'passed':>8}{'not_deliv':>10}{'evaluated':>10}{'success':>8}")
T = collections.Counter()
for a in AG:
    R = [r for r in rows if r["_a"] == a]
    gf = sum(r["final_outcome"] == "generation_failed" for r in R)
    nd = sum(r["final_outcome"] == "not_delivered" for r in R)
    ev = sum(r["final_outcome"] in TESTED for r in R)
    su = sum(r["final_outcome"] == "success" for r in R)
    passed = len(R) - gf
    print(f"{a:22}{len(R):>9}{gf:>9}{passed:>8}{nd:>10}{ev:>10}{su:>8}")
    T["selected"] += len(R); T["gen_fail"] += gf; T["passed"] += passed; T["not_deliv"] += nd; T["evaluated"] += ev; T["success"] += su
print("-" * 76)
print(f"{'TOTAL':22}{T['selected']:>9}{T['gen_fail']:>9}{T['passed']:>8}{T['not_deliv']:>10}{T['evaluated']:>10}{T['success']:>8}")

oc = collections.Counter(r["final_outcome"] for r in rows)
print("\n### final_outcome distribution (all):", dict(oc.most_common()))

succ = [r for r in rows if r["final_outcome"] == "success"]
tool = [r for r in succ if r["goal_kind"] == "tool"]; reply = [r for r in succ if r["goal_kind"] != "tool"]
path = [r for r in succ if r.get("skeleton_success")]
print(f"\n### Success split: total {len(succ)} = tool {len(tool)} + reply {len(reply)} | intermediate-tool compliance, including empty sequences {len(path)}")
print("    Basis: retained-run outcomes (1,000 successes). The paper's first-execution count includes response-goal adjudication and early achievement; "
      "use recompute_final.py. recompute_firstexec.py provides a diagnostic subtotal.")

all_items = {gkey(r) for r in rows}
succ_items = {gkey(r) for r in succ}
print(f"\n### Goal items: denominator(selected) {len(all_items)} | reached {len(succ_items)}")
obs_items = {gkey(r) for r in succ if r["group"] == "observed"}
rec_items = {gkey(r) for r in succ if r["group"] != "observed"}
print(f"    observed-path reached {len(obs_items)} | recombined-path reached {len(rec_items)} | intersection {len(obs_items & rec_items)}")
print(f"    observed-only {len(obs_items - rec_items)} | recombined-only {len(rec_items - obs_items)}")

gt_all = {tkey(r) for r in tool}
gt_7 = {tkey(r) for r in tool if r["_a"] in S7}
print(f"\n### Goal tools (tool successes, distinct env+tool): all-10 {len(gt_all)} | shared-7 {len(gt_7)}")

out = {"scsys_excluded_ids": scsys_ids,
       "pipeline": {a: {"selected": sum(r["_a"] == a for r in rows),
                        "generation_failed": sum(r["_a"] == a and r["final_outcome"] == "generation_failed" for r in rows),
                        "evaluated": sum(r["_a"] == a and r["final_outcome"] in TESTED for r in rows),
                        "success": sum(r["_a"] == a and r["final_outcome"] == "success" for r in rows)} for a in AG},
       "totals": dict(T), "outcome_counts": dict(oc),
       "success_retry_adopted": len(succ), "tool": len(tool), "reply": len(reply), "path_success": len(path),
       "goal_items_denom": len(all_items), "goal_items_reached": len(succ_items),
       "obs_reached": len(obs_items), "rec_reached": len(rec_items),
       "both": len(obs_items & rec_items), "obs_only": len(obs_items - rec_items), "rec_only": len(rec_items - obs_items),
       "goal_tools_all10": len(gt_all), "goal_tools_shared7": len(gt_7)}
json.dump(out, open(HERE / "outputs" / "recompute_5014.json", "w"), ensure_ascii=False, indent=1)
print("\nwrote outputs/recompute_5014.json")
