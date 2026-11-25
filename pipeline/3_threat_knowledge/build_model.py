# -*- coding: utf-8 -*-
"""Compare provisional event graphs and path sets from source-case annotations.

Authority labels require supporting evidence. Incidental delivery records and
decisions to follow an instruction are excluded as separate behaviors here.
The released graph and path set are in transition_graph.json and skeletons.json."""
import json, collections, itertools, glob
from pathlib import Path
R = Path(__file__).resolve().parents[1]
OUT = R / "9_recoding/out/r4_model"
SEQ = json.load(open(R / "4_sequences/out/attack_sequences.json"))["cases"]
SK3 = json.load(open(R / "5_threat_knowledge/out/skeletons.json"))
G3 = json.load(open(R / "4_sequences/out/transition_graph.json"))
P = "+PA-GA"

def nodes_of(slot):
    slot = slot.replace("EXE-?", "EXE-AT").replace("DAC-?", "DAC-UBD")      # C4: when the kind is not stated, a general Node (EXE-AT general tool call · DAC-UBD general information access, detail unconfirmed)
    parts = slot.split("+"); pa = "PA-GA" in parts
    base = [p for p in parts if p != "PA-GA"]
    return [b + (P if pa and b.startswith("EXE") else "") for b in base]

# Modified paths: (case, branch prefix) → event list. An event = (Node list, step, note). "|" = break the segment due to unconfirmed order
E = lambda nodes, step, note="": {"nodes": nodes, "step": step, "note": note}
CUT = "|"
OVR = {
 ("CS0016", "A"): [E(["ENT-DI"], "S06"), E(["OT-RG"], "S06", "Code generation (GPT 1)"), E(["EXE-CCE" + P], "S06"),
                  E(["DAC-CS", "DAC-SRD"], "S06", "Same retrieval event (P7)"), E(["OT-RG"], "S06", "Provide the result")],
 ("CS0021", "A"): [E(["ENT-II"], "S02"), E(["OT-RG", "DAC-UBD"], "S03", "Use conversation content in the URL (GPT 1)"), E(["OT-ER"], "S04")],
 ("CS0021", "B"): [E(["ENT-II"], "S02"), E(["EXE-AT" + P], "S05", "IPI — called in the victim user's session (PA-GA criterion 10/21)")],
 ("CS0024", "-"): [E(["ENT-II"], "S02"), CUT, E(["PST-KB"], "S02", "Ordering between reading and storage unconfirmed (P6)"), E(["ENT-II"], "S03"),
                  E(["OT-RG", "DAC-UBD"], "S04", "S05 basis: email · address · phone number in the output (GPT 1)")],
 ("CS0045", "-"): [E(["ENT-II"], "S04"), E(["EXE-SCU" + P], "S06"), E(["HD-UI"], "S06", "User approval request before execution — [action unconfirmed] (GPT 1)"),
                  E(["EXE-CCE" + P], "S08"), E(["DAC-CS"], "S09"), E(["OT-ER"], "S09")],
 ("CS0048", "A"): [E(["ENT-DI"], "S04"), E(["EXE-SCU" + P], "S04", "Reading the file (SOUL.md) = tool use (C2a) — whether it is a general-purpose file interface is confirmed at re-judgment · DPI Service authority · no execution (CCE) description"), E(["DAC-SRD"], "S04"), E(["OT-RG"], "S04")],
 ("CS0051", "-"): [E(["ENT-II"], "S09"), E(["EXE-SCU" + P], "S12"), E(["EXE-CCE" + P], "S12"), E(["PST-CFG"], "S13"), E(["ENT-II"], "S14"),
                  E(["EXE-AT" + P], "S16", "IPI — the Agent on the victim's computer fetches it on their behalf (PA-GA criterion 10/21)"), E(["ENT-II"], "S16"), E(["EXE-SCU" + P], "S16"), E(["EXE-CCE" + P], "S16")],
 ("CS0053", "-"): [E(["PST-CFG"], "S04"), E(["EXE-AT"], "S06", "The user-requested call activates the malicious implementation — included in the path; not attack-induced, so no PA-GA (GPT 1, P10)"),
                  E(["EXE-CCE" + P], "S06"), E(["OT-ER", "DAC-UBD"], "S07", "Process · exfiltrate the email content (GPT 1)")],
 ("CS0054", "-"): [E(["PST-CFG"], "S02"), E(["ENT-II"], "S04"), E(["EXE-SCU" + P], "S06"), E(["DAC-CS"], "S10", "description: credentials exfiltrated (GPT 1)"),
                  E(["EXE-AT" + P], "S10", "Remote MCP call — EXE-AT generic tool call · details unconfirmed (C2a · C4)"), E(["OT-ER"], "S10")],
 ("CS0055", "-"): [E(["ENT-II"], "S03"), E(["EXE-SCU" + P], "S06", "Click a button"), E(["EXE-CCE" + P], "S06", "Execute JavaScript"),
                  E(["EXE-SCU" + P], "S06", "Open the terminal · paste"), E(["EXE-CCE" + P], "S06", "Execute a command"), E(["EXE-CCE" + P], "S07", "Run the downloaded script (GPT 1)")],
 ("CS0064", "A"): [E(["PST-CFG"], "S05"), E(["EXE-CCE" + P], "S06", "Run the poisoned template logic (GPT 1) · the config-residue path = the victim user's environment (PA-GA criterion 10/21)"), E(["ENT-II"], "S07"), E(["OT-RG"], "S08")],
 ("CS0064", "B"): [E(["PST-CFG"], "S05"), E(["EXE-CCE" + P], "S06"), E(["ENT-II"], "S07"),
                  E(["EXE-AT" + P], "S11", "S10 is INSTR (C5) · send tool — EXE-AT generic tool call · details unconfirmed (C4)"), E(["OT-ER", "DAC-UBD"], "S11", "Transmit sensitive information — DAC-UBD general information access · details unconfirmed (C4)")],
 ("CS0066", "A"): [E(["ENT-II"], "S04"), E(["EXE-AT" + P], "S06"), E(["DAC-UBD"], "S07"), E(["EXE-AT" + P], "S09", "Links S08's URL selection · opening · IPI request under the victim's account (PA-GA criterion 10/21)"), E(["OT-ER"], "S09")],
 ("CS0066", "C"): [E(["ENT-II"], "S04"), E(["EXE-AT" + P], "S11", "S06 is supplementary evidence for this call — no self-link (GPT 3)"), E(["DAC-UBD"], "S11"),
                  E(["OT-RG"], "S12"), E(["EXE-AT" + P], "S12"), E(["OT-ER"], "S12")],
}
NOTES = {"CS0037": "Main attack entry ENT-II is recorded not as S06 (a reconnaissance interaction) but on the basis of the description · the post-S11 action (GPT 3) — the path shape is the same",
         "CS0038": "Link the actual S04 call as the PST-MEM basis (GPT 4)", "CS0039": "Does not add S07 SC-DAT (decision 1A) · links S04 · S05 as the PA-GA basis (GPT 4)",
         "CS0067": "S08 DAC-CS · DAC-SRD same event (P7, automatic)"}
