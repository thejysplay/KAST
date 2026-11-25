# -*- coding: utf-8 -*-
"""Select ATLAS cases using predefined rules on technique metadata.

The screening criteria cover agent presence, evidence of manipulation and
attacker-operated agents. A manually defined technique list provides a separate
cross-check. The published selection is in case_selection.json. This reference
script depends on an ATLAS snapshot and external rule files."""
import argparse, json
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parents[1])); import paths as P


def steps_of(atlas, cid):
    emp = (atlas["relationships"].get(cid) or {}).get("employs") or []
    return sorted(emp, key=lambda e: int("".join(ch for ch in e["step-id"] if ch.isdigit()) or 0))


def hit(steps, table):
    return [{"step": e["step-id"], "technique": e["target"], "name": table[e["target"]]} for e in steps if e["target"] in table]


def full_names(atlas):
    """For each technique, 'parent name: … : own name'. The parent is found via the 'specializes' relation in the YAML relationships (does not rely on the ID format)."""
    T, rel = atlas["techniques"], atlas.get("relationships") or {}
    parent = {k: [x["target"] for x in ((rel.get(k) or {}).get("specializes") or []) if x["target"] in T] for k in T}

    def name(k, seen=()):
        if k in seen:
            raise ValueError(f"specializes cycle: {k}")
        ps = parent[k]
        return ": ".join([name(ps[0], seen + (k,)), T[k]["name"]]) if ps else T[k]["name"]
    return {k: name(k) for k in T}


def has_word(name, words):
    n = name.lower()
    return any(w.lower() in n for w in words)          # case-insensitive substring


def tables(atlas, R):
    """Build technique lookup tables from the configured metadata rules."""
    T, names = atlas["techniques"], full_names(atlas)
    agent = {k: names[k] for k, t in T.items() if (t.get("platforms") or []) == R["agent_platforms"]}
    comp = {k: n for k, n in names.items() if has_word(n, R["compromise_keywords"])}
    oper = {k: n for k, n in names.items() if has_word(n, R["operate_keywords"])}
    return agent, comp, oper


def judge(atlas, cid, tabs):
    case, steps = atlas["case-studies"][cid], steps_of(atlas, cid)
    agent, comp, oper = tabs
    A, C, O = hit(steps, agent), hit(steps, comp), hit(steps, oper)
    if not A:   res, why = "excluded", "no A — no ATLAS Agent-only technique"
    elif O:     res, why = "excluded", "attacker-operation evidence present — role-mixed cases are not included"
    elif not C: res, why = "excluded", "no manipulation/compromise evidence — an Agent is present but no record of being attacked"
    else:       res, why = "selected", "A + manipulation/compromise evidence, no attacker-operation evidence"
    return {"id": cid, "name": case["name"], "type": case.get("type"), "target": case.get("target"), "actor": case.get("actor"),
            "modified_date": str(case.get("modified-date")), "result": res, "reason": why,
            "evidence": {"agent": A, "compromise": C, "operate": O}}


def diff(prev, cur):
    P, C = {r["id"]: r for r in prev["cases"]}, {r["id"]: r for r in cur["cases"]}
    out = {"New cases": [], "Judgment changed": [], "Evidence changed": [], "Case modified": []}
    for cid, r in C.items():
        p = P.get(cid)
        if not p: out["New cases"].append(f"{cid} → {r['result']} ({r['name']})")
        elif p["result"] != r["result"]: out["Judgment changed"].append(f"{cid} {p['result']} → {r['result']} ({r['reason']})")
        elif p["evidence"] != r["evidence"]: out["Evidence changed"].append(f"{cid} {r['result']} (technique evidence changed)")
        if p and p["modified_date"] != r["modified_date"]: out["Case modified"].append(f"{cid} {p['modified_date']} → {r['modified_date']}")
    out["Deleted cases"] = [cid for cid in P if cid not in C]
    pt, ct = set(prev.get("technique_ids") or []), set(cur.get("technique_ids") or [])
    if pt and ct:
        out["New techniques"] = [f"{k} {cur['technique_names'][k]}" for k in sorted(ct - pt)]
        out["Deleted techniques"] = sorted(pt - ct)
    md = [f"# Selection diff: {prev['atlas']} ({prev['rules_version']}) → {cur['atlas']} ({cur['rules_version']})", ""]
    for k, v in out.items():
        md += [f"## {k} ({len(v)})", *[f"- {x}" for x in v], ""]
    return "\n".join(md)


def first_sentence(text, n=220):
    t = " ".join(str(text or "").split())
    i = t.find(". ")
    t = t[: i + 1] if 0 < i < n else t[:n] + ("…" if len(t) > n else "")
    return t.replace("|", "/")


