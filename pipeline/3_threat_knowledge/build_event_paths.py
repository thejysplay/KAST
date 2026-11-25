# -*- coding: utf-8 -*-
"""Assemble intermediate event-coding records for each case and branch.

Records contain Node labels, authority, supporting source text and evidence
for event order. The coding includes model-assisted evidence checks and manual
annotations. The reviewed graph and path set are in transition_graph.json
and skeletons.json."""
import json, re, sys, collections, concurrent.futures as cf
from pathlib import Path
import yaml
R = Path(__file__).resolve().parents[1]
OUT = R / "9_recoding/out/r4_coding"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "3_reliability")); sys.path.insert(0, str(R / "9_recoding"))
from quotes import quotes
NO_LLM = "--no-llm" in sys.argv
SEQ = json.load(open(R / "4_sequences/out/attack_sequences.json"))["cases"]
ST = json.load(open(R / "2_coding/out/step_coding_24.json"))["cases"]
QC = {(x["case"], x["step"], x["idx"]): x for x in json.load(open(R / "9_recoding/out/QUOTE_CANDIDATES.json"))}
STEP = {(cs, s["step_id"]): s for cs, c in ST.items() for s in c["steps"]}
DESC = {}
def _walk(o):
    if isinstance(o, dict):
        if str(o.get("id", "")).startswith("AML.CS"): DESC[o["id"].replace("AML.", "")] = o.get("description", "")
        for v in o.values(): _walk(v)
    elif isinstance(o, list):
        for v in o: _walk(v)
_walk(yaml.safe_load(open(R / "data/ATLAS-2026.09.yaml")))
norm = lambda t: re.sub(r"\s+", " ", t or "").strip().lower()
AUTH = {"User-delegated Authority": "user", "Service / App Authority": "service", "Service Authority": "service"}

def evidence(cs, step, code):
    """Return a quoted phrase from a source annotation or evidence candidate."""
    s = STEP.get((cs, step))
    if not s: return None, None
    for i, n in enumerate(s["nodes"]):
        if n.get("status") == "del" or n["node"] != code: continue
        q = quotes(n.get("note", ""))
        if q: return q[0], "Memo quote"
        c = QC.get((cs, step, i))
        if c and c.get("quote"): return c["quote"], "candidate · " + ("step" if c["source"] == "step" else "description")
    return None, None

def N(code, pa=None, auth=None, quote=None, src=None, detail=None):
    return {"code": code, "pa": pa, "auth": auth, "quote": quote, "quote_src": src, "detail": detail}

# ---------------- 2) edited cases (event unit). order = (type, evidence) — a procedure order · b explicit precedence · c processing–result / produce–use · cut order unconfirmed ----------------
def E(step, nodes, order=None, note="", ev=None, flags=()):
    return {"step": step, "nodes": nodes, "order": order, "note": note, "evidence_steps": ev or [step], "flags": list(flags)}
