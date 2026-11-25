# KAST

Research artifacts for *Reusable Threat Knowledge from Real Attack Cases: Automated Customized Attack Scenario Generation for Agentic AI*.

Testing a new tool-using agent for indirect prompt injection usually starts with an evaluator deciding what to test and what outcome would count as success. KAST (Knowledge-based Attack Scenario Tailoring) automates this initial step. Given an evaluator's description of the target agent, it uses behaviors documented in previous cases to generate test scenarios and their success criteria.

## From documented cases to evaluation scenarios

The study examined 255 steps in 24 selected MITRE ATLAS cases. Using a common set of behavior definitions, the authors identified 41 behavior sequences across 23 cases. One case contained no agent behavior covered by the definitions. The sequences provided 51 distinct transitions between consecutive behaviors. Recombining those transitions and applying the study's structural filters yielded 135,229 candidate paths, including the 41 observed in the source cases.

For each target, the evaluator described its tools, resources, and permissions in an *AgentSpec*. KAST used this specification to identify applicable paths and construct scenarios with goals that could be checked against an execution record. The same case-derived knowledge was used across eight benchmark environments from AgentDojo, AgentDyn, and AppWorld and two coding agents, Cline and OpenHands. All ten used Gemini 2.5 Flash as the target model.

## Evaluation and results

**Generation and goal achievement.** Of the 5,014 units selected for scenario generation, 4,615 (92.0%) passed the generation checks. The study recorded 913 goal successes (18.2% of all selected units). Every environment had at least one recorded success. Cline accounted for 44 and OpenHands for 29.

**Tools reached.** In the seven AgentDojo and AgentDyn environments shared with the built-in attacks, KAST achieved goals for 97 tools, counting each tool once per environment. The built-in attacks reached 38. The two sets shared 23 tools, so KAST achieved goals for 74 tools outside the benchmarks' predefined goal lists.

**Contribution of recombined paths.** Several scenarios can share a goal item, defined by the environment and the target tool or reply type. At least one scenario succeeded for 406 of 689 goal items. Of these, 375 were reached only by scenarios based on recombined paths. For 369 of the 375 items, at least one successful run had designated intermediate tools. For 285 of those 369, a successful run called all of them in the specified order.

**Observed techniques.** Execution records from 907 of the 913 successful KAST runs contained enough evidence for technique mapping. The trace annotations identified 51 distinct MITRE ATLAS techniques across all ten environments. In the seven shared environments, successful KAST runs exhibited 38 techniques, including all 34 observed in successful runs of the built-in attacks. KAST achieved this coverage without using the benchmarks' manually designed goals as input.

## Research materials

- [Experimental data](data/README.md) describes the scenario, execution, and benchmark comparison records.
- [Study artifacts by stage](pipeline/README.md) follows the paper from case selection through evaluation.
- [Results and counting rules](pipeline/7_paper_numbers/PAPER_NUMBERS.md) gives the per-environment results and defines the denominators.
- [Archived release on Zenodo](https://doi.org/10.5281/zenodo.24521076) contains the original version 1.0.0 artifacts. The response-goal adjudication used for the 913 reported successes is available in [the current results](pipeline/7_paper_numbers/PAPER_NUMBERS.md).

To recompute the main evaluation counts offline from the stored records, run the following from the repository root.

```bash
bash pipeline/7_paper_numbers/reproduce.sh
```
