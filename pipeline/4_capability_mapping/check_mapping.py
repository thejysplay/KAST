# -*- coding: utf-8 -*-
"""Schema and evidence-reference checks for capability-mapping outputs.

Checks cover the Node inventory, judgment fields, status consistency and whether
cited paths and sources are present in the supplied AgentSpec. The report also
compares two runs. Passing these checks does not establish the semantic
correctness of a capability judgment.

This reference validator requires full mapping outputs and AgentSpecs that are
not bundled. The public status-only export supports aggregation checks only.
"""
import argparse, collections, json, re, yaml
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECS = HERE.parent / "agent_specs_v3_r2" / "specs"
NODES = ["ENT-DI", "ENT-II", "PA-GA", "DAC-UBD", "DAC-CS", "DAC-SRD", "EXE-AT", "EXE-SCU", "EXE-CCE",
         "SC-SYS", "SC-DAT", "PST-MEM", "PST-KB", "PST-CFG", "OT-RG", "OT-ER", "HD-UI"]
KO = {"ENT-DI": "direct input", "ENT-II": "instruction ingestion", "PA-GA": "use of delegated authority", "DAC-UBD": "work/user information", "DAC-CS": "authentication secret",
      "DAC-SRD": "system information", "EXE-AT": "app-function call", "EXE-SCU": "computer control", "EXE-CCE": "code/command execution", "SC-SYS": "system-behavior change",
      "SC-DAT": "stored-content change", "PST-MEM": "memory persistence", "PST-KB": "retrieval-store persistence", "PST-CFG": "config/setting persistence", "OT-RG": "result generation",
      "OT-ER": "external delivery", "HD-UI": "inducing user action"}
ST = {"active": "active", "conditional": "conditional", "inactive": "inactive", "pending": "pending"}
ap = argparse.ArgumentParser(); ap.add_argument("--tags", nargs="+", default=["run1", "run2"]); a = ap.parse_args()


def parse_path(p):
    toks, i, cur = [], 0, ""
    while i < len(p):
        c = p[i]
        if c == "[":
            if cur: toks.append(cur); cur = ""
            j = p.index("]", i); toks.append(("sel", p[i + 1:j])); i = j + 1
            if i < len(p) and p[i] == ".": i += 1
            continue
        if c == ".":
            if cur: toks.append(cur); cur = ""
        else:
            cur += c
        i += 1
    if cur: toks.append(cur)
    return toks


def resolve(spec, p):
    try:
        node = spec
        for t in parse_path(p.strip()):
            if isinstance(t, tuple):
                sel = t[1].strip().strip("'\"")
                if not isinstance(node, list): return False
                if sel.isdigit() and int(sel) < len(node):
                    node = node[int(sel)]; continue
                hit = [x for x in node if isinstance(x, dict) and sel in (x.get("name"), x.get("id"))]
                if not hit: return False
                node = hit[0]
            else:
                if not isinstance(node, dict) or t not in node: return False
                node = node[t]
        return True
    except Exception:
        return False


def sources(x, acc):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "source" and isinstance(v, str): acc.add(v.strip())
            elif k == "source" and isinstance(v, list): acc.update(str(x).strip() for x in v)
            else: sources(v, acc)
    elif isinstance(x, list):
        for v in x: sources(v, acc)
    return acc


