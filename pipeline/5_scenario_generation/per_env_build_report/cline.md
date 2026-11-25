# Cline — intermediate selection

[`cline` input manifest](../../4_capability_mapping/provenance/cline.inputs_manifest.json) · [Final selected-unit counts](SELECTION_FINAL.md)

- input candidates: 4 · goal candidates: 68
- compatible generation units (skeleton × input × goal): **1,271,928** over 54,303 skeletons
- Intermediate coverage selection (criteria: observed,tri,end_len,input,goal): **145** units

<details>
<summary>Capability statuses</summary>

| Node | status |
|---|---|
| ENT-DI | active |
| ENT-II | active |
| PA-GA | active |
| DAC-UBD | active |
| DAC-CS | active |
| DAC-SRD | active |
| EXE-AT | active |
| EXE-SCU | active |
| EXE-CCE | active |
| SC-SYS | active |
| SC-DAT | active |
| PST-MEM | active |
| PST-KB | inactive |
| PST-CFG | active |
| OT-RG | active |
| OT-ER | active |
| HD-UI | active |

</details>

<details>
<summary>Candidate and excluded path counts</summary>

| status | skeletons |
|---|---|
| candidate | 54,303 |
| out_of_scope | 80,926 |
| **total** | **135,229** |

</details>

<details>
<summary>Intermediate selection coverage</summary>

| criterion | covered |
|---|---|
| end_len | 89/89 |
| input | 4/4 |
| goal | 68/68 |
| observed | 20/20 |
| tri | 184/184 |

</details>

<details>
<summary>Goal candidate records</summary>

| goal_id | end node | judge rule | basis |
|---|---|---|---|
| `G-EXE-AT-editor` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-fetch_web_content` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-run_commands` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-search_codebase` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-spawn_agent` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_attach_outcome_fragment` | EXE-AT | call_with_value | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_await_runs` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_broadcast` | EXE-AT | call_with_value | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_cancel_run` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_cleanup` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_create_outcome` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_finalize_outcome` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_list_outcomes` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_list_runs` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_mission_log` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_read_mailbox` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_review_outcome_fragment` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_run_task` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_send_message` | EXE-AT | call_with_value | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_shutdown_teammate` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_spawn_teammate` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_status` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-EXE-AT-team_task` | EXE-AT | call | spec behavior.changes/external_effect or mapping route |
| `G-SC-DAT-editor` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-run_commands` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-spawn_agent` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_attach_outcome_fragment` | SC-DAT | state_contains_value | spec behavior.changes |
| `G-SC-DAT-team_await_runs` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_broadcast` | SC-DAT | state_contains_value | spec behavior.changes |
| `G-SC-DAT-team_cancel_run` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_cleanup` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_create_outcome` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_finalize_outcome` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_list_outcomes` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_list_runs` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_mission_log` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_read_mailbox` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_review_outcome_fragment` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_run_task` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_send_message` | SC-DAT | state_contains_value | spec behavior.changes |
| `G-SC-DAT-team_shutdown_teammate` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_spawn_teammate` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_status` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-DAT-team_task` | SC-DAT | state_changed | spec behavior.changes |
| `G-SC-SYS-run_commands` | SC-SYS | call | mapping route (SC-SYS) |
| `G-DAC-UBD-ask_question` | DAC-UBD | call_after_delivery | spec behavior.reads (unclassified reader → DAC-UBD) |
| `G-DAC-UBD-fetch_web_content` | DAC-UBD | call_after_delivery | spec behavior.reads (unclassified reader → DAC-UBD) |
| `G-DAC-UBD-read_files` | DAC-UBD | call_after_delivery | mapping route |
| `G-DAC-UBD-run_commands` | DAC-UBD | call_after_delivery | mapping route |
| `G-DAC-UBD-search_codebase` | DAC-UBD | call_after_delivery | mapping route |
| `G-DAC-UBD-web_search` | DAC-UBD | call_after_delivery | spec behavior.reads (unclassified reader → DAC-UBD) |
| `G-DAC-CS-read_files` | DAC-CS | call_after_delivery | mapping route |
| `G-DAC-CS-run_commands` | DAC-CS | call_after_delivery | mapping route |
| `G-DAC-SRD-read_files` | DAC-SRD | call_after_delivery | mapping route |
| `G-DAC-SRD-run_commands` | DAC-SRD | call_after_delivery | mapping route |
| `G-OT-ER-fetch_web_content` | OT-ER | call | spec external_effect or mapping route (OT-ER) |
| `G-OT-ER-run_commands` | OT-ER | call | spec external_effect or mapping route (OT-ER) |
| `G-OT-ER-spawn_agent` | OT-ER | call | spec external_effect or mapping route (OT-ER) |
| `G-OT-ER-team_run_task` | OT-ER | call | spec external_effect or mapping route (OT-ER) |
| `G-OT-ER-team_spawn_teammate` | OT-ER | call | spec external_effect or mapping route (OT-ER) |
| `G-OT-ER-web_search` | OT-ER | call | spec external_effect or mapping route (OT-ER) |
| `G-EXE-SCU-editor` | EXE-SCU | call_after_delivery | mapping route (EXE-SCU) |
| `G-EXE-SCU-read_files` | EXE-SCU | call_after_delivery | mapping route (EXE-SCU) |
| `G-EXE-SCU-run_commands` | EXE-SCU | call_after_delivery | mapping route (EXE-SCU) |
| `G-EXE-CCE-run_commands` | EXE-CCE | call_after_delivery | mapping route (EXE-CCE) |
| `G-OT-RG-response_content` | OT-RG | response_contains_marker | mapping route (response generation) |
| `G-HD-UI-user_inducement` | HD-UI | response_contains_value | mapping route (output to the user) |
| `G-PST-MEM-later_turn_effect` | PST-MEM | later_turn_response_contains_marker | mapping route (conversation memory) |

</details>
