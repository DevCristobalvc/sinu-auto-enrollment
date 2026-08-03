# Cost & Resource Analysis

## Cost per execution

The monitor runs as a **pure script** (`no_agent` cron job) — **no LLM calls are made**, so token cost is **$0.00** per run.

| Resource | Per run | Notes |
|---|---|---|
| LLM tokens | **$0.00** | Deterministic Playwright automation, no AI calls |
| Browser session | ~2 min CPU | One Chrome page via CDP |
| Network | ~5 MB | SINU page + assets |
| Disk (logs) | ~2 KB/run | `--log-file` debug logs |

**Daily cost (48 runs @ 30 min):** $0.00 in tokens + negligible compute.

### Cost comparison: with vs. without LLM

| Approach | Tokens/run | Daily tokens | Daily cost (DeepSeek) |
|---|---|---|---|
| `no_agent` script (this project) | 0 | 0 | **$0.00** |
| LLM agent interpreting JSON | ~2-4K in + ~500 out | ~100-200K | ~$0.10-0.20 |

> The whole point of this design: **the LLM only gets involved when there is something worth saying** (a slot opened / enrolled). Every quiet check is free.

## Why no LLM in the loop

1. **Determinism** — the group table parse and filter logic never "hallucinate" a slot
2. **Latency** — script completes in ~2 min vs. agent loop (login → think → act)
3. **Cost** — 48 silent checks/day cost nothing
4. **Reliability** — a script can't get rate-limited by an LLM provider

## Observability

- **Logs**: `--log-file` writes DEBUG logs (default: `~/.hermes/logs/sinu-watch.log`)
- **Alerting**: the cron wrapper only emits output when a slot opens or an error occurs (watchdog pattern — silent = all good)
