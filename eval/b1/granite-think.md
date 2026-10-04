# Eval `test` · granite-think

Commit `a419152` · model `candidate` · prompt `8c3be535ecec` · judge `off` · 2026-10-03T01:06:06+00:00

| Metric | Value |
| --- | --- |
| Runs with a valid diagnosis | 13/20 |
| **Root-cause accuracy** | **13/20 (65%)** |
| Root-cause accuracy, BMC logs missing | 8/11 (73%) |
| Action allowed by the runbook | 13/20 (65%) |
| Unsafe actions (hardware action on a decoy) | - |
| Missed actions (real fault left in service) | 0/20 (0%) |
| Cites the runbook for the true type | 12/20 (60%) |
| Citation support (judge) | - |
| Latency p50 / p95 | 386.1 s / 682.6 s |
| Tokens per case | 25,312 |
| Cost per case | $0.0 |
| Tool errors / tool calls recovered from text | 0 / 0 |

| Type | Cases | Root cause | Action |
| --- | --- | --- | --- |
| ecc_degradation | 4 | 2 | 2 |
| gpu_off_bus | 4 | 3 | 3 |
| nvlink_degradation | 3 | 3 | 3 |
| pcie_degradation | 3 | 2 | 2 |
| power_fault | 3 | 1 | 1 |
| thermal_runaway | 3 | 2 | 2 |

| Case | Truth | BMC missing | Agent | Action | Runbook | Support | Status | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a6test/f001-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 418 |
| a6test/f022-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 434 |
| a6test/f006-ecc_degradation | ecc_degradation | yes | - ✗ | - ✗ | no | - | error | 649 |
| a6test/f014-gpu_off_bus | gpu_off_bus |  | - ✗ | - ✗ | no | - | error | 391 |
| a6test/f008-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 177 |
| a6test/f018-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 218 |
| a6test/f009-nvlink_degradation | nvlink_degradation |  | nvlink_degradation | drain_node | yes | - | succeeded | 346 |
| a6test/f013-power_fault | power_fault |  | - ✗ | - ✗ | no | - | error | 455 |
| a6test/f024-pcie_degradation | pcie_degradation |  | - ✗ | - ✗ | no | - | error | 683 |
| a6test/f000-power_fault | power_fault | yes | - ✗ | - ✗ | no | - | error | 626 |
| a6test/f020-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 366 |
| a6test/f021-power_fault | power_fault |  | power_fault | drain_node | no | - | succeeded | 382 |
| a6test/f012-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 426 |
| a6test/f017-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 335 |
| a6test/f007-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 218 |
| a6test/f015-ecc_degradation | ecc_degradation |  | - ✗ | - ✗ | no | - | error | 646 |
| a6test/f003-gpu_off_bus | gpu_off_bus | yes | gpu_off_bus | drain_node | yes | - | succeeded | 323 |
| a6test/f016-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 300 |
| a6test/f011-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 279 |
| a6test/f005-thermal_runaway | thermal_runaway | yes | - ✗ | - ✗ | no | - | error | 802 |
