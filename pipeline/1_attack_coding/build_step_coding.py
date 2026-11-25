# -*- coding: utf-8 -*-
"""Assemble the step-level coding records for the 24 selected ATLAS cases.

Each record links steps to source text, Node labels, reasons and branches.
Cases without a coded Node have no path. This stage produces step_coding_24.json.
The release includes an intermediate event-coding record (attack_coding.json)
and the reviewed graph and path set in pipeline/3_threat_knowledge/."""
import json, re, sys, collections
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parents[1])); import paths as P
SEL = P.SEL_JSON
ATLAS = P.ATLAS
OLD = P.SEED
OUT = P.CODING
OLD_CASES = P.LEGACY_CASES
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(P.DEF_DIR))
from coding_new6 import C as NEW, BRANCHES as NEW_BR   # noqa: E402
import definitions_v2 as V2  # noqa: E402

NODES = [n[0] for n in V2.NODES]
REASONS = {r[0]: r[1] for r in V2.REASONS}
AUTH_SRC = {'User-delegated Authority': 'User-delegated Authority', 'Service / App Authority': 'Service / App Authority'}


def clean(s):
    s = re.sub(r'</?(?:div|span|br|p|b|i|u|em|strong|ul|ol|li|a|code|pre|sup|sub|img|table|tr|td|th)\b[^>]*>', ' ', str(s), flags=re.I)   # remove only real HTML tags — preserve source strings like <think>·<<<…>>>
    s = re.sub(r'&(?:nbsp|amp|lt|gt|quot|#\d+);', lambda m: {'&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"'}.get(m.group(0), ' '), s)
    return re.sub(r'\s+', ' ', s).strip()

errors = []
sel = json.loads(SEL.read_text(encoding='utf-8'))
picked = [c[4:] for c in sel['selected']]
atlas = yaml.safe_load(ATLAS.read_text(encoding='utf-8'))
T = atlas['techniques']
old = json.loads(OLD.read_text(encoding='utf-8'))['cases']


def atlas_steps(cid):
    emp = atlas['relationships']['AML.' + cid]['employs']
    return {e['step-id']: e for e in sorted(emp, key=lambda e: int(e['step-id'][1:]))}


def live(nodes):
    return [n for n in nodes if n['status'] in ('keep', 'add')]


def build_paths(cid, steps, branches):
    stepmap = {s['step_id']: s for s in steps}
    if cid in branches:
        b = branches[cid]; kind = b['kind']
        covered = set(b['common']) | {s for _, _, ps in b['paths'] for s in ps}
        if b['common'] and covered != set(stepmap): errors.append(f'{cid}: branch markup does not cover all steps {sorted(set(stepmap) ^ covered)}')
        if kind == 'branch' and b['common'] and not any(live(stepmap[s]['nodes']) for s in b['common']):
            errors.append(f'{cid}: it is a branch but the common steps have no Node')
        plist = [(lab, title, b['common'] + ps) for lab, title, ps in b['paths']]
    else:
        kind, plist = 'single', [('A', 'Single path', [s['step_id'] for s in steps])]
    paths = []
    for lab, title, sids in plist:
        pseq = []
        for sid in sids:
            acted = False
            for n in live(stepmap[sid]['nodes']):
                if str(n.get('note', '')).startswith(PRE): continue   # an R15 pre-injection call is not put in the path · an R9 unknown-type (-?) is left as a cell and connections touching that cell are not counted (k2)
                if n['node'] == 'PA-GA' and not acted: continue                                   # R6: authority goes only with an action in the same step — if that action is dropped from the path, the authority is dropped too
                acted = acted or n['node'].split('-')[0] in ('EXE', 'DAC', 'SC')
                pseq.append(dict(pos=len(pseq) + 1, atlas_step=sid, node=n['node'], res=n['res'], **({'auth': n['auth']} if n.get('auth') else {})))
        if pseq:
            paths.append(dict(label=lab, title=title, steps=sids, sequence=pseq))
    return kind, paths


