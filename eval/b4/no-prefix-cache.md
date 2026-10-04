# Load test: no-prefix-cache

| Agents | Calls | Errors (timeouts) | TTFT p50 | TTFT p95 | Call p50 | Call p95 | Decode tok/s per call | Output tok/s | Prompt tok/s | Incidents/hour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | 0 (0) | 15.3 s | 35.7 s | 33.2 s | 75.7 s | 13.2 | 6.4 | 155 | 19.6 |
| 2 | 5 | 0 (0) | 31.5 s | 40.0 s | 79.4 s | 142.5 s | 10.6 | 7.1 | 173 | 18.2 |
| 4 | 6 | 0 (0) | 52.9 s | 88.3 s | 162.6 s | 203.4 s | 2.6 | 8.2 | 180 | 18.6 |
| 8 | 8 | 5 (5) | 173.8 s | 210.5 s | 287.1 s | 292.7 s | 1.8 | 1.5 | 97 | 8.3 |
