# Eval `test` · qwen-think

Commit `a419152` · model `candidate` · prompt `8c3be535ecec` · judge `off` · 2026-10-03T03:19:10+00:00

| Metric | Value |
| --- | --- |
| Runs with a valid diagnosis | 18/20 |
| **Root-cause accuracy** | **18/20 (90%)** |
| Root-cause accuracy, BMC logs missing | 10/11 (91%) |
| Action allowed by the runbook | 16/20 (80%) |
| Unsafe actions (hardware action on a decoy) | - |
| Missed actions (real fault left in service) | 0/20 (0%) |
| Cites the runbook for the true type | 15/20 (75%) |
| Citation support (judge) | - |
| Latency p50 / p95 | 213.7 s / 382.1 s |
| Tokens per case | 27,062 |
| Cost per case | $0.0 |
| Tool errors / tool calls recovered from text | 0 / 0 |

| Type | Cases | Root cause | Action |
| --- | --- | --- | --- |
| ecc_degradation | 4 | 4 | 4 |
| gpu_off_bus | 4 | 4 | 2 |
| nvlink_degradation | 3 | 3 | 3 |
| pcie_degradation | 3 | 3 | 3 |
| power_fault | 3 | 2 | 2 |
| thermal_runaway | 3 | 2 | 2 |

| Case | Truth | BMC missing | Agent | Action | Runbook | Support | Status | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a6test/f001-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 256 |
| a6test/f022-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | no | - | succeeded | 204 |
| a6test/f006-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 215 |
| a6test/f014-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | replace_part ✗ | yes | - | succeeded | 195 |
| a6test/f008-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | replace_part ✗ | yes | - | succeeded | 168 |
| a6test/f018-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 261 |
| a6test/f009-nvlink_degradation | nvlink_degradation |  | nvlink_degradation | drain_node | yes | - | succeeded | 162 |
| a6test/f013-power_fault | power_fault |  | - ✗ | - ✗ | no | - | error | 407 |
| a6test/f024-pcie_degradation | pcie_degradation |  | pcie_degradation | drain_node | yes | - | succeeded | 188 |
| a6test/f000-power_fault | power_fault | yes | power_fault | replace_part | no | - | succeeded | 177 |
| a6test/f020-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 258 |
| a6test/f021-power_fault | power_fault |  | power_fault | replace_part | no | - | succeeded | 185 |
| a6test/f012-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 157 |
| a6test/f017-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 219 |
| a6test/f007-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 212 |
| a6test/f015-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 261 |
| a6test/f003-gpu_off_bus | gpu_off_bus | yes | gpu_off_bus | drain_node | yes | - | succeeded | 190 |
| a6test/f016-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 265 |
| a6test/f011-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 316 |
| a6test/f005-thermal_runaway | thermal_runaway | yes | - ✗ | - ✗ | no | - | error | 382 |