# Apply recorded coding adjustments to the upstream step annotations.
PRE = "[pre-injection] "                                     # R15: a call that, under a normal request, ends up reading attack content — recorded but removed from the path
def nd(node, res, note, auth=None):
    d = dict(node=node, res=res, status="add", seq=None, note=note)
    if auth: d["auth"] = auth
    return d
V2_EDITS = {   # (case, step): (action, Node list, reason) — action: replace = replace this step's Nodes / prepend = add in front / renote = replace the note on the same Node
 ("CS0026", "S06"): ("replace", [nd("PST-KB", "RAG / Knowledge Base", '"all received emails are ingested into the Copilot RAG database" — describes only storage (indexing). Entry into the model context is S09 (v2: storage alone does not attach ENT-II)')], "Separate ENT-II·PST-KB"),
 ("CS0059", "S05"): ("replace", [nd("PST-KB", "RAG / Knowledge Base", '"automatically ingested into a RAG database" — describes only storage. Entry into the context is S06 (v2)')], "Separate ENT-II·PST-KB"),
 ("CS0021", "S02"): ("prepend", [nd("EXE-AT", "Connector / API", PRE + '"retrieve the webpage using its WebPilot plugin" — plugin call per the user\'s request (R15)')], "R15"),
 ("CS0045", "S04"): ("prepend", [nd("EXE-AT", "MCP / Remote Tool", PRE + '"asked Cursor to use an MCP tool to scrape the malicious website" — MCP call per the user\'s request (R15)')], "R15"),
 ("CS0051", "S09"): ("prepend", [nd("EXE-AT", "Connector / API", PRE + '"retrieved from the website using the OpenClaw\'s web_fetch Skill" — call per the user\'s request (R15)')], "R15"),
 ("CS0055", "S03"): ("prepend", [nd("EXE-SCU", "Browser Control", PRE + '"visited the researcher\'s website" — a website visit during a task (R15)')], "R15"),
 ("CS0024", "S03"): ("prepend", [nd("EXE-AT", "Search / Retrieval Tool", PRE + '"retrieved by the email assistant in another reply generation task" — a search call during a normal task (decision 1015 ②, R7·R15)')], "R7 implied·R15"),
 ("CS0059", "S06"): ("prepend", [nd("EXE-AT", "Search / Retrieval Tool", PRE + '"it retrieved the malicious email into its context" — search per the user\'s call (decision 1015 ②, R7·R15)')], "R7 implied·R15"),
 ("CS0063", "S04"): ("prepend", [nd("EXE-AT", "Connector / API", PRE + '"Gemini retrieved the adversary-controlled content" — call per a calendar/email summary request (decision 1015 ②, R7·R15)')], "R7 implied·R15"),
 ("CS0066", "S04"): ("prepend", [nd("EXE-AT", "Connector / API", PRE + '"caused the agent to retrieve the malicious content" — call per a mailbox summary request (decision 1015 ②, R7·R15)')], "R7 implied·R15"),
 ("CS0039", "S04"): ("prepend", [nd("EXE-AT", "MCP / Remote Tool", PRE + '"used Claude Sonnet (which can interact with Jira via the Atlassian MCP server) to help them resolve the malicious ticket" — the MCP call that read the ticket (decision 1015 ②, R7·R15)')], "R7 implied·R15"),
 ("CS0053", "S06"): ("prepend", [nd("EXE-AT", "MCP / Remote Tool", PRE + '"users … instructed their AI agent to use tools provided by the poisoned Postmark MCP Server" — a legitimate call per the user\'s request (R15, sequence review 1015)')], "R15"),
 ("CS0026", "S12"): ("renote", {"HD-UI": "[action unconfirmed] Provides a manipulated response (manipulated citation · attacker account) that induces the transfer — basis: case description 'successfully manipulated Microsoft 365 Copilot … manipulate the document reference in its response. This tricks the user …'. The user's actual transfer is conditional on S13 'If the victim follows through' — unconfirmed",
                                  "OT-RG": "A response containing a manipulated citation · attacker account information — basis: the response-manipulation result in the case description (S12 is that instruction content)"}, "Unify the HD-UI definition"),
}
# ── adjudication results for items where the independent coder differed (reliability/adjudication.py) — apply add/remove to the coding
from adjudication import D as ADJ   # noqa: E402
RES = {"ENT-DI": "Chat / UI Input", "EXE-AT": "Connector / API", "EXE-CCE": "Shell / OS Command", "OT-ER": "External API / HTTP Endpoint",
       "OT-RG": "Text / Response", "DAC-UBD": "Work Document", "PA-GA": "User-delegated Authority", "PST-CFG": "Persistent Prompt / Configuration",
       "ENT-II": "Search / Retrieved Content", "HD-UI": "Link Navigation / Click", "EXE-?": "(details held)", "DAC-?": "(details held)"}
