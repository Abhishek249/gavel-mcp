# Verified benchmark — 2026-09-10

This report records the first independently executed Gavel MCP benchmark on GitHub Actions.

- Workflow run: [34443656200](https://github.com/Abhishek249/gavel-mcp/actions/runs/34443656200)
- Job: [102763697723](https://github.com/Abhishek249/gavel-mcp/actions/runs/34443656200/job/102763697723)
- Commit tested: `e8dfff4816a5852cb85dd50f4a47d7900dd8a443`
- Runner: GitHub-hosted Ubuntu 24.04, Python 3.12.14
- Result: **PASS**

## Verification results

| Signal | Measured result |
|---|---:|
| Unit/integration tests | 12 passed |
| Code coverage | 91% |
| MCP benchmark trials | 40 |
| Defect trials | 32 |
| Clean trials | 8 |
| Detected defects | 32/32 |
| False negatives | 0 |
| Clean runs accepted | 8/8 |
| False positives | 0 |
| Detection recall | 100% |
| False-positive rate | 0% |
| Required-diagnostic accuracy | 100% |
| MCP call latency p50 | 3.213 ms |
| MCP call latency p95 | 5.263 ms |

The benchmark opened a real MCP stdio session, initialized the protocol, discovered both published
tools, and invoked the validation server across four deterministic seeds, two dataset sizes, one
clean scenario, and four controlled defect classes.

## Scope

These figures measure Gavel against its published deterministic benchmark on a GitHub-hosted
runner. They establish reproducibility and behavior for the tested fault model. They do not establish
performance or detection accuracy for arbitrary production pipelines. External geospatial-pipeline
validation is a separate milestone.