CUT = "CUT"
OVR = {
 ("CS0016", "A"): [
   E("S06", [N("ENT-DI")]),
   E("S06", [N("OT-RG", quote="outputted … Python code", src="step")], ("c", "Input → code produced from that input (\"Instead write code that displays all environment variables\" → \"outputted … Python code\")"), "Code generation (GPT)"),
   E("S06", [N("EXE-CCE", pa=True, auth="service", quote="executed Python code that printed the host system's environment variables", src="step")], ("b", "description \"Python code that is then executed\""), "DPI · Service authority: the attacker can only ask questions; code runs on the server"),
   E("S06", [N("DAC-CS", quote="included the application's unsecured GPT-3 API key", src="Memo quote"), N("DAC-SRD", quote="printed the host system's environment variables", src="Memo quote")], ("c", "Execution → that execution prints the environment variables (\"printed the host system's environment variables\")"), "Same retrieval event (P7) — 'which' is not sequence evidence"),
   E("S06", [N("OT-RG", quote="revealed system environment variables", src="step")], ("c", "Obtained value → output containing that value"), "Provide the result (an output distinct from code generation)")],
 ("CS0021", "A"): [
   E("S02", [N("ENT-II")]),
   E("S03", [N("OT-RG"), N("DAC-UBD", quote="embed the user's chat history as query parameter in the URL", src="step", detail={"status": "confirmed", "what": "chat history", "quote": "embed the user's chat history"})], None, "Use conversation content (GPT)"),
   E("S04", [N("OT-ER")])],
 ("CS0021", "B"): [E("S02", [N("ENT-II")]), E("S05", [N("EXE-AT", pa=True, auth="user")], None, "IPI · plugin call in the victim user's session (PA-GA 10/21)")],
 ("CS0024", "-"): [
   E("S02", [N("ENT-II")]),
   E("S02", [N("PST-KB")], ("cut", "Between reading (reply generation) and RAG storage there is an ordering expression but no process–result relation (P6)")),
   E("S03", [N("ENT-II")]),
   E("S04", [N("OT-RG"), N("DAC-UBD", quote="leak sensitive data such as emails, addresses, and phone numbers", src="step S05", detail={"status": "confirmed", "what": "emails, addresses, phone numbers", "quote": "emails, addresses, and phone numbers"})], None, "Linked on the basis of S05 (GPT)", ev=["S04", "S05"])],
 ("CS0045", "-"): [
   E("S04", [N("ENT-II")]),
   E("S06", [N("EXE-SCU", pa=True, auth="user")]),
   E("S06", [N("HD-UI", quote="Cursor prompted the user before executing a shell command", src="step")], ("c", "Tool call → approval request before execution (\"prompted the user before executing a shell command\")"),
     "Induce approval of the attack command — evidence together with the S07 base64-disguised command · user approval [action unconfirmed] (GPT)", ev=["S06", "S07"]),
   E("S08", [N("EXE-CCE", pa=True, auth="user")], None, "", flags=["Check the source whether the S08 \"find file location\" command and the S09 curl exfiltration command are the same command (GPT)"]),
   E("S09", [N("DAC-CS"), N("OT-ER")], None, "No separate acquisition evidence, so two judgments on the same exfiltration event (GPT) — S08 only finds the location")],
 ("CS0048", "A"): [
   E("S04", [N("ENT-DI")]),
   E("S04", [N("EXE-SCU", pa=True, auth="service", quote="prompted ClawdBot to `cat SOUL.md`", src="step")], ("c", "Input → a shell command made from that input"),
     "cat is a shell command, so the interface is evident in the source (C2a) · DPI Service authority (a system file reachable only via the control screen) · execution (EXE-CCE) is not attached because there is no execution description (GPT)", flags=["Confirm EXE-SCU interface evidence (GPT)"]),
   E("S04", [N("DAC-SRD")], ("c", "Command → the system-prompt content obtained by that command")),
   E("S04", [N("OT-RG")], ("c", "Obtained value → a response containing that value (\"it replied with its contents\")"))],
 ("CS0051", "-"): [
   E("S09", [N("ENT-II")]), E("S12", [N("EXE-SCU", pa=True, auth="user")]), E("S12", [N("EXE-CCE", pa=True, auth="user")], ("b", "\"to retrieve and execute the malicious script\"")),
   E("S13", [N("PST-CFG")]), E("S14", [N("ENT-II")]),
   E("S16", [N("EXE-AT", pa=True, auth="user")], None, "web_fetch — IPI · the Agent on the victim's computer fetches it on their behalf (PA-GA 10/21)"),
   E("S16", [N("ENT-II")], ("c", "Request → that response (a command inside the TODO list) enters the context")),
   E("S16", [N("EXE-SCU", pa=True, auth="user")], ("b", "\"requested the TODO list … and executed the commands via its bash Skill\"")),
   E("S16", [N("EXE-CCE", pa=True, auth="user")], ("c", "Shell tool → run the command via that tool"))],
 ("CS0053", "-"): [
   E("S04", [N("PST-CFG")]),
   E("S06", [N("EXE-AT", quote="instructed their AI agent to use tools provided by the poisoned Postmark MCP Server", src="step",
               detail={"status": "confirmed", "what": "Postmark MCP email-sending tool", "quote": "use tools provided by the poisoned Postmark MCP Server"})], None,
     "A legitimate call the user requested — not an attack-induced execution, so no PA-GA. That call activates the malicious implementation and is included in the path (P10 exception, GPT)"),
   E("S06", [N("EXE-CCE", pa=True, auth="user")], ("c", "Call → malicious code executed by that call (\"the malicious code was executed\")")),
   E("S07", [N("OT-ER"), N("DAC-UBD", quote="the entire contents of their emails are exfiltrated", src="step", detail={"status": "confirmed", "what": "email contents", "quote": "the entire contents of their emails"})], None, "Process and exfiltrate the email content (GPT)")],
 ("CS0054", "-"): [
   E("S02", [N("PST-CFG")]), E("S04", [N("ENT-II")]), E("S06", [N("EXE-SCU", pa=True, auth="user")]),
   E("S10", [N("DAC-CS", quote="the victim's credentials are exfiltrated to the poisoned MCP server", src="description")], None, "description: credential exfiltration (C1 · GPT)"),
   E("S10", [N("EXE-AT", pa=True, auth="user", detail={"status": "not_confirmed", "what": "", "quote": ""})], ("b", "description \"store their contents in one of the input variables to the tool. When the tool runs, …\""), "Remote MCP call — details unconfirmed"),
   E("S10", [N("OT-ER")], ("b", "description \"When the tool runs, the victim's credentials are exfiltrated\""))],
 ("CS0055", "-"): [
   E("S03", [N("ENT-II")]),
   E("S06", [N("EXE-SCU", pa=True, auth="user", quote="Clicking the \"see instructions\" button", src="step")], None, "Click a button"),
   E("S06", [N("EXE-CCE", pa=True, auth="user", quote="executed JavaScript that placed a malicious command into the agent's clipboard", src="step")], ("c", "Click → that click executes JavaScript (\"Clicking … executed JavaScript\")"), "Execute JavaScript"),
   E("S06", [N("EXE-SCU", pa=True, auth="user", quote="open a terminal, paste the contents of its clipboard", src="step")], ("b", "\"The agent then proceeded to … open a terminal\""), "Open the terminal · paste"),
   E("S06", [N("EXE-CCE", pa=True, auth="user", quote="hit return, executing the command", src="step")], ("c", "Paste and press return → execute the command"), "Execute a command"),
   E("S07", [N("EXE-CCE", pa=True, auth="user", quote="The researcher's script ran", src="step")], ("c", "description \"The command downloads a script … and executes it\""), "Run the downloaded script — the actual execution of S07 (only the potential-harm sentence is HARM, P10 fact unit)")],
 ("CS0064", "A"): [
   E("S05", [N("PST-CFG")]),
   E("S06", [N("EXE-CCE", pa=True, auth="user", quote="causing the attacker-modified prompt-construction logic to execute", src="step")], None, "Run the poisoned template logic — a different event from installation (GPT), r3 DUP fix"),
   E("S07", [N("ENT-II")]), E("S08", [N("OT-RG")])],
 ("CS0064", "B"): [
   E("S05", [N("PST-CFG")]),
   E("S06", [N("EXE-CCE", pa=True, auth="user", quote="causing the attacker-modified prompt-construction logic to execute", src="step")]),
   E("S07", [N("ENT-II")]),
   E("S11", [N("EXE-AT", pa=True, auth="user", quote="The compromised agent invokes a network-capable or write-capable tool", src="step", detail={"status": "not_confirmed", "what": "network-capable or write-capable tool (kind not stated)", "quote": "invokes a network-capable or write-capable tool"})], None, "S10 is INSTR (C5) · the send-tool type is unknown → treated as a generic tool call"),
   E("S11", [N("OT-ER", quote="transmit sensitive information to an attacker-controlled destination", src="step"), N("DAC-UBD", quote="transmit sensitive information", src="step", detail={"status": "not_confirmed", "what": "", "quote": "transmit sensitive information"})], ("c", "Send-tool call → transmit sensitive information"), "Uses and transmits sensitive information — information type unknown (GPT)")],
 ("CS0066", "A"): [
   E("S04", [N("ENT-II")]), E("S06", [N("EXE-AT", pa=True, auth="user")]), E("S07", [N("DAC-UBD")]),
   E("S09", [N("EXE-AT", pa=True, auth="user")], None, "Links S08's URL selection and opening to this event (GPT)", ev=["S08", "S09"]), E("S09", [N("OT-ER")], ("c", "URL request → data delivered by that request"))],
 ("CS0066", "C"): [
   E("S04", [N("ENT-II")]),
   E("S11", [N("EXE-AT", pa=True, auth="user")], None, "S06 is supplementary evidence for this call — no evidence of a separate second call; does not create a self-link (GPT)", ev=["S06", "S11"]),
   E("S11", [N("DAC-UBD")], ("c", "Search the mailbox → collect addresses")), E("S12", [N("OT-RG")]), E("S12", [N("EXE-AT", pa=True, auth="user")], ("b", "\"reproduce the prompt in new emails … and distribute them\"")),
   E("S12", [N("OT-ER")], ("c", "Send-tool call → email distribution"))],
}
MERGE = {("CS0026", "S12", "OT-RG", "HD-UI"): "Same response event — the manipulated answer itself induces the transfer; no 2-gram between the two (P3 · P7, GPT)"}
NOTES = {"CS0037": "Main attack entry ENT-II: recorded not as S06 (a reconnaissance interaction) but as the description · on the basis that it is the same attack branch as the post-S11 action — r3 note 'the only remaining inflow evidence' removed (GPT)",
         "CS0038": "PST-MEM: linked on the basis of the S03 instruction + the actual call in S04's next interaction (GPT)",
         "CS0039": "The S07 reply posting is an incidental record for delivery, so it is not SC-DAT (decision) · PA-GA basis: the S04 support-engineer context + S05 access to the victim's JSM (GPT)",
         "CS0050": "No Agent path — reason code NOAGENT is marked as a SCOPE sub-reason (r4)"}