def keyword_evidence(atlas, R):
    """For each keyword: the techniques it matches + the first sentence of the ATLAS description, and the selection change when that keyword is removed. Also the change when a candidate word is added."""
    T, cases, names = atlas["techniques"], sorted(atlas["case-studies"]), full_names(atlas)
    sel = lambda RR: {c for c in cases if judge(atlas, c, tables(atlas, RR))["result"] == "selected"}
    base, ev = sel(R), {"keywords": [], "candidates": []}
    for kind in ("compromise_keywords", "operate_keywords"):
        for w in R[kind]:
            hits = [{"id": k, "name": names[k], "desc": first_sentence(T[k].get("description"))} for k in sorted(T) if has_word(names[k], [w])]
            s = sel({**R, kind: [x for x in R[kind] if x != w]})
            ev["keywords"].append({"kind": kind[:-9], "word": w, "techniques": hits, "drop_minus": sorted(base - s), "drop_plus": sorted(s - base)})
    for kind, words in (R.get("sensitivity_candidates") or {}).items():
        for w in words:
            key = f"{kind}_keywords"
            s = sel({**R, key: R[key] + [w]})
            ev["candidates"].append({"kind": kind, "word": w, "n_tech": sum(has_word(names[k], [w]) for k in T),
                                     "add_plus": sorted(s - base), "add_minus": sorted(base - s)})
    return ev


