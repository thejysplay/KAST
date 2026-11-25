# Evaluation results

Run `bash reproduce.sh` in this directory to aggregate the stored records offline. See the [primary output](outputs/recompute_final.json) and [benchmark comparison](outputs/recompute_builtin.json).

## Results by environment

The denominator is the [5,014 selected generation units](selected_5014_ids.txt), including generation failures. Ten DailyLife SC-SYS units are excluded. A success requires goal achievement after delivery in the first execution.

| Environment | Selected | Generation passed | Successful |
|---|---:|---:|---:|
| AgentDojo banking | 29 | 29 | 12 |
| AgentDojo Slack | 34 | 31 | 9 |
| AgentDojo travel | 96 | 92 | 46 |
| AgentDojo workspace | 294 | 283 | 95 |
| AgentDyn daily life | 236 | 201 | 51 |
| AgentDyn GitHub | 252 | 208 | 28 |
| AgentDyn shopping | 205 | 176 | 36 |
| AppWorld | 3,646 | 3,393 | 563 |
| Cline | 127 | 122 | 44 |
| OpenHands | 95 | 80 | 29 |
| **Total** | **5,014** | **4,615** | **913** |

Of the 3,786 delivered runs with assessable outcomes, 848 met tool goals and 65 met response goals. Together these account for 18.2% of the selected units.

| Measure | Result |
|---|---|
| Distinct goal items reached | 406 of 689 (58.9%). A goal item pairs an environment with a tool or response type. |
| Goal items by path group | 31 from observed paths and 401 from recombined paths. The sets share 26 items, leaving 375 reached only by recombined paths. |
| Intermediate tools called in order | Of 825 successful runs with verifiable intermediate tools, 551 called all of them in order after delivery without errors. Another 88 had no verifiable intermediate tool. |
| Reach across ten environments | 390 environment–tool pairs and 51 ATLAS techniques, including 18 Impact/Exfiltration techniques. |

## Comparison on seven shared benchmark environments

| Measure | KAST | Built-in attacks |
|---|---:|---:|
| Executed runs | 1,020 | 1,189 |
| Goal tools reached (counted per environment) | 97 | 38 |
| ATLAS techniques observed in successful runs | 38 | 34 |
| Impact/Exfiltration techniques | 14 | 12 |

The methods share 23 goal tools and 34 techniques. Executed-run totals include undelivered runs and execution errors. Technique counts use stored `effect_observed` labels within the 139-technique catalogue, with the 15 IDs in `MISLABEL` excluded. See the [annotation scope](../8_technique_coverage/README.md).

## How the stored success counts relate

| Successes | Counting rule |
|---:|---|
| 1,000 | [Retained runs after argument checks](../6_execution_judgment/results_summary.md), including follow-up attempts |
| 885 | First runs after excluding 115 follow-up successes |
| **913** | Paper result. Includes 38 additional post-delivery early achievements and excludes 10 quotation-only responses. |
| 1,028 | Diagnostic total after applying the same early-achievement and response-goal rules to retained runs |

A response goal requires the agent to present the specified content as its own reply. For user-inducement goals, the agent must recommend the specified action to the user. The [response-goal corrections](reply_adjudication.json) are applied to the stored judgments. The review focused on reported successes. The original screening did not assess every message sent outside the chat. The raw data preserve the original execution-time judgments.

Of the 742 IDs with an undelivered first execution, 419 had delivery on follow-up and 115 met their goals. The other 323 follow-ups were undelivered or failed generation. The 38 early achievements exclude one of 39 candidates because its goal was a required benign action.