def check(sid, d, spec):
    errs, ev_total, ev_bad_path, ev_bad_src = [], 0, [], []
    srcs = sources(spec, set())
    if d.get("agent_id") != sid: errs.append(f"agent_id `{d.get('agent_id')}`")
    nm = d.get("node_mappings") or []
    ids = [n.get("node_id") for n in nm]
    if sorted(ids) != sorted(NODES): errs.append(f"Node list mismatch: missing {set(NODES) - set(ids)} · duplicate/extra {[i for i, c in collections.Counter(ids).items() if c > 1 or i not in NODES]}")
    pend = False
    for n in nm:
        s, nid = n.get("status"), n.get("node_id")
        if s not in ST: errs.append(f"{nid}: status `{s}`"); continue
        pend |= s == "pending"
        R = n.get("routes") or []
        if s in ("active", "conditional") and not R: errs.append(f"{nid}: {s} but no routes")
        if s == "conditional" and not any(r.get("conditions") for r in R): errs.append(f"{nid}: conditional but no conditions")
        if s == "inactive" and not n.get("inactive_basis"): errs.append(f"{nid}: inactive but no inactive_basis")
        if s == "inactive" and R: errs.append(f"{nid}: inactive but has routes")
        if s == "pending" and not n.get("missing_information"): errs.append(f"{nid}: pending but no missing_information")
        for r in R:
            for e in r.get("evidence") or []:
                ev_total += 1
                if not resolve(spec, str(e.get("spec_path", ""))): ev_bad_path.append(f"{nid} {r.get('route_id')}: `{e.get('spec_path')}`")
                src = e.get("source")
                for one in (src if isinstance(src, list) else [src]):
                    if one in (None, "", "null"): continue
                    o = str(one).strip()
                    if o not in srcs and not any(o in s_ for s_ in srcs):
                        ev_bad_src.append(f"{nid} {r.get('route_id')}: `{o[:120]}`")
            if not (r.get("evidence")): errs.append(f"{nid} {r.get('route_id')}: no evidence")
    if bool(d.get("mapping_complete")) != (not pend): errs.append(f"mapping_complete={d.get('mapping_complete')} but pending {'present' if pend else 'absent'}")
    return {"errors": errs, "evidence": ev_total, "bad_path": ev_bad_path, "bad_source": ev_bad_src,
            "status": {n.get("node_id"): n.get("status") for n in nm}}


ids = sorted({p.name.split(".")[0] for p in (HERE / "out").glob("*.json") if not p.name.endswith(".meta.json")})
res = collections.defaultdict(dict)
for sid in ids:
    spec = yaml.safe_load((SPECS / f"{sid}.yaml").read_text(encoding="utf-8"))
    for t in a.tags:
        f = HERE / "out" / f"{sid}.{t}.json"
        if f.exists():
            res[sid][t] = check(sid, json.loads(f.read_text(encoding="utf-8")), spec)

L = ["# Capability-mapping check result", "",
     "Schema and evidence-reference checks with a two-run comparison; these do not establish the semantic correctness of a judgment.",
     "Judgment: active = a functional route is confirmed · conditional = when a stated condition is met · inactive = no/blocked capability per the evidence · pending = insufficient information to decide. This is not an attack-success judgment.", "",
     "## Target × Node judgment (run1)", "",
     "| Target | " + " | ".join(f"{n}<br>({KO[n]})" for n in NODES) + " |", "|---|" + "---|" * len(NODES)]
for sid in ids:
    r = res[sid].get(a.tags[0])
    if r:
        L.append(f"| `{sid}` | " + " | ".join(ST.get(r["status"].get(n), "?") for n in NODES) + " |")
L += ["", "## Checks", "", "| Target | Run | Format errors | # evidence | missing spec_path | source not in spec | run1·run2 judgment agreement |", "|---|---|---|---|---|---|---|"]
summary = {}
for sid in ids:
    s1, s2 = res[sid].get(a.tags[0]), res[sid].get(a.tags[1]) if len(a.tags) > 1 else None
    agree = None
    if s1 and s2:
        diff = [n for n in NODES if s1["status"].get(n) != s2["status"].get(n)]
        dtxt = ", ".join("%s %s→%s" % (n, ST.get(s1["status"].get(n)), ST.get(s2["status"].get(n))) for n in diff)
        agree = f"{len(NODES) - len(diff)}/17" + (f" (differs: {dtxt})" if diff else "")
    for t, r in res[sid].items():
        L.append(f"| `{sid}` | {t} | {len(r['errors'])} | {r['evidence']} | {len(r['bad_path'])} | {len(r['bad_source'])} | {agree if t == a.tags[0] else ''} |")
    summary[sid] = {t: {"status": r["status"], "errors": r["errors"], "bad_path": r["bad_path"], "bad_source": r["bad_source"]} for t, r in res[sid].items()}
L.append("")
for sid in ids:
    for t, r in res[sid].items():
        if r["errors"] or r["bad_path"] or r["bad_source"]:
            L += [f"### `{sid}` {t}", ""] + [f"- format: {e}" for e in r["errors"]] + [f"- path: {e}" for e in r["bad_path"][:30]] + [f"- source: {e}" for e in r["bad_source"][:30]] + [""]
(HERE / "MAPPING_CHECK.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
(HERE / "mapping_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n".join(L[:12 + len(ids)]))