def report(out, R):
    """Summarize the selection criteria, evidence and decisions for each case."""
    tb, cc = out["tables"], out["crosscheck_manual"]
    L = [f"# Case selection evidence — {out['atlas']} · rules {out['rules_version']}", "",
         "This document is generated automatically by `select_cases.py`. The same ATLAS YAML and the same rules produce the same document.", "",
         "## 1. Rules", "",
         "**selection = A ∧ C ∧ ¬O** (looks at all steps of a case)", "",
         "| Item | Rule (computed from YAML technique fields) |", "|---|---|",
         f"| A an Agent is present | there is a technique whose `platforms` is exactly {R['agent_platforms']} |",
         f"| C manipulation/compromise evidence | there is a technique whose full name contains one of {R['compromise_keywords']} |",
         f"| O attacker-operation evidence | there is a technique whose full name contains one of {R['operate_keywords']} |", "",
         "- Full name: for a sub-technique, `parent name: sub name` (e.g. `AML.T0080.000` → `AI Agent Context Poisoning: Memory`).",
         "- The parent name is found via the YAML `specializes` relation, and keywords are compared as case-insensitive substrings.",
         "- Dropping cases that have O is a conservative collection policy that keeps out role-mixed cases (not a proof that no victim Agent is present).",
         "- A and C are each checked only for presence at the case level. That the Agent in A and the target in C are the same entity is not proven via the YAML.",
         "- Keywords do not map names and definitions perfectly. E.g. the name of `AML.T0108` is 'AI Agent' so it does not match C, but its description covers abuse of a victim Agent. `AML.T0121` 'AI Agent Environment Reconstruction' does not match O.", "",
         f"## 2. Results", "", f"cases {out['n']} → A {out['n_A']} → **selected {len(out['selected'])}** · excluded {len(out['excluded'])}", "",
         f"Cross-check against the manually reviewed technique list (`{R.get('crosscheck')}`), selected {cc['manual_selected']} — "
         + ("**identical to the rule result**" if cc["same"] else f"difference: rule-only {cc['only_rule']} / human-list-only {cc['only_manual']}") if cc else "no cross-check", "",
         "## 3. Technique table computed by the rules", ""]
    for key, title in (("A", "A — Agent-only techniques"), ("C", "C — manipulation/compromise techniques"), ("O", "O — attacker-operation techniques")):
        L += [f"### {title} ({len(tb[key])})", "", " · ".join(f"`{k}` {v}" for k, v in sorted(tb[key].items())), ""]
    kv = out.get("keyword_evidence")
    if kv:
        cs = lambda xs: ", ".join(x[4:] for x in xs) or "no change"
        L += ["## 4. Keyword evidence", "",
              "The keywords translate the definition's 'manipulation/compromise' (injection, poisoning, tampering, manipulation, jailbreak) and 'attacker operation' (Agent deployment, autonomous execution) into the vocabulary of ATLAS technique names.",
              "Below, for each keyword, are the techniques it matches, the first sentence of each technique's ATLAS description (original text), and how the selection changes when that single keyword is removed.",
              "This is a sensitivity check, not a rule change. A keyword whose removal leaves the result unchanged is not therefore unnecessary (another technique may keep catching the same case).", "",
              "### 4-1. Removing keywords one at a time", "", "| Kind | Keyword | # techniques matched | cases dropped if removed | cases added if removed |", "|---|---|---|---|---|"]
        for k in kv["keywords"]:
            L.append(f"| {k['kind']} | `{k['word']}` | {len(k['techniques'])} | {cs(k['drop_minus']) if k['drop_minus'] else '—'} | {cs(k['drop_plus']) if k['drop_plus'] else '—'} |")
        L += ["", "### 4-2. Adding candidate words that were not included", "", "| Kind | Candidate | # techniques matched | cases added if added | cases dropped if added |", "|---|---|---|---|---|"]
        for c in kv["candidates"]:
            L.append(f"| {c['kind']} | `{c['word']}` | {c['n_tech']} | {cs(c['add_plus']) if c['add_plus'] else '—'} | {cs(c['add_minus']) if c['add_minus'] else '—'} |")
        L += ["", "### 4-3. Techniques per keyword with the ATLAS description (first sentence, original text)", ""]
        for k in kv["keywords"]:
            L += [f"**`{k['word']}`** ({k['kind']})", "", "| Technique | Full name | ATLAS description |", "|---|---|---|"]
            L += [f"| `{t['id']}` | {t['name']} | {t['desc']} |" for t in k["techniques"]] + [""]
    L += ["## 5. Judgment per case", "", "| Case | Name | Judgment | Reason | A evidence | C evidence | O evidence |", "|---|---|---|---|---|---|---|"]
    fmt = lambda xs: ", ".join(f"{x['step']} {x['technique'][4:]}" for x in xs) or "—"
    for r in out["cases"]:
        e = r["evidence"]
        L.append(f"| {r['id'][4:]} | {r['name']} | **{r['result']}** | {r['reason']} | {fmt(e['agent'])} | {fmt(e['compromise'])} | {fmt(e['operate'])} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default=str(P.ATLAS))
    ap.add_argument("--rules", default=str(HERE / "rules" / "selection_rules.v1.yaml"))
    ap.add_argument("--prev", help="previous selection result json — the diff is written to .diff.md")
    a = ap.parse_args()
    atlas = yaml.safe_load(Path(a.atlas).read_text(encoding="utf-8"))
    R = yaml.safe_load(Path(a.rules).read_text(encoding="utf-8"))
    ver = atlas["collection"]["version"]
    T = atlas["techniques"]
    tabs = tables(atlas, R)
    rows = [judge(atlas, cid, tabs) for cid in sorted(atlas["case-studies"])]
    pick = lambda res: [r["id"] for r in rows if r["result"] == res]
    cc = yaml.safe_load((HERE / R["crosscheck"]).read_text(encoding="utf-8")) if R.get("crosscheck") else None
    cross = None
    if cc:
        alt = (tabs[0], {k: v for k, v in cc["compromise"].items() if k in T}, {k: v for k, v in cc["operate"].items() if k in T})
        alt_sel = [cid for cid in sorted(atlas["case-studies"]) if judge(atlas, cid, alt)["result"] == "selected"]
        cross = {"manual_selected": len(alt_sel), "same": alt_sel == pick("selected"),
                 "only_rule": sorted(set(pick("selected")) - set(alt_sel)), "only_manual": sorted(set(alt_sel) - set(pick("selected")))}
    out = {"atlas": f"ATLAS-{ver}", "atlas_modified": str(atlas["collection"].get("modified-date")), "rules_version": R["rules_version"],
           "n": len(rows), "n_A": sum(bool(r["evidence"]["agent"]) for r in rows), "selected": pick("selected"), "excluded": pick("excluded"),
           "tables": {"A": tabs[0], "C": tabs[1], "O": tabs[2]},
           "technique_ids": sorted(T), "technique_names": full_names(atlas), "crosscheck_manual": cross, "cases": rows}
    od = P.SEL_JSON.parent; od.mkdir(parents=True, exist_ok=True)
    f = od / f"ATLAS-{ver}__rules-{R['rules_version']}.json"
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline='\n')
    out["keyword_evidence"] = keyword_evidence(atlas, R)
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline='\n')
    f.with_suffix(".md").write_text(report(out, R), encoding="utf-8", newline='\n')
    print(f"[select] ATLAS-{ver} cases {len(rows)} → A {out['n_A']} → selected {len(out['selected'])} · excluded {len(out['excluded'])}"
          f" | table A {len(tabs[0])}·C {len(tabs[1])}·O {len(tabs[2])} | human-list cross-check {'match' if cross and cross['same'] else cross}"
          f" → {f.relative_to(HERE)}")
    if a.prev:
        prev = json.loads(Path(a.prev).read_text(encoding="utf-8"))
        g = f.with_suffix(".diff.md"); g.write_text(diff(prev, out), encoding="utf-8", newline='\n'); print("  diff →", g.relative_to(HERE))
