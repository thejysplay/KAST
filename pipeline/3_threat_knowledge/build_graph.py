# -*- coding: utf-8 -*-
"""Compare graph summaries from intermediate event-coding records.

Events with uncertain order delimit segments. The tables summarize the supplied
coding versions. The reviewed graph and path set are published separately in
transition_graph.json and skeletons.json."""
import json, collections, itertools, glob
from pathlib import Path
R = Path(__file__).resolve().parents[1]; OUT = R / "9_recoding/out/r4_coding"
D = json.load(open(OUT / "R4_CODING_DRAFT.json"))
SK3 = json.load(open(R / "5_threat_knowledge/out/skeletons.json"))
G3 = json.load(open(R / "4_sequences/out/transition_graph.json"))
V3 = json.load(open(R / "9_recoding/out/r4_model/MODEL_r4_v3.json"))
lab = lambda n: n["code"] + ("+PA-GA" if n.get("pa") else "")

EV = collections.defaultdict(list); segs_all = []
for p in D["paths"]:
    segs, cur = [], []
    for e in p["events"]:
        if e["order"][0] == "cut" and cur: segs.append(cur); cur = []
        cur.append(e)
    segs.append(cur); segs_all.append((p, segs))
    for sg in segs:
        for a, b in zip(sg, sg[1:]):
            for x, y in itertools.product(a["nodes"], b["nodes"]):
                EV[(lab(x), lab(y))].append({"case": p["case"], "branch": p["branch"], "from": a["id"], "to": b["id"], "order": b["order"][0], "basis": b["order"][1][:160]})
K = sorted(EV); V = sorted({v for e in K for v in e})
obs = []
for p, segs in segs_all:
    for j, sg in enumerate(segs):
        for combo in itertools.product(*[[lab(n) for n in e["nodes"]] for e in sg]):
            obs.append((p["case"], combo, j == 0, j == len(segs) - 1))
STARTS = sorted({q[0] for _, q, f, _ in obs if f}); ENDS = sorted({q[-1] for _, q, _, l in obs if l})
MAX_LEN = max(len(q) for _, q, _, _ in obs); MIN_LEN = 2
CAP = collections.Counter()
for _, q, _, _ in obs:
    for s, n in collections.Counter(q).items(): CAP[s] = max(CAP[s], n)
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
full = {q for _, q, f, l in obs if f and l}
pres = sum(1 for q in full if q in sset)

def nodes_of(slot):
    slot = slot.replace("EXE-?", "EXE-AT").replace("DAC-?", "DAC-UBD")
    parts = slot.split("+"); pa = "PA-GA" in parts
    return [b + ("+PA-GA" if pa and b.startswith("EXE") else "") for b in parts if b != "PA-GA"]
Kset = set(K); SKID = {s["id"]: s for s in SK3["skeletons"]}
cmp = collections.Counter(); lost = collections.Counter()
for f in glob.glob(str(R / "7_scenario_generation/out_r3c/*/FINAL_RESULTS.jsonl")):
    for l in open(f):
        r = json.loads(l); seq = [nodes_of(s) for s in SKID[r["scenario_id"].split("__")[-1]]["slots"]]
        bad = [(x[0], y[0]) for x, y in zip(seq, seq[1:]) if not any((a, b) in Kset for a in x for b in y)]
        cmp["units"] += 1; cmp["grounded"] += not bad
        if r["final_outcome"] == "success": cmp["success"] += 1; cmp["success_grounded"] += not bad
        for b in set(bad): lost[f"{b[0]} → {b[1]}"] += 1
K3n = {(x, y) for e in G3["edges"] for x in nodes_of(e["from"]) for y in nodes_of(e["to"])}
Kv3 = {(e["from"], e["to"]) for e in V3["K"]}
json.dump({"status": "on the r4 re-judgment draft basis (before review)", "V": V, "K": [{"from": a, "to": b, "cases": sorted({x["case"] for x in EV[(a, b)]}), "evidence": EV[(a, b)]} for a, b in K],
           "rules": {"starts": STARTS, "ends": ENDS, "min_len": MIN_LEN, "max_len": MAX_LEN, "repeat_caps": dict(sorted(CAP.items()))},
           "stats": {"V": len(V), "K": len(K), "skeletons": len(skel), "start_ENT-II": sum(1 for q in skel if q[0] == "ENT-II"), "observed_full": len(full), "observed_preserved": pres, **{f"existing_{k}": v for k, v in cmp.items()}}},
          open(OUT / "GRAPH_r4_draft.json", "w"), ensure_ascii=False, indent=1)
json.dump([{"id": f"R4D{i:05d}", "nodes": list(q), "length": len(q), "kind": "observed" if q in full else "recombined"} for i, q in enumerate(skel, 1)], open(OUT / "skeletons_r4_draft.json", "w"), ensure_ascii=False)
f2 = lambda S: ", ".join(f"{a} → {b}" for a, b in sorted(S)) or "none"
md = ["# Comparison of intermediate event graphs", "", "The table reports intermediate coding results.", "",
      "| Item | r3 | r4 v3 provisional | r4 re-judgment draft |", "|---|---|---|---|",
      f"| Vertices \\|V\\| | 17 cells | {len(V3['V'])} | {len(V)} |", f"| 2-gram \\|K\\| | {len(G3['edges'])} | {len(Kv3)} | {len(K)} |",
      f"| Skeletons | {len(SK3['skeletons']):,} | {V3['stats']['skeletons']:,} | {len(skel):,} |",
      f"| ENT-II-start skeletons | 6,906 | {V3['stats']['start_ENT-II']:,} | {sum(1 for q in skel if q[0] == 'ENT-II'):,} |",
      f"| Observed-path reproduction | 29/29 | {V3['stats']['observed_preserved']}/{V3['stats']['observed_full']} | {pres}/{len(full)} |",
      f"| Existing scenarios keeping their grounding | 1,347 | {V3['stats']['existing_grounded']} | {cmp['grounded']} |",
      f"| Existing successes keeping their grounding | 224 | {V3['stats']['existing_success_grounded']} | {cmp['success_grounded']} |", "",
      "Vertices: " + ", ".join(V), "", "## vs r3 (expanded to Node units)", "", "newly added: " + f2(set(K) - K3n), "", "removed: " + f2(K3n - set(K)), "",
      "## vs v3 provisional", "", "newly added: " + f2(set(K) - Kv3), "", "removed: " + f2(Kv3 - set(K)), "",
      "## Edges where existing scenarios lost their grounding (# scenarios)", "", ", ".join(f"{k} {v}" for k, v in lost.most_common()) or "none", "",
      f"Rules: start {STARTS} · end {ENDS} · length {MIN_LEN}~{MAX_LEN} · repeat caps " + str({k: v for k, v in sorted(CAP.items()) if v > 1}) + " (others 1)"]
(OUT / "COMPARE_r4_draft.md").write_text("\n".join(md), encoding="utf-8"); print("\n".join(md))
