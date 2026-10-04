# Spike test

Phases: 60 s at 0.05 req/s, 180 s at 0.4 req/s, 120 s at 0.05 req/s
Requests: 81 sent, 0 failed. TTFT p50 99s, p95 195s, max 205s.

| Milestone (from spike start) | Time |
| --- | --- |
| Requests waiting above target (2) | +15 s |
| KEDA asks for another replica | +40 s |
| New pod created | +40 s |
| New pod Ready | not reached |
| Scaled back down | +535 s |
| Alert VLLMTimeToFirstTokenHigh firing | +254 s |

Per 30 s window (TTFT of requests sent in the window):

| t (s) | sent | errors | TTFT p50 | TTFT p95 | max waiting | desired | ready | pending |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | 0 | 3.2s | 3.3s | 0.0 | 1 | 1 | 0 |
| 30 | 1 | 0 | 3.2s | 3.2s | 0.0 | 1 | 1 | 0 |
| 60 | 12 | 0 | 13s | 24s | 4.0 | 1 | 1 | 0 |
| 90 | 12 | 0 | 43s | 54s | 12 | 2 | 1 | 1 |
| 120 | 12 | 0 | 76s | 89s | 16 | 2 | 1 | 1 |
| 150 | 12 | 0 | 112s | 127s | 24 | 2 | 1 | 1 |
| 180 | 12 | 0 | 148s | 161s | 29 | 2 | 1 | 1 |
| 210 | 12 | 0 | 185s | 197s | 36 | 2 | 1 | 1 |
| 240 | 2 | 0 | 188s | 205s | 37 | 2 | 1 | 1 |
| 270 | 1 | 0 | 172s | 172s | 33 | 2 | 1 | 1 |
| 300 | 2 | 0 | 145s | 155s | 28 | 2 | 1 | 1 |
| 330 | 1 | 0 | 129s | 129s | 25 | 2 | 1 | 1 |
| 360 | 0 | 0 | - | - | 20 | 2 | 1 | 1 |
| 390 | 0 | 0 | - | - | 15 | 2 | 1 | 1 |
| 420 | 0 | 0 | - | - | 10 | 2 | 1 | 1 |
| 450 | 0 | 0 | - | - | 3.0 | 2 | 1 | 1 |
| 480 | 0 | 0 | - | - | 0.0 | 2 | 1 | 1 |
| 510 | 0 | 0 | - | - | 0.0 | 2 | 1 | 1 |
| 540 | 0 | 0 | - | - | 0.0 | 2 | 1 | 1 |
| 570 | 0 | 0 | - | - | 0.0 | 1 | 1 | 0 |
| 600 | 0 | 0 | - | - | 0.0 | 1 | 1 | 0 |
| 630 | 0 | 0 | - | - | 0.0 | 1 | 1 | 0 |