EXTRA_FLAGS = [
 ("CS0048", "S06", "The note says 'no authority' but the label is PA-GA — unify the note and label on the basis of root-shell use (service authority) (GPT)"),
 ("CS0064", "S09", "Confirm the DUP handling basis — whether it is the same output, or split it if it is a different attack variant. Also confirm the malicious-code-generation result in the description (GPT)"),
 ("CS0037", "S00", "Reconcile the difference between the original technique ID AML.T0006.003 and the current AML.T0006 (GPT)"),
 ("CS0041", "S03", "Fix the reason code that treated a posting possibility as an actual posting (GPT)"),
 ("CS0051", "S08", "Fix the note that used 'domain mistake' as the delivery reason (GPT)"),
 ("CS0059", "S09", "Fix the note that used 'attempt' as a duplicate reason (GPT)"),
 ("CS0039", "S04", "Character-mismatch quote — keep verbatim or mark as an elided quote (GPT)"),
 ("CS0048", "S04", "Two character-mismatch quote lines — keep verbatim or mark as an elided quote (GPT)"),
]

# ---------------- 1) automatic conversion ----------------
def auto_events(cs, p):
    evs = []
    for x in p["sequence"]:
        slot = x["node"].replace("EXE-?", "EXE-AT").replace("DAC-?", "DAC-UBD")
        parts = slot.split("+"); pa = "PA-GA" in parts
        a = x.get("authority") or {}
        nodes = []
        for b in [q for q in parts if q != "PA-GA"]:
            q, src = evidence(cs, x["atlas_step"], x["node"].split("+")[0] if "?" in x["node"] else b)
            nd = N(b, pa=(pa if b.startswith("EXE") else None), auth=(AUTH.get(a.get("src", ""), a.get("src")) if pa and b.startswith("EXE") else None), quote=q, src=src)
            if "?" in x["node"] and b in ("EXE-AT", "DAC-UBD"): nd["detail"] = {"status": "not_confirmed", "what": "", "quote": ""}; nd["from_unknown"] = True
            nodes.append(nd)
        evs.append(E(x["atlas_step"], nodes, None, ("r3 unknown notation → generic Node · details unconfirmed (C4)" if "?" in x["node"] else "")))
        if a: evs[-1]["auth_note"] = f"{a.get('scope', '')} · {a.get('how', '')}"
    for i in range(len(evs) - 1, 0, -1):
        a, b = evs[i - 1], evs[i]
        k = (cs, a["step"], a["nodes"][-1]["code"], b["nodes"][0]["code"])
        if a["step"] == b["step"] and k in MERGE:
            a["nodes"] += b["nodes"]; a["note"] = MERGE[k]; del evs[i]
    return evs