RES_FIX = {("CS0053", "S04", "PST-CFG"): "Tool Package / Implementation",
           ("CS0064", "S11", "EXE-?"): "(details held)",
           ("CS0054", "S10", "EXE-AT"): "MCP / Remote Tool", ("CS0054", "S10", "PA-GA"): "User-delegated Authority", ("CS0045", "S09", "DAC-CS"): "API / Secret Key",
           ("CS0048", "S04", "EXE-SCU"): "Terminal / CLI", ("CS0048", "S04", "EXE-CCE"): "Shell / OS Command", ("CS0048", "S04", "PA-GA"): "Service / App Authority",
           ("CS0045", "S09", "EXE-SCU"): "Terminal / CLI", ("CS0045", "S09", "EXE-CCE"): "Shell / OS Command", ("CS0039", "S06", "PA-GA"): "User-delegated Authority", ("CS0039", "S07", "PA-GA"): "User-delegated Authority",
           ("CS0052", "S10", "OT-ER"): "External API / HTTP Endpoint", ("CS0059", "S07", "EXE-AT"): "Connector / API", ("CS0024", "S04", "OT-RG"): "Text / Response",
           ("CS0066", "S12", "OT-RG"): "Text / Response", ("CS0066", "S12", "EXE-AT"): "Communication Tool", ("CS0066", "S12", "PA-GA"): "User-delegated Authority", ("CS0066", "S12", "OT-ER"): "Email / External Message",
           ("CS0037", "S06", "ENT-II"): "Email", ("CS0037", "S03", "EXE-AT"): "Communication Tool", ("CS0037", "S03", "OT-ER"): "Email / External Message", ("CS0037", "S13", "PA-GA"): "Service / App Authority",
           ("CS0024", "S05", "DAC-UBD"): "Communication Content", ("CS0063", "S14", "PA-GA"): "User-delegated Authority", ("CS0054", "S02", "PST-CFG"): "Persistent Prompt / Configuration",
           ("CS0064", "S05", "PST-CFG"): "Persistent Prompt / Configuration", ("CS0039", "S06", "EXE-AT"): "MCP / Remote Tool", ("CS0016", "S08", "OT-RG"): "Code / Generated Artifact",
           ("CS0059", "S08", "OT-RG"): "Text / Response", ("CS0052", "S10", "EXE-CCE"): "Python Execution", ("CS0053", "S06", "EXE-CCE"): "Tool Implementation Code"}
