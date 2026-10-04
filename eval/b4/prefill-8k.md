# Load test: prefill-8k

| Agents | Calls | Errors (timeouts) | TTFT p50 | TTFT p95 | Call p50 | Call p95 | Decode tok/s per call | Output tok/s | Prompt tok/s | Incidents/hour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 7 | 0 (0) | 3.9 s | 26.6 s | 23.9 s | 45.8 s | 13.1 | 8.9 | 243 | 31.8 |
| 2 | 12 | 0 (0) | 2.1 s | 29.4 s | 32.7 s | 67.4 s | 10.4 | 14.9 | 369 | 43.8 |
| 4 | 11 | 0 (0) | 17.2 s | 44.1 s | 82.7 s | 177.1 s | 7.5 | 17.8 | 410 | 36.1 |
| 8 | 9 | 0 (0) | 125.0 s | 152.2 s | 207.7 s | 282.1 s | 4.9 | 14.4 | 295 | 25.2 |