# Apply the recorded authority-subject annotations consistently within each case.
AUTH_FIX = {("CS0048", "S05"): ("service", "CS0048 is a DPI that moved ClawdBot via an exposed control screen — the attacker is not a legitimate user, and execution is carried out under the service identity of the ClawdBot host. Unified with branches A · C (in r3, only branch B had been recorded as User-delegated Authority)")}
paths = []
for cs, v in sorted(SEQ.items()):
    for p in v["paths"]:
        lab = (p.get("label") or "-").split(" ")[0]
        if (cs, lab) in OVR: evs = [dict(e, nodes=[dict(n) for n in e["nodes"]]) for e in OVR[(cs, lab)]]; src = "Correction (GPT review · decision)"
        else: evs = auto_events(cs, p); src = "Automatic conversion"
        for i, e in enumerate(evs):
            e["id"] = f"{cs}-{lab}-E{i + 1}"
            for n in e["nodes"]:
                if not n.get("quote"):
                    q, s_ = evidence(cs, e["step"], n["code"]); n["quote"], n["quote_src"] = q, s_
            if i == 0: e["order"] = ("start", "Path start (P13)")
            elif e["order"] is None and evs[i - 1]["step"] != e["step"]: e["order"] = ("a", f"Procedure order within the same branch, {evs[i - 1]['step']} → {e['step']}")
        for e in evs:
            fx = AUTH_FIX.get((cs, e["step"]))
            if fx:
                for n in e["nodes"]:
                    if n.get("pa") and n.get("auth") != fx[0]: n["auth"] = fx[0]; e["note"] = (e.get("note", "") + " · " if e.get("note") else "") + "Unify the authority subject: " + fx[1]
        paths.append({"case": cs, "branch": lab, "label": p.get("label") or "Single path", "source": src, "events": evs, "note": NOTES.get(cs, "")})

