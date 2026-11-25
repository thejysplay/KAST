# -*- coding: utf-8 -*-
"""Summarize capability judgments using the two-run intersection.

The released mask retains only Nodes marked active by both mapping runs.
This reference script also reports differences from comparison runs. All four
complete run outputs are required by the script and are not bundled. The public
status-only export documents the released mask separately.
"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
IDS = ["agentdojo_banking", "agentdojo_slack", "agentdojo_travel", "agentdojo_workspace", "agentdyn-dailylife",
       "agentdyn-github", "agentdyn-shopping", "appworld", "cline", "openhands"]
NODES = ["ENT-DI", "ENT-II", "PA-GA", "DAC-UBD", "DAC-CS", "DAC-SRD", "EXE-AT", "EXE-SCU", "EXE-CCE", "SC-SYS", "SC-DAT",
         "PST-MEM", "PST-KB", "PST-CFG", "OT-RG", "OT-ER", "HD-UI"]


def load(sid, tag):
    return {n["node_id"]: n for n in json.loads((H / "out" / f"{sid}.{tag}.json").read_text())["node_mappings"]}


def strict(a, b):
    return "active" if a == b == "active" else "inactive"


final, chg, dis = {}, [], []
for sid in IDS:
    f1, f2 = load(sid, "r4b_run1"), load(sid, "r4b_run2")
    p1, p2 = load(sid, "r4run1"), load(sid, "r4run2")  # Comparison inputs for the diagnostic table only.
    final[sid] = {}
    for n in NODES:
        a, b = f1[n]["status"], f2[n]["status"]
        new = strict(a, b)
        old = strict(p1[n]["status"], p2[n]["status"])
        final[sid][n] = new
        if a != b:
            dis.append((sid, n, a, b))
        if new != old:
            chg.append((sid, n, old, new, a, b, (f1[n].get("reason") or "")[:160]))

json.dump({"rule": "active only if r4b_run1 = r4b_run2 = active", "model": "gemini-2.5-pro", "final": final},
          open(H / "capability_mapping.json", "w"), ensure_ascii=False, indent=1)

M = {"active": "active", "inactive": "inactive"}
L = ["# Capability mapping — Gemini 2.5 Pro, temperature 0, two-run intersection", "",
     "Final = a Node is active only when both runs are active.", "",
     "| Target | " + " | ".join(NODES) + " |", "|---|" + "---|" * len(NODES)]
L += [f"| {sid} | " + " | ".join(M[final[sid][n]] for n in NODES) + " |" for sid in IDS]
L += ["", f"## Two-run disagreements ({len(dis)} cells -> inactive)", "", "| Target | Node | run1 | run2 |", "|---|---|---|---|"] + \
     [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in dis]
L += ["", f"## Differences from the comparison runs ({len(chg)})", "",
      "| Target | Node | before | now | run1 / run2 | reason |", "|---|---|---|---|---|---|"]
L += [f"| {a} | {b} | {c} | {d} | {e} / {f} | {g} |" for a, b, c, d, e, f, g in chg]
print("\n".join(L))
