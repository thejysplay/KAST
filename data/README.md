# Evaluation data

| Archive | Contents |
|---|---|
| [Scenarios](scenarios/) | One JSON record per unit. `fixed` identifies the assigned path and goal, `generated` contains the scenario text (or null on generation failure), `checks` records generation checks, and `meta` contains model or error metadata. |
| [Execution traces](traces/) | Retained messages, events, delivery flags, and execution-time judgments. Additional state fields vary by environment. Execution-time [judgments](../pipeline/6_execution_judgment/per_env_judged_results/) are keyed by scenario ID. |
| [First-execution manifests](first_exec/) | IDs whose initial execution was undelivered. For these IDs, the archive contains follow-up records. The original undelivered traces are unavailable. |
| [Built-in attack traces](builtin_traces/) | Benchmark task IDs, messages, and the benchmark's own security and utility outcomes. |

A KAST scenario ID has the form `<environment>__<number>__<path ID>`. The same ID links the scenario, its trace, and its [technique annotations](../pipeline/8_technique_coverage/README.md). Full generation prompts and raw model responses are unavailable in this release.

See the [results and counting rules](../pipeline/7_paper_numbers/PAPER_NUMBERS.md) for how the records enter the paper's evaluation.