# ---------------- 3) LLM: detail-confirmation status · same-step order ----------------
import hashlib
CACHE_P = OUT / "llm_cache.json"
CACHE = json.load(open(CACHE_P)) if CACHE_P.exists() else {}
def ask(prompt):
    k = hashlib.sha256(prompt.encode()).hexdigest()
    if k not in CACHE:
        from backend import gen_json
        CACHE[k] = gen_json(prompt, model="gemini-pro", temp=0)
    return CACHE[k]
# where a human corrected the LLM order judgment (cases where the LLM read A · B in reverse)
ORDER_FIX = {
 ("CS0037", "S11", "EXE-AT", "DAC-UBD"): ("c", "Call → retrieval by that call (\"asks the agent to retrieve … The agent retrieves the entire file\") — the LLM read the order backwards and a human corrected it"),
 ("CS0049", "S10", "EXE-SCU", "EXE-CCE"): ("c", "Tool → execution via that tool (\"executed the shell command using it's `bash` tool\") — the LLM read the order backwards and a human corrected it"),
}
def verbatim(q, cs, step):
    return bool(q) and (norm(q) in norm(STEP[(cs, step)]["text"]) or norm(q) in norm(DESC.get(cs, "")))

detail_jobs, order_jobs = [], []
for p in paths:
    for i, e in enumerate(p["events"]):
        for n in e["nodes"]:
            if n["code"] in ("EXE-AT", "DAC-UBD") and not n.get("detail"): detail_jobs.append((p, e, n))
        if e["order"] is None: order_jobs.append((p, i))

def do_detail(job):
    p, e, n = job; cs = p["case"]; st = STEP[(cs, e["step"])]
    kind = "tool or function the Agent invoked" if n["code"] == "EXE-AT" else "kind of information the Agent accessed"
    prompt = ("You audit qualitative coding of ATLAS AI-incident case studies. The Node below is already assigned; do not change it.\n"
              f"Node: {n['code']} — {'General Tool Invocation: the Agent actually invoked a tool or function' if n['code'] == 'EXE-AT' else 'General Information Access: the content of information was actually read, retrieved or used'}.\n"
              f"Question: does the source text state the specific {kind}? If yes, name it briefly and copy the shortest verbatim phrase (3-20 words) that states it. "
              "If the text only says a tool was used / data was accessed without saying which, answer not_confirmed.\n\n"
              f"CASE {cs} SUMMARY:\n{DESC.get(cs, '')}\n\nSTEP {e['step']}:\n{st['text']}\n\n"
              'Return JSON: {"status":"confirmed"|"not_confirmed","what":"<short name or empty>","quote":"<verbatim phrase or empty>"}')
    try: o = ask(prompt)
    except Exception as ex: return job, {"status": "error", "what": "", "quote": "", "error": str(ex)[:120]}
    st_ = o.get("status") if o.get("status") in ("confirmed", "not_confirmed") else "not_confirmed"
    q = (o.get("quote") or "").strip()
    ok = verbatim(q, cs, e["step"]) if q else st_ == "not_confirmed"
    return job, {"status": st_, "what": o.get("what", ""), "quote": q, "verbatim": ok, "by": "LLM"}

