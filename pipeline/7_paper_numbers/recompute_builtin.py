# -*- coding: utf-8 -*-
"""Built-in comparison on the adjudicated KAST basis (shared-7 environments): goal tools and ATLAS techniques
reached by KAST vs. by each benchmark's own built-in injection attacks, with common / each-only splits,
Impact/Exfiltration subset, and executed-run totals. No API.

Built-in side reads the benchmarks' own attack traces (data/_unpacked/builtin, unpacked by reproduce.sh),
the per-env static injection items, the case mapping, and the built-in trace->ATLAS map."""
import json, os, glob, gzip, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JUDGED = ROOT / "pipeline/6_execution_judgment/per_env_judged_results"
TC = ROOT / "pipeline/8_technique_coverage"
DATA = Path(os.environ.get("KAST_DATA", ROOT / "data"))
UNPACK = DATA / "_unpacked"
AG = ["agentdojo_banking", "agentdojo_slack", "agentdojo_travel", "agentdojo_workspace", "agentdyn-dailylife",
      "agentdyn-github", "agentdyn-shopping", "appworld", "cline", "openhands"]
S7 = AG[:7]
BENIGN = ("supervisor.", "api_docs.")


def scsys(r, a):
    return a == "agentdyn-dailylife" and any(s.split("+")[0] == "SC-SYS" for s in r.get("slots", []))


def _open(p):
    return gzip.open(p, "rt") if str(p).endswith(".gz") else open(p)


def load_scenario(a, sid):
    p = UNPACK / a / "scenarios" / f"{sid}.json"
    if not p.exists():
        raise SystemExit("data/_unpacked missing -- run `bash reproduce.sh` first.")
    return json.load(open(p))


ALL139 = {t["id"] for t in json.load(open(TC / "atlas_techniques.json"))}
IE = set(json.load(open(TC / "atlas_denominators.json"))["impact_exfiltration_technique_ids"])
# 15 technique IDs excluded by the aggregation filter; see PAPER_NUMBERS.md.
MISLABEL = {"AML.T0080.000", "AML.T0081", "AML.T0110", "AML.T0110.002", "AML.T0048.004", "AML.T0083",
            "AML.T0010.005", "AML.T0047", "AML.T0108", "AML.T0018", "AML.T0018.003", "AML.T0007",
            "AML.T0010", "AML.T0092", "AML.T0082"}
obs = lambda r: ({d["id"] for d in r["observed"] if d["status"] == "effect_observed"} & ALL139) - MISLABEL

_mapp = TC / "trace_atlas_mapping.jsonl.gz"
if not _mapp.exists():
    _mapp = TC / "trace_atlas_mapping.jsonl"
LLM = {r["id"]: r for r in map(json.loads, _open(_mapp))}

T1 = set()
for a in AG:
    fp = DATA / "first_exec" / f"{a}.json"
    if fp.exists():
        T1 |= set(json.load(open(fp)))
EARLY = set(json.load(open(HERE / "early_achievement_ids.json")))

QUOTED_ONLY = set(json.loads((HERE / "reply_adjudication.json").read_text(encoding="utf-8"))["quoted_only"])

# ---- KAST adjudicated success set (shared-7): goal tools + techniques ----
kast_gt7 = set(); kast_tech7 = set(); kast_tech_all = set()
kev_runs = []
for a in AG:
    for r in map(json.loads, open(JUDGED / f"{a}.jsonl")):
        if scsys(r, a):
            continue
        sid = r["scenario_id"]; sc = load_scenario(a, sid)
        gtool = (sc["fixed"].get("goal") or {}).get("tool") or ""
        retry = sid in T1; is_early = (sid in EARLY) and not gtool.startswith(BENIGN)
        first = "not_delivered" if retry else ("success" if (is_early or r["final_outcome"] == "success") else r["final_outcome"])
        if sid in QUOTED_ONLY and first == "success":
            first = "quoted_only"
        tt = sc["fixed"].get("target_tool")
        if first == "success":
            x = LLM.get(sid); o = obs(x) if x else set()
            kast_tech_all |= o
            if a in S7:
                kast_tech7 |= o
                if r["goal_kind"] == "tool":
                    kast_gt7.add((a, tt))
        # cumulative executed runs on shared-7 (first-execution basis): a scenario whose first execution ran
        # but was undelivered counts as an executed run even if a later regeneration failed (so it is kept
        # although final_outcome is generation_failed/not_runnable).
        if a in S7 and (r["final_outcome"] not in ("generation_failed", "not_runnable") or sid in T1):
            kev_runs.append({(a, tt)} if (first == "success" and r["goal_kind"] == "tool") else set())

