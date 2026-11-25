# -*- coding: utf-8 -*-
"""Produce an independent codebook-based annotation for each ATLAS case step.

The coder receives the English codebook, case description, full procedure and
target step. The prompt excludes reference labels and coded examples. The study
used Gemini 2.5 Flash at temperature 0 across 255 steps. The reference script
requires additional source files and model access."""
import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); import paths as P
sys.path.insert(0, str(HERE)); import backend
import yaml

CODEBOOK_MD = HERE.parent / "1_definitions/r4_draft/DEFINITIONS_r4_EN.md"
MODELS = {"gemini-pro": "gemini-2.5-pro", "gemini": "gemini-2.5-flash"}
RAW = HERE / "out" / "raw_r4"     # out/raw_r4/<model>/<case>_<step>.json — one debug file per step


def build_codebook():
    t = CODEBOOK_MD.read_text(encoding="utf-8")
    a = t.index("## 2. Units"); b = t.index("## 7. Path rules")
    keep, skip = [], False
    for ln in t[a:b].splitlines():
        if ln.strip().startswith("- **Source examples:**"): skip = True; continue
        if skip and (ln.startswith("  -") or not ln.strip()):
            if not ln.strip(): skip = False; keep.append(ln)
            continue
        skip = False; keep.append(ln)
    keep = [re.sub(r"\s*\(CS\d{4}[^)]*\)", "", ln) for ln in keep]   # drop parenthetical pointers to our own coded steps
    cb = "# CODEBOOK r4 — Unit / Attack Node definitions (English canonical). Apply exactly.\n\n" + "\n".join(keep)
    return cb.replace("**", "")


CB = build_codebook()
CASES = json.loads(P.CODING.read_text(encoding="utf-8"))["cases"]
_Y = yaml.safe_load(P.ATLAS.read_text(encoding="utf-8"))["case-studies"]
def _clean(x):
    x = re.sub(r'</?(?:div|span|br|p|b|i|u|em|strong|ul|ol|li|a|code|pre|sup|sub|img|table|tr|td|th)\b[^>]*>', ' ', str(x), flags=re.I)
    return re.sub(r'\s+', ' ', x).strip()
DESC = {cid: _clean(_Y["AML." + cid].get("description", "")) for cid in CASES}

PROMPT = """You are an independent coder applying the codebook below to ONE step of a MITRE ATLAS case study.
Read the case description and the full procedure for context, but code ONLY the target step. Evidence for a fact of the
target step may come from the target step itself, from another step of the same case, or from the case description; say
where. Follow the codebook strictly: actual occurrence only; several facts per step are allowed; PA-GA is written
together with the action Node it qualifies (e.g. "EXE-AT+PA-GA"); no Node for the model's decision to follow an
instruction; content that is not an Agent fact gets a reason code instead of a Node.

{codebook}

Return JSON only:
{{"facts": [{{"fact": "<short English description>", "quote": "<exact phrase from the evidence>", "where": "<target | step S## | description>", "node": "<Attack Node code, with +PA-GA if it applies, or empty>", "reason": "<reason code if no node, else empty>"}}]}}
If the target step has no Agent fact, return one item with node "" and the reason code.

CASE: {case}
CASE DESCRIPTION:
{desc}

FULL PROCEDURE:
{proc}

TARGET STEP {sid}:
{text}
"""

_client = None
import threading
_tl = threading.local()
def _log():
    if not hasattr(_tl, "log"): _tl.log = []
    return _tl.log
def call(prompt, model):
    global _client
    LOG = _log()
    from google import genai
    backend._load_key()
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    last = ""
    for attempt in range(4):
        try:
            r = _client.models.generate_content(model=model, contents=prompt,
                                                config={"temperature": 0, "max_output_tokens": 16384, "response_mime_type": "application/json"})
            u = r.usage_metadata
            usage = {"prompt": getattr(u, "prompt_token_count", 0) or 0, "output": getattr(u, "candidates_token_count", 0) or 0,
                     "thoughts": getattr(u, "thoughts_token_count", 0) or 0}
            txt = (getattr(r, "text", "") or "").strip()
            fr = str(getattr(r.candidates[0], "finish_reason", "")) if getattr(r, "candidates", None) else ""
            LOG.append({"attempt": attempt, "raw": txt, "finish_reason": fr, "usage": usage})
            if txt: return backend._parse_json(txt), usage
            last = "empty text"
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:200]}"; LOG.append({"attempt": attempt, "error": repr(e)[:2000]}); time.sleep(5 * (attempt + 1))
    raise RuntimeError(last)


