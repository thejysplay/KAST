# Capability-mapping records

The released judgments use Gemini 2.5 Pro, temperature 0, with two runs per environment.
The final status is active only when both runs mark the Node active.

| Record | Contents |
|---|---|
| [capability_mapping.json](capability_mapping.json) | Final per-environment Node statuses. |
| [mapping_runs_status.json](provenance/mapping_runs_status.json) | Status-only `run1`, `run2` and `final` values; the final values match the capability map. |
| [Input manifests](provenance/) | Original input SHA-256 hashes, capability statuses and intermediate selection counts. |

The [environment tables](../5_scenario_generation/per_env_build_report/) give the candidate counts after mapping.
The [selection summary](../5_scenario_generation/per_env_build_report/SELECTION_FINAL.md) lists the units selected for evaluation.

Full mapping rationales and AgentSpec files are unavailable in this release. The manifests identify the original inputs by hash.
The public path file was reserialized for release and has a different byte hash from the original.