# CS0026 S12 has both OT-RG and HD-UI on the same event.
MERGE = {("CS0026", "S12", "OT-RG", "HD-UI")}

paths = []; used = set()
for cs, v in sorted(SEQ.items()):
    for p in v["paths"]:
        lab = (p.get("label") or "-").split(" ")[0]
        if (cs, lab) in OVR:
            raw = OVR[(cs, lab)]; used.add((cs, lab)); src = "Modified"
        else:
            raw = [E(nodes_of(x["node"]), x["atlas_step"]) for x in p["sequence"]]; src = "Automatic conversion"
            for i in range(len(raw) - 1, 0, -1):     # merge the same event
                a, b = raw[i - 1], raw[i]
                if (cs, a["step"], a["nodes"][0], b["nodes"][0]) in MERGE:
                    a["nodes"] = a["nodes"] + b["nodes"]; a["note"] = "Same event (P3 · P7)"; del raw[i]
        segs, cur = [], []
        for x in raw:
            if x == CUT: segs.append(cur); cur = []
            else: cur.append(dict(x))
        segs.append(cur)
        k = 0
        for sg in segs:
            for ev in sg: k += 1; ev["id"] = f"{cs}-{lab}-E{k}"
        paths.append({"case": cs, "branch": lab, "source": src, "segments": segs, "note": NOTES.get(cs, "")})
assert used == set(OVR), set(OVR) - used

EV = collections.defaultdict(list)
for p in paths:
    for sg in p["segments"]:
        for a, b in zip(sg, sg[1:]):
            for x, y in itertools.product(a["nodes"], b["nodes"]):
                if "?" in x or "?" in y: continue
                EV[(x, y)].append({"case": p["case"], "branch": p["branch"], "from": a["id"], "to": b["id"], "step_from": a["step"], "step_to": b["step"],
                                   "order": "Same step" if a["step"] == b["step"] else "Different step"})
K = sorted(EV); V = sorted({n for e in K for n in e})

obs = []
for p in paths:
    for j, sg in enumerate(p["segments"]):
        for combo in itertools.product(*[ev["nodes"] for ev in sg]):
            obs.append((p["case"], p["branch"], tuple(combo), j == 0, j == len(p["segments"]) - 1))
STARTS = sorted({q[0] for *_, q, f, _ in [(o[0], o[1], o[2], o[3], o[4]) for o in obs] if f and "?" not in q[0]})
ENDS = sorted({q[-1] for _, _, q, _, l in obs if l and "?" not in q[-1]})
MAX_LEN = max(len(q) for _, _, q, _, _ in obs); MIN_LEN = 2
CAP = collections.Counter()
for _, _, q, _, _ in obs:
    for s, n in collections.Counter(x for x in q if "?" not in x).items(): CAP[s] = max(CAP[s], n)
