# Spike test

Phases: 60 s at 0.05 req/s, 180 s at 0.4 req/s, 120 s at 0.05 req/s
Requests: 81 sent, 0 failed. TTFT p50 75s, p95 202s, max 206s.

| Milestone (from spike start) | Time |
| --- | --- |
| Requests waiting above target (2) | +17 s |
| KEDA asks for another replica | +44 s |
| New pod created | +44 s |
| New pod Ready | +96 s |
| Scaled back down | +527 s |
| Alert VLLMTimeToFirstTokenHigh firing | +260 s |

Per 30 s window (TTFT of requests sent in the window):

| t (s) | sent | errors | TTFT p50 | TTFT p95 | max waiting | desired | ready | pending |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | 0 | 3.1s | 7.3s | 0.0 | 1 | 1 | 0 |
| 30 | 1 | 0 | 3.2s | 3.2s | 0.0 | 1 | 1 | 0 |
| 60 | 12 | 0 | 14s | 25s | 4.0 | 1 | 1 | 0 |
| 90 | 12 | 0 | 69s | 104s | 11 | 2 | 1 | 0 |
| 120 | 12 | 0 | 153s | 184s | 19 | 2 | 1 | 0 |
| 150 | 12 | 0 | 187s | 201s | 22 | 2 | 2 | 0 |
| 180 | 12 | 0 | 53s | 206s | 31 | 2 | 2 | 0 |
| 210 | 12 | 0 | 75s | 202s | 39 | 2 | 2 | 0 |
| 240 | 2 | 0 | 190s | 201s | 39 | 2 | 2 | 0 |
| 270 | 1 | 0 | 173s | 173s | 34 | 2 | 2 | 0 |
| 300 | 2 | 0 | 18s | 136s | 28 | 2 | 2 | 0 |
| 330 | 1 | 0 | 5.9s | 5.9s | 24 | 2 | 2 | 0 |
| 360 | 0 | 0 | - | - | 20 | 2 | 2 | 0 |
| 390 | 0 | 0 | - | - | 15 | 2 | 2 | 0 |
| 420 | 0 | 0 | - | - | 7.0 | 2 | 2 | 0 |
| 450 | 0 | 0 | - | - | 3.0 | 2 | 2 | 0 |
| 480 | 0 | 0 | - | - | 0.0 | 2 | 2 | 0 |
| 510 | 0 | 0 | - | - | 0.0 | 2 | 2 | 0 |
| 540 | 0 | 0 | - | - | 0.0 | 2 | 2 | 0 |
| 570 | 0 | 0 | - | - | 0.0 | 1 | 1 | 0 |
| 600 | 0 | 0 | - | - | 0.0 | 1 | 1 | 0 |
| 630 | 0 | 0 | - | - | 0.0 | 1 | 1 | 0 |
