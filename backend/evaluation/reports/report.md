# AI Novel Agent Evaluation Report

- Mode: `mock`
- Generated: 2026-08-13 22:34:49

## Retrieval

| variant | hit_rate | precision@3 | context_relevance |
| --- | --- | --- | --- |
| budget | 100.00% | 33.33% | 37.18% |
| keyword | 100.00% | 33.33% | 41.38% |

## Agent Pipeline

- Task Success: 100.00%
- Reviewer Detection: 100.00%
- Average Quality: 92.5
- Average Latency: 3.2 ms
- Average Tokens: 4576
- Total Estimated Cost: 0.000000

| id | retriever | memory | review | status | quality | latency_ms | llm_calls | tokens | cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chapter-baseline | keyword | True | True | success | 100 | 4.8 | 6 | 5378 | 0.000000 |
| chapter-baseline | keyword | True | False | success | 100 | 3.0 | 5 | 4484 | 0.000000 |
| chapter-baseline | keyword | False | True | success | 100 | 2.5 | 4 | 3700 | 0.000000 |
| chapter-baseline | keyword | False | False | success | 100 | 2.1 | 3 | 2806 | 0.000000 |
| reviewer-injection | keyword | True | True | success | 70 | 4.3 | 8 | 7057 | 0.000000 |
| reviewer-injection | keyword | True | False | success | 100 | 3.2 | 5 | 4672 | 0.000000 |
| reviewer-injection | keyword | False | True | success | 70 | 3.6 | 6 | 5635 | 0.000000 |
| reviewer-injection | keyword | False | False | success | 100 | 1.8 | 3 | 2880 | 0.000000 |