ADJ = collections.defaultdict(list)
for a, b in K: ADJ[a].append(b)
skel = []
def walk(path, cnt):
    if len(path) >= MIN_LEN and path[-1] in ENDS: skel.append(tuple(path))
    if len(path) == MAX_LEN: return
    for nxt in sorted(ADJ.get(path[-1], [])):
        if cnt[nxt] < CAP[nxt]:
            cnt[nxt] += 1; path.append(nxt); walk(path, cnt); path.pop(); cnt[nxt] -= 1
for s in STARTS: walk([s], collections.Counter({s: 1}))
skel = sorted(set(skel), key=lambda q: (len(q), q)); sset = set(skel)
full = {q for _, _, q, f, l in obs if f and l and not any("?" in x for x in q)}
pres = sum(1 for q in full if q in sset)

SKID = {s["id"]: s for s in SK3["skeletons"]}; Kset = set(K)
def grounded(slots):
    seq = [nodes_of(s) for s in slots]
    return all(any((a, b) in Kset for a in x for b in y) for x, y in zip(seq, seq[1:]))
cmp = collections.Counter(); lost_by = collections.Counter()
K3 = {(e["from"], e["to"]) for e in G3["edges"]}
K3n = {(x, y) for a, b in K3 for x in nodes_of(a) for y in nodes_of(b)}
for f in glob.glob(str(R / "7_scenario_generation/out_r3c/*/FINAL_RESULTS.jsonl")):
    for l in open(f):
        r = json.loads(l); sl = SKID[r["scenario_id"].split("__")[-1]]["slots"]; g = grounded(sl)
        cmp["units"] += 1; cmp["grounded"] += g
        if r["final_outcome"] == "success": cmp["success"] += 1; cmp["success_grounded"] += g
        if not g:
            seq = [nodes_of(s) for s in sl]
            for x, y in zip(seq, seq[1:]):
                if not any((a, b) in Kset for a in x for b in y): lost_by[f"{x[0]} → {y[0]}"] += 1
added = sorted(set(K) - K3n); removed = sorted(K3n - set(K))
stats = {"V": len(V), "K": len(K), "skeletons": len(skel), "start_ENT-II": sum(1 for q in skel if q[0] == "ENT-II"),
         "observed_full": len(full), "observed_preserved": pres, **{f"existing_{k}": v for k, v in cmp.items()}}
json.dump({"status": "r4 v3 — GPT review (10/20) + decisions (10/20 · 10/21). Before checking the re-judgment worksheet", "V": V,
           "K": [{"from": a, "to": b, "cases": sorted({x["case"] for x in EV[(a, b)]}), "evidence": EV[(a, b)]} for a, b in K],
           "rules": {"starts": STARTS, "ends": ENDS, "min_len": MIN_LEN, "max_len": MAX_LEN, "repeat_caps": dict(sorted(CAP.items()))},
           "stats": stats, "paths": paths}, open(OUT / "MODEL_r4_v3.json", "w"), ensure_ascii=False, indent=1)
json.dump([{"id": f"R4SK{i:05d}", "nodes": list(q), "length": len(q), "kind": "observed" if q in full else "recombined"} for i, q in enumerate(skel, 1)],
          open(OUT / "skeletons_r4_v3.json", "w"), ensure_ascii=False)
md = ["# Comparison of provisional graph summaries", "", "The table reports intermediate coding results.", "",
      "| Item | r3 | r4 v3 |", "|---|---|---|",
      f"| Graph vertices | 17 cells | {len(V)} Nodes |", f"| 2-gram | {len(K3)} | {len(K)} |", f"| Skeletons | {len(SK3['skeletons']):,} | {len(skel):,} |",
      f"| ENT-II-start skeletons | 6,906 | {stats['start_ENT-II']:,} |", f"| Observed-path reproduction | 29/29 | {pres}/{len(full)} |",
      f"| Existing scenarios keeping grounding | 1,347/1,347 | {cmp['grounded']:,}/{cmp['units']:,} |", f"| Existing successes keeping grounding | 224/224 | {cmp['success_grounded']}/{cmp['success']} |", "",
      "Vertices: " + ", ".join(V), "", "Newly added 2-grams: " + (", ".join(f"{a} → {b}" for a, b in added) or "none"), "",
      "Removed 2-grams: " + (", ".join(f"{a} → {b}" for a, b in removed) or "none"), "",
      "Edges where existing scenarios lost grounding (# scenarios): " + ", ".join(f"{k} {v}" for k, v in lost_by.most_common()), "",
      f"Rules: start {STARTS} · end {ENDS} · length {MIN_LEN}~{MAX_LEN} · repeat caps " + str({k: v for k, v in sorted(CAP.items()) if v > 1}) + " (others 1)"]
(OUT / "COMPARE_r3_r4_v3.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
