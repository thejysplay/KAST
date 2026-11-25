# Technique annotations

Stored execution annotations were produced by Gemini 2.5 Flash at temperature 0. Coverage counts distinct
`effect_observed` technique IDs in eligible successful runs. Source-case labels in
`../6_execution_judgment/per_env_judged_results/` are separate and do not contribute to these counts.

| File | Contents |
|---|---|
| `trace_atlas_mapping.jsonl.gz` | KAST scenario annotations; `observed` entries contain technique `id`, `status`, and `evidence`. |
| `builtin_atlas_mapping.jsonl.gz` | Built-in attack annotations, keyed by `trace_src`. |
| `atlas_techniques.json` | Catalogue of 139 ATLAS technique IDs and definitions. |
| `atlas_denominators.json` | Impact/Exfiltration subset and counting metadata. |
| `builtin_static_items/<env>.json` | Goal tools (`effect_tools`) for each built-in injection task. |
| `case_mapping.jsonl` | Reference technique annotations for 55 built-in injection-task designs. |
| `run_observations.jsonl` | 55 reference observation records. |
| `failure_causes_per_scenario.json` | Failure-cause labels by scenario. |

See [reported results and aggregation definitions](../7_paper_numbers/PAPER_NUMBERS.md) for coverage by
evaluation scope and the 15-ID exclusion set. [Mapper input limits](TRUNCATION_IMPACT.md) describes the
message-length restriction and its diagnostic.
