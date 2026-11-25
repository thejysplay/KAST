# Study artifacts

| Stage | Published material |
|---|---|
| Case selection | [Selected MITRE ATLAS cases and selection criteria](0_case_selection/case_selection.json) |
| Case coding | [Intermediate event annotations](1_attack_coding/attack_coding.json) and [independent coding agreement](2_coding_reliability/coding_reliability_kappa.json) |
| Threat knowledge | [Reviewed graph summary](3_threat_knowledge/threat_knowledge/summary.json), [behavior transitions](3_threat_knowledge/transition_graph.json), and [candidate paths](3_threat_knowledge/skeletons.json) |
| Target mapping | [Capability judgments by environment](4_capability_mapping/capability_mapping.json) and [mapping provenance](4_capability_mapping/PROVENANCE.md) |
| Scenario selection | [Selected units](5_scenario_generation/per_env_units_selected/) and [selection counts by environment](5_scenario_generation/per_env_build_report/SELECTION_FINAL.md) |
| Execution and judgment | [Per-environment judgments](6_execution_judgment/per_env_judged_results/) and [retained-run totals](6_execution_judgment/results_summary.md) |
| Evaluation | [Reported metrics and aggregation rules](7_paper_numbers/PAPER_NUMBERS.md) and [ATLAS technique annotations](8_technique_coverage/README.md) |

The intermediate coding record contains 154 events. The reviewed graph uses 152. Stages 0–6 include reference implementations that require additional inputs or benchmark environments. In particular, the reference selector assigns one resource pair to each selected path, while the published selection can include multiple pairs for a path.