AUTH = {"User-delegated Authority": "User-delegated Authority", "Service / App Authority": "Service / App Authority"}
ORDER = ["PST-CFG", "PST-KB", "ENT-DI", "ENT-II", "EXE-AT", "EXE-SCU", "EXE-CCE", "EXE-?", "PA-GA", "DAC-UBD", "DAC-CS", "DAC-SRD", "DAC-?", "SC-SYS", "SC-DAT", "PST-MEM", "OT-RG", "OT-ER", "HD-UI"]
def apply_adj(cid, steps):
    for st in steps:
        for (c, sid, node, act, why) in ADJ:
            if c != cid or sid != st["step_id"]: continue
            if act == "remove":
                st["nodes"] = [n for n in st["nodes"] if not (n["node"] == node and n["status"] in ("keep", "add") and not str(n.get("note", "")).startswith(PRE))]   # a [pre-injection] record is not subject to adjudication removal
            elif act == "add" and not any(n["node"] == node and n["status"] in ("keep", "add") for n in st["nodes"]):
                res = RES_FIX.get((c, sid, node), RES.get(node, ""))
                d = dict(node=node, res=res, status="add", seq=None, note=f"[re-applied] {why}")
                if node == "PA-GA": d["auth"] = dict(src=AUTH.get(res, "User-delegated Authority"), scope="(re-applied — see source evidence)", how=why[:120])
                st["nodes"].append(d)
            st.setdefault("adjudication", []).append(dict(node=node, decision=act, why=why))
        # keep the existing Node order (source order) and insert only re-applied Nodes at their ORDER position
        live_n = [n for n in st["nodes"] if n["status"] in ("keep", "add") and not str(n.get("note", "")).startswith("[re-applied]")]
        new_n = [n for n in st["nodes"] if str(n.get("note", "")).startswith("[re-applied]")]
        dead_n = [n for n in st["nodes"] if n["status"] not in ("keep", "add")]
        rank = lambda n: ORDER.index(n["node"]) if n["node"] in ORDER else 99
        for nn in new_n:
            i = next((k for k, x in enumerate(live_n) if rank(x) > rank(nn) and not str(x.get("note", "")).startswith(PRE)), len(live_n))
            live_n.insert(i, nn)
        st["nodes"] = live_n + dead_n
        if live_n: st["reason"] = None
        elif not st.get("reason") or any(x["decision"] == "remove" for x in st.get("adjudication", [])):
            whys = " ".join(x["why"] for x in st.get("adjudication", []) if x["decision"] == "remove")
            st["reason"] = "INSTR" if "→ INSTR" in whys else "PREP" if "PREP" in whys else (st.get("reason") or "DUP")
    return steps

def apply_v2(cid, steps):
    out = []
    for st in steps:
        st = json.loads(json.dumps(st))
        for n in st["nodes"]:
            if n["node"] == "SC-BIZ": n["node"] = "SC-DAT"; n["note"] = (n.get("note") or "") + " (v2: SC-BIZ → SC-DAT, the changed target (the calendar event) is a Resource)"
        e = V2_EDITS.get((cid, st["step_id"]))
        if e:
            act, val, why = e
            if act == "replace": st["nodes"], st["reason"] = val, None
            elif act == "prepend": st["nodes"] = val + st["nodes"]
            elif act == "renote":
                for n in st["nodes"]:
                    if n["node"] in val and n["status"] in ("keep", "add"): n["note"] = val[n["node"]]
            st["v2_edit"] = why
        out.append(st)
    return out

# Apply reviewed reason codes, annotation wording and authority labels.
REASON_FIX = {("CS0050", s): "NOAGENT" for s in ("S03", "S05", "S06", "S07", "S08")}
REASON_FIX[("CS0064", "S06")] = "DUP"
REASON_FIX[("CS0053", "S05")] = "DUP"   # 'effects persist' = restatement of the S04 installation (PST-CFG)
REASON_FIX.update({("CS0037", "S08"): "PREP", ("CS0037", "S09"): "PREP",        # the attacker learns the Agent's access scope = reconnaissance (no event recorded before → not DUP)
                   ("CS0048", "S03"): "INSTR",                                  # 'could have injected the prompt directly' = a capability description
                   ("CS0054", "S07"): "INSTR", ("CS0054", "S08"): "INSTR", ("CS0054", "S09"): "INSTR"})   # instruction content (not a restatement of a recorded event)   # the victim loads/interprets the poisoned template = restatement of the S05 PST-CFG effect (not attacker-placement DELIV) — context entry is S07 ENT-II
