# AI Novel Agent Evaluation Report

- Mode: `mock`
- Generated: 2026-08-13 22:29:01

## Retrieval

| variant | hit_rate | precision@3 | context_relevance |
| --- | --- | --- | --- |
| budget | 100.00% | 33.33% | 37.18% |
| keyword | 100.00% | 33.33% | 41.38% |

## Agent Pipeline

- Task Success: 100.00%
- Reviewer Detection: 100.00%
- Average Quality: 92.5
- Average Latency: 2.9 ms
- Average Tokens: 4576
- Total Estimated Cost: 0.000000

| id | retriever | memory | review | status | quality | latency_ms | llm_calls | tokens | cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chapter-baseline | keyword | True | True | success | 100 | 4.4 | 6 | 5378 | 0.000000 |
| chapter-baseline | keyword | True | False | success | 100 | 2.9 | 5 | 4484 | 0.000000 |
| chapter-baseline | keyword | False | True | success | 100 | 2.4 | 4 | 3700 | 0.000000 |
| chapter-baseline | keyword | False | False | success | 100 | 1.7 | 3 | 2806 | 0.000000 |
| reviewer-injection | keyword | True | True | success | 70 | 4.2 | 8 | 7057 | 0.000000 |
| reviewer-injection | keyword | True | False | success | 100 | 3.2 | 5 | 4672 | 0.000000 |
| reviewer-injection | keyword | False | True | success | 70 | 3.1 | 6 | 5635 | 0.000000 |
| reviewer-injection | keyword | False | False | success | 100 | 1.8 | 3 | 2880 | 0.000000 |
