# -*- coding: utf-8 -*-
"""Inspect a message-length proxy and stored ATLAS labels in successful KAST runs.

The mapper digest retained the first 1,200 characters of each message. This
diagnostic flags messages[*].content values whose txt() conversion exceeds that
limit, then compares stored `attempted` IDs with the `effect_observed` union.
The proxy does not reconstruct the original digest or normalize every trace
layout. Unflagged records are not verified to have complete mapper input.

This conditional analysis does not identify unlabelled techniques, reassess
observed labels, or evaluate built-in mappings. It provides no bound on a new
mapping run and no conclusion that coverage would remain unchanged. Inputs are
read-only. No model API calls or agent executions are performed.

Run `bash ../7_paper_numbers/reproduce.sh` first (unpacks scenarios + traces)."""
import json, os, gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JUDGED = ROOT / "pipeline/6_execution_judgment/per_env_judged_results"
DATA = Path(os.environ.get("KAST_DATA", ROOT / "data"))
UNPACK = DATA / "_unpacked"
AG = ["agentdojo_banking", "agentdojo_slack", "agentdojo_travel", "agentdojo_workspace", "agentdyn-dailylife",
      "agentdyn-github", "agentdyn-shopping", "appworld", "cline", "openhands"]
S7 = AG[:7]
CUT = 1200
MIS = {"AML.T0080.000", "AML.T0081", "AML.T0110", "AML.T0110.002", "AML.T0048.004", "AML.T0083", "AML.T0010.005",
       "AML.T0047", "AML.T0108", "AML.T0018", "AML.T0018.003", "AML.T0007", "AML.T0010", "AML.T0092", "AML.T0082"}
BENIGN = ("supervisor.", "api_docs.")

ALL139 = {t["id"] for t in json.load(open(HERE / "atlas_techniques.json"))}
_m = HERE / "trace_atlas_mapping.jsonl.gz"
LLM = {r["id"]: r for r in map(json.loads, gzip.open(_m, "rt") if _m.exists() else open(HERE / "trace_atlas_mapping.jsonl"))}
T1 = set()
for a in AG:
    fp = DATA / "first_exec" / f"{a}.json"
    if fp.exists():
        T1 |= set(json.load(open(fp)))
PAPER_NUMBERS = ROOT / "pipeline/7_paper_numbers"
EARLY = set(json.load(open(PAPER_NUMBERS / "early_achievement_ids.json")))
QUOTED_ONLY = set(json.loads((PAPER_NUMBERS / "reply_adjudication.json").read_text(encoding="utf-8"))["quoted_only"])


def scsys(r, a):
    return a == "agentdyn-dailylife" and any(s.split("+")[0] == "SC-SYS" for s in r.get("slots", []))


def obs(sid, status):
    r = LLM.get(sid)
    return (({d["id"] for d in r["observed"] if d["status"] == status} & ALL139) - MIS) if r else set()


def txt(c):
    if isinstance(c, list):
        return "\n".join(str(b.get("content", b.get("text", "")) if isinstance(b, dict) else b) for b in c)
    return str(c or "")


def load_scn(a, sid):
    p = UNPACK / a / "scenarios" / f"{sid}.json"
    if not p.exists():
        raise SystemExit("run reproduce.sh first (data/_unpacked missing)")
    return json.load(open(p))


# Build the eligible success set and apply the message-content length proxy.
succ = []
for a in AG:
    for r in map(json.loads, open(JUDGED / f"{a}.jsonl")):
        if scsys(r, a):
            continue
        sid = r["scenario_id"]; sc = load_scn(a, sid)
        gtool = (sc["fixed"].get("goal") or {}).get("tool") or ""
        is_early = (sid in EARLY) and not gtool.startswith(BENIGN)
        first = "nd" if sid in T1 else ("success" if (is_early or r["final_outcome"] == "success") else r["final_outcome"])
        if first != "success" or sid in QUOTED_ONLY:
            continue
        tp = UNPACK / a / "traces" / f"{sid}.json"
        exposed = False
        if tp.exists():
            tr = json.load(open(tp))
            exposed = any(len(txt(m.get("content"))) > CUT for m in tr.get("messages", []) if isinstance(m, dict))
        succ.append((a, sid, sc, exposed))

exposed = [s for s in succ if s[3]]
EO_all = set(); EO7 = set()
for a, sid, sc, ex in succ:
    o = obs(sid, "effect_observed"); EO_all |= o
    if a in S7:
        EO7 |= o
AT_all = set(); AT7 = set()
for a, sid, sc, ex in exposed:
    o = obs(sid, "attempted"); AT_all |= o
    if a in S7:
        AT7 |= o
at_all = sorted(AT_all - EO_all); at7 = sorted(AT7 - EO7)

print(f"eligible successes {len(succ)} | messages[*].content length-proxy flags (> {CUT} chars): {len(exposed)}")
print(f"stored effect_observed union: all-10 {len(EO_all)} | shared-7 {len(EO7)}")
print(f"stored attempted IDs in proxy-flagged successes absent from that union: all-10 {at_all or 'none'} | shared-7 {at7 or 'none'}")
print("Scope: content-field length proxy and existing KAST labels only; no complete digest reconstruction, re-mapping, built-in sensitivity analysis, or bound on new mapping results.")

for scope, atset in [("all-10", at_all), ("shared-7", at7)]:
    for tech in atset:
        print(f"\n[{scope}] {tech} — proxy-flagged successes with this stored attempted label:")
        pool = succ if scope == "all-10" else [s for s in succ if s[0] in S7]
        for a, sid, sc, ex in pool:
            if not ex:
                continue
            if tech not in obs(sid, "attempted"):
                continue
            g = sc["fixed"].get("goal") or {}
            val = str(g.get("value") or g.get("marker") or "")
            tr = json.load(open(UNPACK / a / "traces" / f"{sid}.json"))
            fr = ""
            for m in reversed(tr.get("messages", [])):
                if isinstance(m, dict) and m.get("role") == "assistant" and txt(m.get("content")).strip():
                    fr = txt(m.get("content")); break
            # A prefix location alone does not attribute a label to truncation.
            pos = fr.find(val[:30]) if val else -1
            flag = (
                f"goal-prefix match at index {pos} in final assistant content (length {len(fr)})"
                if pos > CUT
                else (
                    f"goal-prefix match at index {pos} in final assistant content (length {len(fr)})"
                    if pos >= 0
                    else "no goal-prefix match in final assistant content"
                )
            )
            print(f"  {sid} goal={g.get('kind')}/{g.get('end_node')} -> {flag}")
