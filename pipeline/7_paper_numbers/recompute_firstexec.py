# -*- coding: utf-8 -*-
"""Calculate diagnostic first-execution and retained-run aggregates for the 5,014-unit cohort.
IDs in the first-execution-undelivered manifest are assigned not_delivered in the
first-execution subtotal. This script does not apply early-achievement annotations;
recompute_final.py provides the paper's primary results. The retained-run diagnostic
includes follow-up outcomes. No API calls."""
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


def scsys(r, a):
    return a == "agentdyn-dailylife" and any(s.split("+")[0] == "SC-SYS" for s in r.get("slots", []))


def load_scenario(a, sid):
    p = UNPACK / a / "scenarios" / f"{sid}.json"
    if not p.exists():
        raise SystemExit("data/_unpacked missing -- run `bash reproduce.sh` first.")
    return json.load(open(p))


# T1 = scenarios whose FIRST execution was undelivered
T1 = set()
for a in AG:
    fp = DATA / "first_exec" / f"{a}.json"
    if fp.exists():
        T1 |= set(json.load(open(fp)))
print("first-execution-undelivered manifest IDs:", len(T1))

rows = []
for a in AG:
    for r in map(json.loads, open(JUDGED / f"{a}.jsonl")):
        if scsys(r, a):
            continue
        fx = load_scenario(a, r["scenario_id"]).get("fixed", {})
        r["_a"] = a; r["_tt"] = fx.get("target_tool")
        r["_retry"] = r["scenario_id"] in T1
        r["_first"] = "not_delivered" if r["_retry"] else r["final_outcome"]
        rows.append(r)

gkey = lambda r: (r["_a"], r["_tt"] if r["goal_kind"] == "tool" else "reply:" + r["end_node"])
tkey = lambda r: (r["_a"], r["_tt"])


def metrics(outcome_field, label):
    succ = [r for r in rows if r[outcome_field] == "success"]
    tool = [r for r in succ if r["goal_kind"] == "tool"]; reply = [r for r in succ if r["goal_kind"] != "tool"]
    path = [r for r in succ if r.get("skeleton_success")]
    items = {gkey(r) for r in succ}
    obs = {gkey(r) for r in succ if r["group"] == "observed"}; rec = {gkey(r) for r in succ if r["group"] != "observed"}
    gt7 = {tkey(r) for r in tool if r["_a"] in S7}
    oc = collections.Counter(r[outcome_field] for r in rows)
    print(f"\n### {label}")
    print(f"  success {len(succ)} (tool {len(tool)} / reply {len(reply)}) | skeleton-ok records {len(path)}")
    print(f"  goal items reached {len(items)}/689 | observed {len(obs)} recombined {len(rec)} "
          f"intersection {len(obs&rec)} observed-only {len(obs-rec)} recombined-only {len(rec-obs)}")
    print(f"  goal tools shared-7 {len(gt7)}")
    return {"success": len(succ), "tool": len(tool), "reply": len(reply), "skel_ok": len(path),
            "items": len(items), "obs": len(obs), "rec": len(rec), "both": len(obs & rec),
            "obs_only": len(obs - rec), "rec_only": len(rec - obs), "goal_tools_7": len(gt7), "outcome_counts": dict(oc)}


print("\nselection units:", len(rows), "| retried_undelivered:", sum(r["_retry"] for r in rows))
pri = metrics("_first", "Diagnostic first-execution subtotal (early-achievement annotations not applied)")
sec = metrics("final_outcome", "Diagnostic retained-run aggregate (1,000 successes)")

out = {"T1_count": len(T1), "selected": len(rows), "retried_undelivered": sum(r["_retry"] for r in rows),
       "primary_firstexec": pri, "secondary_retry": sec}
json.dump(out, open(HERE / "outputs" / "recompute_firstexec.json", "w"), ensure_ascii=False, indent=1)
print("\nwrote outputs/recompute_firstexec.json")