OLD_RULE = {"Rule G": "R6", "Rule E": "R8 new event", "Rule D": "same handling", "Rule F": "ENT↔OT-ER direction"}
NOTE_FIX = {
    ("CS0026", "S12", "HD-UI"): "[action unconfirmed] Induced action: transfer to the attacker's account. Provides a manipulated response (manipulated citation · attacker account) that induces the transfer — source: ATLAS AML.CS0026 case description, paragraph 1 'The prompt injection overrode Copilot's search functionality … and manipulate the document reference in its response. This tricks the user into believing that Copilot's result is trustworthy and makes it more likely they will follow through with the wire transfer'. The user's actual transfer is conditional on S13 'If the victim follows through'",
    ("CS0026", "S12", "OT-RG"): "A response containing a manipulated citation · attacker account information — source: ATLAS AML.CS0026 case description, paragraph 1 '… manipulate the document reference in its response' (the S12 source is that instruction content)",
    ("CS0024", "S04", "OT-RG"): "S04·S05 describe the self-replication and information exposure of the same generated output. No separate attack-induced new acquisition is confirmed, so no additional DAC·PA is attached and S05 is linked as supplementary evidence for S04",
    ("CS0054", "S10", "EXE-AT"): "[re-applied] A call that put personal data in the tool arguments and sent it to the remote MCP server — S04 'the agent invoked the poisoned MCP tool and acted on the malicious instructions contained in its definition' describes the same call (linked to S04 as the call's basis, not counted as a separate legitimate call). The tool description enters the context before the call, so S04 is ENT-II",
    ("CS0064", "S09", "HD-UI"): "[action unconfirmed] Induced action: opening a link/reference chosen by the attacker — 'in a form that appears relevant or trustworthy to the user'",
}
ORDER_FIX = {("CS0016", "S08"): ["ENT-DI", "OT-RG", "EXE-CCE", "PA-GA", "SC-SYS"],   # input → code generation → execution of that code → no response
             ("CS0066", "S12"): ["OT-RG", "EXE-AT", "PA-GA", "OT-ER"],                 # create a copy of the prompt → send call → goes out to contacts
             ("CS0054", "S10"): ["DAC-?", "EXE-AT", "PA-GA", "OT-ER"]}
AUTH_CASE = {   # PA-GA authority source — whose authority the Agent acted under in the case (User-delegated Authority / Service / App Authority)
    "CS0016": "Service / App Authority", "CS0021": "User-delegated Authority", "CS0024": "User-delegated Authority", "CS0026": "User-delegated Authority",
    "CS0037": "Service / App Authority", "CS0038": "User-delegated Authority", "CS0039": "User-delegated Authority", "CS0041": "User-delegated Authority",
    "CS0045": "User-delegated Authority", "CS0046": "User-delegated Authority", "CS0048": "Service / App Authority", "CS0049": "User-delegated Authority",
    "CS0050": "User-delegated Authority", "CS0051": "User-delegated Authority", "CS0052": "Service / App Authority", "CS0053": "Service / App Authority",
    "CS0054": "User-delegated Authority", "CS0055": "User-delegated Authority", "CS0059": "User-delegated Authority", "CS0062": "Service / App Authority",
    "CS0063": "User-delegated Authority", "CS0064": "User-delegated Authority", "CS0066": "User-delegated Authority", "CS0067": "Service / App Authority"}