def unwrap(facts):
    out = []
    for f in facts or []:
        if isinstance(f, dict) and "facts" in f and "fact" not in f: out += unwrap(f["facts"])
        else: out.append(f)
    return out


def run(job, model):
    cid, c, s = job
    proc = "\n".join(f"{x['step_id']}: {x['text']}" for x in c["steps"])
    p = PROMPT.format(codebook=CB, case=c["name"], desc=DESC.get(cid, ""), proc=proc, sid=s["step_id"], text=s["text"])
    _tl.log = []
    def dump(res):   # full debug record per step: prompt, every attempt's raw text / error, parsed result
        d = RAW / model; d.mkdir(parents=True, exist_ok=True)
        (d / f"{cid}_{s['step_id']}.json").write_text(json.dumps({"case": cid, "step": s["step_id"], "model": MODELS[model],
            "time": time.strftime("%Y-%m-%d %H:%M:%S"), "attempts": _tl.log, "result": res, "prompt": p}, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        r, usage = call(p, MODELS[model])
        facts = unwrap(r.get("facts") if isinstance(r, dict) else (r if isinstance(r, list) else None))
        res = {"case": cid, "step": s["step_id"], "facts": None, "error": "empty: " + str(r)[:200]} if not facts else {"case": cid, "step": s["step_id"], "facts": facts}
        dump(res); return res, usage
    except Exception as e:
        res = {"case": cid, "step": s["step_id"], "facts": None, "error": repr(e)[:300]}; dump(res); return res, None


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="gemini-pro"); ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--steps", default=None, help="Comma-separated CASE:STEP identifiers for a subset of steps."); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    out = HERE / "out" / f"{a.model}-r4"; out.mkdir(parents=True, exist_ok=True)
    (out / "codebook.md").write_text(CB, encoding="utf-8", newline="\n")
    leaks = sorted(set(re.findall(r"CS\d{4}", CB)))
    print(f"codebook {len(CB)} chars; case ids left in codebook: {leaks}")
    jobs = [(cid, c, s) for cid, c in sorted(CASES.items()) for s in c["steps"]]
    if a.steps:
        want = {tuple(x.split(":")) for x in a.steps.split(",")}; jobs = [j for j in jobs if (j[0], j[2]["step_id"]) in want]
    f, fu = out / "coding.json", out / "usage.json"
    done = {(r["case"], r["step"]): r for r in json.loads(f.read_text())} if f.exists() else {}
    used = json.loads(fu.read_text()) if fu.exists() else {}
    todo = [j for j in jobs if done.get((j[0], j[2]["step_id"]), {}).get("facts") is None]
    print(f"jobs {len(jobs)} · to run {len(todo)}")
    if a.dry: sys.exit(0)
    with ThreadPoolExecutor(a.workers) as ex:
        for r, u in ex.map(lambda j: run(j, a.model), todo):
            done[(r["case"], r["step"])] = r
            if u: used[f"{r['case']}:{r['step']}"] = u
    order = [(cid, s["step_id"]) for cid, c in sorted(CASES.items()) for s in c["steps"]]
    f.write_text(json.dumps([done[k] for k in order if k in done], ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    fu.write_text(json.dumps(used, indent=1), encoding="utf-8", newline="\n")
    tot = {k: sum(v[k] for v in used.values()) for k in ("prompt", "output", "thoughts")}
    print(f"done {sum(1 for k in order if k in done and done[k]['facts'] is not None)} · failed {sum(1 for k in order if k in done and done[k]['facts'] is None)} · tokens {tot}")
