# -*- coding: utf-8 -*-
"""Measure agreement between the independent coder and the reviewed reference.

The comparison covers 255 steps and reports behavior-presence agreement,
per-Unit and per-Node kappa, exact Node-set agreement and unknown-code counts.
The reference excludes CS0048-A-E2 and counts PA-GA as a separate Node.
coding_reliability_kappa.json contains the reported Gemini 2.5 Flash results."""
import argparse, json, collections, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = HERE.parent
NODES = ["ENT-DI", "ENT-II", "PA-GA", "DAC-UBD", "DAC-CS", "DAC-SRD", "EXE-AT", "EXE-SCU", "EXE-CCE", "SC-SYS", "SC-DAT",
         "PST-MEM", "PST-KB", "PST-CFG", "OT-RG", "OT-ER", "HD-UI"]
UNITS = ["ENT", "PA", "DAC", "EXE", "SC", "PST", "OT", "HD"]
EXCLUDE_EVENTS = {"CS0048-A-E2"}


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n; pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return po, (round((po - pe) / (1 - pe), 2) if pe < 1 else None)


def reference():
    D = json.load(open(R / "9_recoding/out/r4_coding/R4_CODING_DRAFT.json"))
    ref = collections.defaultdict(set)
    for p in D["paths"]:
        for e in p["events"]:
            if e.get("id") in EXCLUDE_EVENTS: continue
            for n in e["nodes"]:
                ref[(p["case"], e["step"])].add(n["code"])
                if n.get("pa"): ref[(p["case"], e["step"])].add("PA-GA")
    for r in D["reason_steps"]: ref.setdefault((r["case"], r["step"]), set())
    for r in D["background"]:   # pre-injection normal calls kept as background records, excluded from paths -> no Node
        if r.get("r4", "").startswith("background record"): ref.setdefault((r["case"], r["step"]), set())
    return ref


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="gemini-pro"); a = ap.parse_args()
    out = HERE / "out" / f"{a.model}-r4"
    rows = json.load(open(out / "coding.json"))
    ours = reference()
    theirs, unknown = {}, collections.Counter()
    for r in rows:
        k = (r["case"], r["step"]); theirs[k] = set()
        for f in r["facts"] or []:
            for nd in re.sub(r"\([^)]*\)", "", str(f.get("node") or "")).upper().replace(",", "+").split("+"):   # drop annotations like "(specific kind confirmed: ...)"
                nd = nd.strip()
                if not nd: continue
                if nd in NODES: theirs[k].add(nd)
                else: unknown[nd] += 1
    K = sorted(k for k in ours if k in theirs)
    missing = sorted(set(ours) - set(theirs))
    res = {"model": a.model, "steps_compared": len(K), "steps_reference": len(ours), "steps_missing": [f"{c} {s}" for c, s in missing]}
    po, k = kappa([bool(ours[x]) for x in K], [bool(theirs[x]) for x in K]); res["agent_fact"] = {"agree": round(po, 3), "kappa": k}
    res["exact_set"] = round(sum(ours[x] == theirs[x] for x in K) / len(K), 3)
    ne = [x for x in K if ours[x] or theirs[x]]
    res["exact_set_nonempty"] = round(sum(ours[x] == theirs[x] for x in ne) / max(1, len(ne)), 3)
    res["units"], res["nodes"] = [], []
    for u in UNITS:
        A = [any(n.startswith(u + "-") for n in ours[x]) for x in K]; B = [any(n.startswith(u + "-") for n in theirs[x]) for x in K]
        po, kk = kappa(A, B); res["units"].append({"unit": u, "ours": sum(A), "coder": sum(B), "both": sum(p and q for p, q in zip(A, B)), "agree": round(po, 3), "kappa": kk})
    ks = []
    for nd in NODES:
        A = [nd in ours[x] for x in K]; B = [nd in theirs[x] for x in K]
        po, kk = kappa(A, B)
        if kk is not None and (sum(A) or sum(B)): ks.append(kk)
        res["nodes"].append({"node": nd, "ours": sum(A), "coder": sum(B), "both": sum(p and q for p, q in zip(A, B)), "agree": round(po, 3), "kappa": kk,
                             "only_ours": [f"{c} {s}" for (c, s), p, q in zip(K, A, B) if p and not q],
                             "only_coder": [f"{c} {s}" for (c, s), p, q in zip(K, A, B) if q and not p]})
    ks_sorted = sorted(ks)
    res["node_kappa_mean"] = round(sum(ks) / len(ks), 2) if ks else None
    res["node_kappa_median"] = ks_sorted[len(ks_sorted) // 2] if ks else None
    res["unknown_codes"] = dict(unknown)
    (out / "compare.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    L = [f"# Codebook application agreement — {a.model}", "",
         f"Steps {len(K)}/{len(ours)} · Agent-fact presence agreement {res['agent_fact']['agree']:.0%} kappa={res['agent_fact']['kappa']} · "
         f"Node kappa mean {res['node_kappa_mean']} / median {res['node_kappa_median']} · exact Node-set {res['exact_set']:.0%} "
         f"(steps where either side has a Node: {res['exact_set_nonempty']:.0%})", "",
         "| Unit | Ours | Coder | Both | kappa |", "|---|---|---|---|---|"] + [f"| {u['unit']} | {u['ours']} | {u['coder']} | {u['both']} | {u['kappa']} |" for u in res["units"]]
    L += ["", "| Node | Ours | Coder | Both | kappa | Ours only | Coder only |", "|---|---|---|---|---|---|---|"] + [
        f"| {n['node']} | {n['ours']} | {n['coder']} | {n['both']} | {n['kappa']} | {', '.join(n['only_ours'][:6])} | {', '.join(n['only_coder'][:6])} |" for n in res["nodes"]]
    if unknown: L += ["", f"Codes not in the codebook: {dict(unknown)}"]
    (out / "compare.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