def finalize(cid, steps):
    import re as _re
    for st in steps:
        r = REASON_FIX.get((cid, st["step_id"]))
        if r and not live(st["nodes"]): st["reason"] = r
        for n in st["nodes"]:
            note = n.get("note") or ""
            for a, b in OLD_RULE.items(): note = _re.sub(a + r"\b", b, note)
            n["note"] = NOTE_FIX.get((cid, st["step_id"], n["node"]), note)
    # Attach PA-GA to the execution or to a read or state change with no call in the preceding step.
    prev_exe = False
    for st in steps:
        L = [n for n in live(st["nodes"]) if not str(n.get("note", "")).startswith(PRE)]
        old = [n for n in L if n["node"] == "PA-GA"]
        st["nodes"] = [n for n in st["nodes"] if not (n["node"] == "PA-GA" and n["status"] in ("keep", "add"))]
        acts = [n for n in L if n["node"] != "PA-GA"]
        exe = [n for n in acts if n["node"].startswith("EXE")]
        ds = [n for n in acts if n["node"].split("-")[0] in ("DAC", "SC")]
        for anchor in (exe if exe else ds[:1] if (ds and not prev_exe) else []):   # one per execution (EXE); if there is no execution, one on the first acquisition/change
            res = old[0]["res"] if old else AUTH_CASE[cid]
            auth = dict(old[0]["auth"]) if old and old[0].get("auth") else dict(scope="(the case's Agent authority scope — see judgment note)", how=f"{anchor['node']} — action induced by the attack")
            auth["src"] = AUTH.get(res, "User-delegated Authority")
            why = "Attack-induced execution" if exe else "An acquisition/change by the call that is not recorded in a preceding step"
            pa = dict(node="PA-GA", res=res, status="add", seq=None, auth=auth,
                      note=f"[R6] {why}({anchor['node']}) — which the attacker cannot write directly {AUTH.get(res, '')} authority used by the Agent on their behalf" + (f" · previous note: {old[0]['note']}" if old and old[0].get('note') else ""))
            i = st["nodes"].index(anchor); st["nodes"].insert(i + 1, pa)
        of = ORDER_FIX.get((cid, st["step_id"]))
        if of:   # source causal order (so the listing order of Nodes in the same step is not used as time order; if the source states an order, keep it)
            lv = [n for n in st["nodes"] if n["status"] in ("keep", "add")]; dead = [n for n in st["nodes"] if n not in lv]
            key = lambda n: of.index(n["node"]) + (0.5 if n["node"] == "PA-GA" else 0) if n["node"] in of else 99
            st["nodes"] = sorted(lv, key=key) + dead
            st["order_note"] = "Source causal order: " + " → ".join(of)
        if L: prev_exe = bool(exe)
    # Derive the display name from the adjudicated reason code.
    for st in steps:
        st["reason_label"] = REASONS.get(st.get("reason"), "")
    return steps

