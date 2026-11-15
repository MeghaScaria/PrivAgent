# WP6 task set hash

`experiments/v2/wp6_tasks.json` SHA-256: `fd2f48a648f036c0ec51751683e1281ba19e1507526f7f7ea3302c840ad7927d`

40 benign + 40 attack tasks; development subset (6): ben_ans_hr_performance, ben_send_public_newsletter, ben_send_hr_partner, atk_web_agentdojo_salary, atk_doc_injecagent_hr, atk_doc_injecagent_finance.

Recorded before any real-LLM run. Every pilot result file records this hash; a run against a different task file is refused.

## Version 2

`experiments/v2/wp6_tasks_v2.json` SHA-256: `68f688f9da5e034c5e15df040028c870f9f1e6d287257a13d303db0472614ee7`

40 benign + 80 attack tasks: family A 60 (of which 20 use the AgentDojo important_instructions structure), family B (assumed compromise of the writer) 20. Version 1's tasks are included unchanged. Development subsets (6 each): A: ben_ans_hr_performance, ben_send_public_newsletter, ben_send_hr_partner, atk_web_agentdojo_salary, atk_doc_injecagent_hr, atk_doc_injecagent_finance; A_strong: ben_ans_hr_performance, ben_send_public_newsletter, ben_send_hr_partner, atk_web_important_salary, atk_doc_important_hr, atk_doc_important_finance; B: ben_ans_hr_performance, ben_send_public_newsletter, ben_send_hr_partner, atk_b_salary, atk_b_hr, atk_b_finance.

Recorded before any run on version 2. Version 1 (above) is unchanged.
