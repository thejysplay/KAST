# -*- coding: utf-8 -*-
"""Reference implementation for AgentSpec-based capability mapping.

The published mapping uses Gemini 2.5 Pro at temperature 0. This script records
raw and parsed judgments with model and input-hash metadata. Required AgentSpecs,
definitions and prompt files are not all bundled; this is not a standalone
regenerator of the released capability map.
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--ids", nargs="+", required=True)
ap.add_argument("--tag", required=True)
ap.add_argument("--model", default="gemini-2.5-pro")
ap.add_argument("--specs", default=str(HERE.parent / "agent_specs_v3_r2" / "specs"))
ap.add_argument("--defs", default=str(ROOT / "1_definitions" / "definitions_v2_en.json"))
ap.add_argument("--defs-md", default=None, help="English definition document")
ap.add_argument("--strip-injection", action="store_true", help="Omit experiment-specific injection annotations from the mapping input")
a = ap.parse_args()

import re as _re
if a.defs_md:
    _md = Path(a.defs_md).read_text(encoding="utf-8")
    _md = _re.sub(r"<!--.*?-->", "", _md, flags=_re.S)
    _secs = _re.split(r"(?m)^(?=## )", _md)
    _keep = [x for x in _secs if _re.match(r"## (2|3|4|5)\. ", x)]
    assert len(_keep) == 4, [x[:30] for x in _secs]
    NODE_DEFS = "".join(_keep).strip()
    assert NODE_DEFS.count("PA-GA") > 0
else:
  D = json.loads(Path(a.defs).read_text(encoding="utf-8"))
  assert len(D["nodes"]) == 17
  NODE_DEFS = json.dumps({
    "units": [{"code": u[0], "name": u[1], "question": u[2], "axis": u[3], "definition": u[5] if len(u) > 5 else None} for u in D["units"]],
    "nodes": [{k: n.get(k) for k in ("code", "unit", "name", "def", "cues", "nots", "nb") if k in n} for n in D["nodes"]],
    "assignment_rules": [{"id": r[0], "title": r[1], "text": r[2]} for r in D["rules"]],
    "path_rules": D.get("path_rules"),
  }, ensure_ascii=False, indent=1)
TPL = (HERE / "prompts" / "mapping_prompt_en.md").read_text(encoding="utf-8")
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_key():
    if os.getenv("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    env = Path(os.environ["SPECTRA_ENV_FILE"])
    for ln in env.read_text().splitlines():
        if ln.startswith("GEMINI_API_KEY="):
            return ln.split("=", 1)[1].strip().strip('"')
    raise SystemExit("GEMINI_API_KEY not found")


from google import genai
client = genai.Client(api_key=load_key())
import yaml
(HERE / "out").mkdir(exist_ok=True); (HERE / "raw").mkdir(exist_ok=True)
for sid in a.ids:
    spec_yaml = (Path(a.specs) / f"{sid}.yaml").read_text(encoding="utf-8")
    spec = yaml.safe_load(spec_yaml)
    if a.strip_injection:
        for ip in spec.get("input_points") or []: ip.pop("injection", None)
    spec_json = json.dumps(spec, ensure_ascii=False, indent=1, default=str)
    prompt = TPL.replace("{AGENT_SPEC}", spec_json).replace("{NODE_DEFINITIONS}", NODE_DEFS)
    text, err, usage = "", None, None
    for attempt in range(4):
        try:
            r = client.models.generate_content(model=a.model, contents=prompt,
                config={"temperature": 0, "max_output_tokens": 65536, "response_mime_type": "application/json"})
            text = (r.text or "").strip()
            usage = getattr(r, "usage_metadata", None)
            if text:
                break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:300]}"; time.sleep(10 * (attempt + 1))
    (HERE / "raw" / f"{sid}.{a.tag}.txt").write_text(text, encoding="utf-8")
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception as e:
        err = (err or "") + f" | parse: {e}"
    if parsed is not None:
        (HERE / "out" / f"{sid}.{a.tag}.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=1), encoding="utf-8")
    meta = {"id": sid, "tag": a.tag, "model": a.model, "temperature": 0, "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "spec_sha256": sha(spec_yaml), "spec_dir": a.specs, "defs": a.defs_md or a.defs, "strip_injection": a.strip_injection, "definitions_sha256": sha(NODE_DEFS), "prompt_template_sha256": sha(TPL),
            "prompt_sha256": sha(prompt), "prompt_chars": len(prompt), "parsed": parsed is not None, "error": err,
            "usage": {k: getattr(usage, k, None) for k in ("prompt_token_count", "candidates_token_count", "thoughts_token_count", "total_token_count")} if usage else None}
    (HERE / "out" / f"{sid}.{a.tag}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(sid, a.tag, "ok" if parsed is not None else f"FAIL {err}", meta["usage"], flush=True)