cases, origin = {}, {}
for cid in picked:
    A = atlas_steps(cid)
    if cid in old:                                                   # existing coding — check the source is identical
        oc = json.loads((OLD_CASES / cid / 'case.json').read_text(encoding='utf-8'))
        same = all(clean(s['description']) == clean(A[s['step_id']]['description']) for s in oc['atlas_steps']) \
            and [s['step_id'] for s in oc['atlas_steps']] == list(A)
        if not same: errors.append(f'{cid}: the source of the existing coding differs from ATLAS-2026.09 — needs recoding')
        o = old[cid]
        steps = finalize(cid, apply_adj(cid, apply_v2(cid, o['steps'])))
        for st in steps: st['text'] = clean(A[st['step_id']]['description'])   # the display source text is re-read from the ATLAS YAML (preserving the source string)
        if steps != o['steps']:  # Preserve the source branches when coding changes.
            br = {cid: dict(kind=o['path_kind'], common=[], paths=[(p['label'], p['title'], p['steps']) for p in o['paths']])} if o['path_kind'] != 'single' else {}
            kind, paths = build_paths(cid, steps, br)
        else:
            paths = o['paths']
        cases[cid] = dict(name=o['name'], steps=steps, paths=paths, path_kind=o['path_kind'])
        origin[cid] = 'step_coding_22seed (source confirmed identical)'
        continue
    if cid not in NEW:
        errors.append(f'{cid}: selected but no coding'); continue
    if [r[0] for r in NEW[cid]] != list(A): errors.append(f'{cid}: step list differs from the source')
    steps = []
    for sid, nodes, reason, note in NEW[cid]:
        lv = live(nodes)
        if not lv and reason not in REASONS: errors.append(f'{cid}/{sid}: no Node but no reason code')
        if lv and reason: errors.append(f'{cid}/{sid}: has a Node but also a reason code')
        for i, n in enumerate(lv):
            if n['node'] not in NODES and not (n['node'].endswith('-?') and n['node'][:-2] in {x.split('-')[0] for x in NODES}): errors.append(f'{cid}/{sid}: unknown Node {n["node"]}')
            if n['node'] == 'PA-GA':
                a = n.get('auth') or {}
                if not all(a.get(k) for k in ('src', 'scope', 'how')): errors.append(f'{cid}/{sid}: no PA-GA authority record')
                elif AUTH_SRC.get(a['src']) != n['res']: errors.append(f'{cid}/{sid}: PA-GA source·resource mismatch')
                if i == 0: errors.append(f'{cid}/{sid}: no execution/access Node before PA-GA')
        e = A[sid]
        steps.append(dict(step_id=sid, technique=T[e['target']]['name'], technique_id=e['target'], text=clean(e['description']),
                          nodes=nodes, reason=reason, reason_label=REASONS.get(reason, ''), note=note))
    steps = finalize(cid, apply_adj(cid, apply_v2(cid, steps)))
    kind, paths = build_paths(cid, steps, NEW_BR)
    cases[cid] = dict(name=atlas['case-studies']['AML.' + cid]['name'], steps=steps, paths=paths, path_kind=kind)
    origin[cid] = 'coding_new6 (ATLAS-2026.09 source)'
    if not paths:
        cases[cid]['no_path_reason'] = "No Agent (LLM) involvement (R13). The selection condition (A∧C∧¬O) is met, but every step of the attack is performed by the attacker's JavaScript calling the OpenClaw gateway API directly — token theft (S03) · authentication (S05) · turning off the approval feature (S06) · turning off the sandbox (S07) · remote code execution (S08) are all NOAGENT. There is no step where the LLM read or processed the attack content, so there is no Agent sequence"

if errors:
    print('errors:'); [print('  ', e) for e in errors]; sys.exit(1)

nodes_cnt = collections.Counter(n['node'] for c in cases.values() for s in c['steps'] for n in live(s['nodes']))
meta = dict(selection=P.rel(SEL), atlas=ATLAS.name, n_cases=len(cases),
            n_paths=sum(len(c['paths']) for c in cases.values()),
            total_steps=sum(len(c['steps']) for c in cases.values()),
            steps_with_node=sum(1 for c in cases.values() for s in c['steps'] if live(s['nodes'])),
            reasons=dict(collections.Counter(s['reason'] for c in cases.values() for s in c['steps'] if not live(s['nodes']))),
            node_labels=dict(nodes_cnt), origin=origin,
            no_path=[cid for cid, c in cases.items() if not c['paths']])
OUT.write_text(json.dumps(dict(meta=meta, cases=cases), ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(f"[step_coding_24] cases {meta['n_cases']} · paths {meta['n_paths']} · steps {meta['total_steps']} (steps with Node {meta['steps_with_node']}) → {OUT.name}")
print('  no path:', meta['no_path'])
for cid in picked:
    if origin[cid].startswith('coding_new6'):
        for p in cases[cid]['paths']:
            print(f"  {cid} {p['label']} {p['title']}: " + ' → '.join(e['node'] for e in p['sequence']))