# ---- built-in (benchmarks' own static injection attacks) ----
BASE = UNPACK / "builtin"
if not (BASE / "AgentDojo").exists():
    raise SystemExit("data/_unpacked/builtin missing -- run `bash reproduce.sh` first.")
CMB = {c["case_id"] for c in map(json.loads, open(TC / "case_mapping.jsonl"))}
DOM = [("AgentDojo", "banking", "agentdojo_banking"), ("AgentDojo", "slack", "agentdojo_slack"),
       ("AgentDojo", "travel", "agentdojo_travel"), ("AgentDojo", "workspace", "agentdojo_workspace"),
       ("AgentDyn", "dailylife", "agentdyn-dailylife"), ("AgentDyn", "github", "agentdyn-github"),
       ("AgentDyn", "shopping", "agentdyn-shopping")]
BL = {}
for r in map(json.loads, _open(TC / "builtin_atlas_mapping.jsonl.gz")):
    BL[r["trace_src"]] = obs(r)

bi_gt7 = set(); bi_tech7 = set(); bev_runs = []; bi_runs = 0; bi_succ = 0
for bench, suite, ag in DOM:
    eff = {x["injection_task"]: x.get("effect_tools") or []
           for x in json.load(open(TC / "builtin_static_items" / f"{ag}.json"))["injection_tasks"]}
    for fp in glob.glob(str(BASE / bench / suite / "*" / "*.json")):
        d = json.load(open(fp)); it = d["injection_task_id"]
        if f"{bench.lower()}__{suite}__{it}" not in CMB:
            continue
        bi_runs += 1; succ = bool(d["security"])
        src = f"{bench}/{suite}/{d['user_task_id']}/{it}.json"
        if succ:
            bi_succ += 1
            for t in eff.get(it, []):
                bi_gt7.add((ag, t))
            if BL.get(src):
                bi_tech7 |= BL[src]
        bev_runs.append({(ag, t) for t in eff.get(it, [])} if succ else set())

print(f"KAST shared-7: goal tools {len(kast_gt7)} | techniques {len(kast_tech7)} | all-10 techniques {len(kast_tech_all)}")
print(f"built-in shared-7: runs {bi_runs} success {bi_succ} | goal tools {len(bi_gt7)} | techniques {len(bi_tech7)}")
print(f"\ngoal tools: common {len(kast_gt7&bi_gt7)} | KAST-only {len(kast_gt7-bi_gt7)} | built-in-only {len(bi_gt7-kast_gt7)}  (KAST {len(kast_gt7)} / built-in {len(bi_gt7)})")
print(f"techniques: common {len(kast_tech7&bi_tech7)} | KAST-only {len(kast_tech7-bi_tech7)} | built-in-only {len(bi_tech7-kast_tech7)} | union {len(kast_tech7|bi_tech7)}  (KAST {len(kast_tech7)} / built-in {len(bi_tech7)})")
print(f"Impact/Exfiltration: KAST {len(kast_tech7&IE)} built-in {len(bi_tech7&IE)} common {len((kast_tech7&IE)&(bi_tech7&IE))} union {len((kast_tech7|bi_tech7)&IE)}")
print(f"\nexecuted-run totals: KAST runs {len(kev_runs)} (final goal tools {len(set().union(*kev_runs)) if kev_runs else 0}) | built-in runs {len(bev_runs)} (final {len(set().union(*bev_runs)) if bev_runs else 0})")
print(f"all-10 techniques KAST {len(kast_tech_all)} Impact/Exfiltration {len(kast_tech_all&IE)}")

json.dump({"kast_gt7": len(kast_gt7), "bi_gt7": len(bi_gt7), "gt_common": len(kast_gt7 & bi_gt7), "gt_kast_only": len(kast_gt7 - bi_gt7), "gt_bi_only": len(bi_gt7 - kast_gt7),
           "kast_tech7": len(kast_tech7), "bi_tech7": len(bi_tech7), "tech_common": len(kast_tech7 & bi_tech7), "tech_kast_only": len(kast_tech7 - bi_tech7), "tech_bi_only": len(bi_tech7 - kast_tech7), "tech_union": len(kast_tech7 | bi_tech7),
           "ie_kast": len(kast_tech7 & IE), "ie_bi": len(bi_tech7 & IE), "ie_union": len((kast_tech7 | bi_tech7) & IE),
           "tech_all10": len(kast_tech_all), "ie_all10": len(kast_tech_all & IE),
           "kast_runs": len(kev_runs), "bi_runs": len(bev_runs), "bi_success": bi_succ},
          open(HERE / "outputs" / "recompute_builtin.json", "w"), ensure_ascii=False, indent=1)
print("\nwrote outputs/recompute_builtin.json")
