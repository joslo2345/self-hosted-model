# B4 cost model

Tokens per incident (mean of the 20 B1 runs): 38,614 prompt (3,231 first call, 9,243 new on later calls, 26,140 repeated prefix), 1,470 output.

## Hosted (per incident, prompt caching on)

| Model | Per incident | Per 1,000 | If thinking triples output |
| --- | --- | --- | --- |
| claude-opus-5-5 | $0.0970 | $97 | $156 |
| claude-sonnet-5-5 | $0.0511 | $51 | $81 |
| claude-haiku-4-5 | $0.0256 | $26 | $40 |

## Self-hosted A100 (estimated)

Estimated capacity of one A100: 1,473 incidents/hour with prefix caching, 579 without (prefill 6,933 tok/s at 40% MFU; decode step 7.0 ms at 70% of bandwidth; batch 16). Weight cache: $16/month.

| GPU | $/hour | Cost/day, 1 replica always on | Per 1,000 at full use | Break-even vs Opus 5.5 | vs Sonnet 5.5 | vs Haiku 4.5 |
| --- | --- | --- | --- | --- | --- | --- |
| A100 on demand | $3.673 | $88.68 | $2.49 | 914/day | 1,735/day | 3,470/day |
| A100 spot | $0.679 | $16.82 | $0.46 | 173/day | 329/day | 658/day |

## Laptop (measured, for scale)

Latency target: model call p95 <= 60 s, no timeouts.

| Config | Best incidents/hour within target (agents) | Peak incidents/hour (agents) |
| --- | --- | --- |
| baseline | 32 (1) | 44 (2) |
| no-prefix-cache | none | 20 (1) |
| prefill-8k | 32 (1) | 44 (2) |