def do_order(job):
    p, i = job; cs = p["case"]; a, b = p["events"][i - 1], p["events"][i]; st = STEP[(cs, b["step"])]
    prompt = ("You audit event order in a coded ATLAS AI-incident case study. Two events from the SAME step are listed. "
              "Decide whether the source text supports that event A happened before event B. Accept only: "
              "(b) an explicit order expression (then, after, once, when…, resulting in, causing) or "
              "(c) a processing–result relation stated in the text (a call → what it produced; an input → the output produced from it; code produced → that code executed; a value obtained → the output containing it). "
              "A relative clause such as 'which included' is NOT order evidence. If neither is supported, answer none.\n\n"
              f"CASE {cs} SUMMARY:\n{DESC.get(cs, '')}\n\nSTEP {b['step']}:\n{st['text']}\n\n"
              f"Event A: {', '.join(n['code'] for n in a['nodes'])}\nEvent B: {', '.join(n['code'] for n in b['nodes'])}\n\n"
              'Return JSON: {"type":"b"|"c"|"none","quote":"<shortest verbatim phrase showing the order, or empty>","why":"<one short sentence>"}')
    try: o = ask(prompt)
    except Exception as ex: return job, ("error", str(ex)[:120], False)
    t = o.get("type") if o.get("type") in ("b", "c", "none") else "none"
    q = (o.get("quote") or "").strip()
    return job, (t, q + (" — " + o.get("why", "") if o.get("why") else ""), verbatim(q, cs, b["step"]) if q else False)

if not NO_LLM:
    with cf.ThreadPoolExecutor(8) as ex:
        for (p, e, n), d in ex.map(do_detail, detail_jobs): n["detail"] = d
        for (p, i), (t, why, ok) in ex.map(do_order, order_jobs):
            e = p["events"][i]; a = p["events"][i - 1]
            fk = (p["case"], e["step"], a["nodes"][-1]["code"], e["nodes"][0]["code"])
            if fk in ORDER_FIX:
                e["order"] = ORDER_FIX[fk]; e["order_by"] = "Human (correction of the LLM judgment)"; continue
            e["order"] = ("cut" if t in ("none", "error") else t, why, )
            e["order_by"] = "LLM" + ("" if ok or t in ("none",) else " · the evidence quote does not match the source — needs review")
            if t == "none": e["flags"].append("The LLM could not find same-step ordering evidence → the path is cut (P6) — needs review")
else:
    for p, e, n in detail_jobs: n["detail"] = {"status": "pending", "what": "", "quote": ""}
    for p, i in order_jobs: p["events"][i]["order"] = ("pending", "")

json.dump(CACHE, open(CACHE_P, "w"), ensure_ascii=False)
# records outside the path (pre-injection legitimate calls · held)
background = []
for cs, c in ST.items():
    for s in c["steps"]:
        for n in s["nodes"]:
            if n.get("status") == "del": continue
            note = n.get("note", "")
            if note.startswith("[pre-injection]"):
                keep = (cs, s["step_id"]) == ("CS0053", "S06")
                background.append({"case": cs, "step": s["step_id"], "node": n["node"], "note": note, "r4": "Path included (poisoned-implementation execution, P10 exception)" if keep else "background record · path excluded (P10)"})
            elif n.get("status") == "hold":
                background.append({"case": cs, "step": s["step_id"], "node": n["node"], "note": note, "r4": "CS0045 S06 HD-UI — accepted (S06 approval request + S07 disguised command), user approval unconfirmed (GPT)"})

# reason-code steps
reason_steps = [{"case": cs, "step": s["step_id"], "reason": ("SCOPE (NOAGENT)" if s.get("reason") == "NOAGENT" else s.get("reason")), "note": s.get("note", "")}
                for cs, c in ST.items() for s in c["steps"] if not [n for n in s["nodes"] if n.get("status") != "del"]]
for cs, step, why in EXTRA_FLAGS:
    background.append({"case": cs, "step": step, "node": "—", "note": "", "r4": "Needs review: " + why})

json.dump({"status": "r4 re-judgment draft — before human · GPT review", "codebook": "1_definitions/r4_draft/DEFINITIONS_r4_EN.md",
           "paths": paths, "background": background, "reason_steps": reason_steps},
          open(OUT / "R4_CODING_DRAFT.json", "w"), ensure_ascii=False, indent=1)
c = collections.Counter()
for p in paths:
    for e in p["events"]:
        c["events"] += 1; c["order_" + e["order"][0]] += 1
        for n in e["nodes"]:
            c["nodes"] += 1
            if n.get("detail"): c["detail_" + n["detail"].get("status", "?")] += 1
            if not n.get("quote"): c["no_quote"] += 1
print(dict(c)); print("flags:", sum(len(e["flags"]) for p in paths for e in p["events"]) + len(EXTRA_FLAGS))
