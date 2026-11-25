# -*- coding: utf-8 -*-
"""Reference selector with one resource pair per selected skeleton.

This implementation and its report describe a reference selection, not the
released pair-cover selection, which can reuse a skeleton across resource pairs.
The released selected-unit data and per_env_build_report/SELECTION_FINAL.md
provide the counts used in the paper. Required upstream build artifacts are
not all bundled.
"""
import json, collections, sys
from pathlib import Path
H = Path(__file__).resolve().parent; OUT = H / "out_r4"
IDS = sys.argv[1:] or ["agentdojo_banking", "agentdojo_slack", "agentdojo_travel", "agentdojo_workspace", "agentdyn-dailylife",
                       "agentdyn-github", "agentdyn-shopping", "appworld", "cline", "openhands"]
def endn(s): return [x for x in s[-1].split("+") if x != "PA-GA"][0]
def grams(s, n): return {tuple(s[i:i + n]) for i in range(len(s) - n + 1)}
num = lambda sid: int(sid.split("-")[1])
rows = []
for ag in IDS:
    od = OUT / ag; pairs = json.load(open(od / "units_pairs_by_end.json"))
    cand = [r for r in map(json.loads, open(od / "skeleton_status.jsonl")) if r["status"].startswith("candidate") and pairs.get(endn(r["slots"]))]
    obs = sorted([r for r in cand if r["kind"] == "observed"], key=lambda r: num(r["skeleton_id"]))
    un = sorted([r for r in cand if r["kind"] != "observed"], key=lambda r: num(r["skeleton_id"]))
    T3 = set().union(*(grams(r["slots"], 3) for r in un)) if un else set()
    in3 = {g for t in T3 for g in (t[:2], t[1:])}
    B2 = set().union(*(grams(r["slots"], 2) for r in un)) if un else set()
    resid = B2 - in3                                   # 2-grams not contained in any 3-gram
    P = {r["skeleton_id"]: grams(r["slots"], 3) | (grams(r["slots"], 2) & resid) for r in un}
    target = T3 | resid; need = set(target); chosen = []
    while need:
        best = max(un, key=lambda r: (len(P[r["skeleton_id"]] & need), -num(r["skeleton_id"])))
        if not P[best["skeleton_id"]] & need: break
        chosen.append(best); need -= P[best["skeleton_id"]]
    units = []
    for grp, rs in (("observed", obs), ("unobserved", chosen)):
        ui, ug = collections.Counter(), collections.Counter()
        for r in rs:
            i, g = min(pairs[endn(r["slots"])], key=lambda q: (ui[q[0]], ug[q[1]], q[0], q[1]))
            ui[i] += 1; ug[g] += 1
            units.append({"group": grp, "skeleton_id": r["skeleton_id"], "slots": r["slots"], "length": r["length"],
                          "observed_in": r["observed_in"], "input_id": i, "goal_id": g})
    (od / "units_selected_final.json").write_text(json.dumps(units, ensure_ascii=False, indent=1))
    sel2 = set().union(*(grams(r["slots"], 2) for r in chosen)) if chosen else set()
    n3 = T3
    rows.append(dict(agent=ag, eligible=len(cand), obs=len(obs), un_elig=len(un), un=len(chosen),
                     bi=f"{len(sel2 & B2)}/{len(B2)}", resid=len(resid), tri=f"{len(n3 - need)}/{len(n3)}",
                     inp=f"{len({u['input_id'] for u in units})}/{len(json.load(open(od / 'inputs.json')))}",
                     gl=f"{len({u['goal_id'] for u in units})}/{len(json.load(open(od / 'goals.json')))}", total=len(units)))
    print(rows[-1], flush=True)
L = ["# Reference selection — one resource pair per selected skeleton", "", "This reference report is separate from the released pair-cover selection.", "",
     "| Environment | Eligible skeletons | Observed | Unobserved eligible | Unobserved selected | 3-gram | Residual 2-gram | 2-gram (result) | Injection points used | Result tools used | Selected units |", "|---|---:|---:|---:|---:|---|---:|---|---|---|---:|"]
L += [f"| {r['agent']} | {r['eligible']:,} | {r['obs']} | {r['un_elig']:,} | {r['un']} | {r['tri']} | {r['resid']} | {r['bi']} | {r['inp']} | {r['gl']} | {r['total']} |" for r in rows]
L += ["", f"Total: {sum(r['total'] for r in rows)} (observed {sum(r['obs'] for r in rows)} + unobserved {sum(r['un'] for r in rows)})"]
(OUT / "SELECTION_FINAL.md").write_text("\n".join(L) + "\n"); print("\n".join(L))
