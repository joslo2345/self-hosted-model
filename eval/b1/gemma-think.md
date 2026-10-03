# Eval `test` · gemma-think

Commit `a419152` · model `candidate` · prompt `8c3be535ecec` · judge `off` · 2026-10-02T22:04:36+00:00

| Metric | Value |
| --- | --- |
| Runs with a valid diagnosis | 17/20 |
| **Root-cause accuracy** | **17/20 (85%)** |
| Root-cause accuracy, BMC logs missing | 10/11 (91%) |
| Action allowed by the runbook | 15/20 (75%) |
| Unsafe actions (hardware action on a decoy) | - |
| Missed actions (real fault left in service) | 1/20 (5%) |
| Cites the runbook for the true type | 13/20 (65%) |
| Citation support (judge) | - |
| Latency p50 / p95 | 198.1 s / 350.6 s |
| Tokens per case | 30,686 |
| Cost per case | $0.0 |
| Tool errors / tool calls recovered from text | 1 / 0 |

| Type | Cases | Root cause | Action |
| --- | --- | --- | --- |
| ecc_degradation | 4 | 4 | 4 |
| gpu_off_bus | 4 | 3 | 3 |
| nvlink_degradation | 3 | 2 | 2 |
| pcie_degradation | 3 | 3 | 3 |
| power_fault | 3 | 3 | 2 |
| thermal_runaway | 3 | 2 | 1 |

| Case | Truth | BMC missing | Agent | Action | Runbook | Support | Status | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a6test/f001-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | no | - | succeeded | 209 |
| a6test/f022-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 196 |
| a6test/f006-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 240 |
| a6test/f014-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 250 |
| a6test/f008-gpu_off_bus | gpu_off_bus |  | - ✗ | - ✗ | no | - | invalid_output | 112 |
| a6test/f018-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | no | - | succeeded | 373 |
| a6test/f009-nvlink_degradation | nvlink_degradation |  | - ✗ | - ✗ | no | - | invalid_output | 115 |
| a6test/f013-power_fault | power_fault |  | power_fault | none ✗ | yes | - | succeeded | 176 |
| a6test/f024-pcie_degradation | pcie_degradation |  | pcie_degradation | drain_node | yes | - | succeeded | 270 |
| a6test/f000-power_fault | power_fault | yes | power_fault | replace_part | no | - | succeeded | 196 |
| a6test/f020-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 144 |
| a6test/f021-power_fault | power_fault |  | power_fault | escalate | yes | - | succeeded | 351 |
| a6test/f012-pcie_degradation | pcie_degradation | yes | pcie_degradation | replace_part | no | - | succeeded | 188 |
| a6test/f017-ecc_degradation | ecc_degradation |  | ecc_degradation | replace_part | yes | - | succeeded | 176 |
| a6test/f007-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 183 |
| a6test/f015-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 176 |
| a6test/f003-gpu_off_bus | gpu_off_bus | yes | gpu_off_bus | drain_node | yes | - | succeeded | 200 |
| a6test/f016-thermal_runaway | thermal_runaway | yes | - ✗ | - ✗ | no | - | error | 204 |
| a6test/f011-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 332 |
| a6test/f005-thermal_runaway | thermal_runaway | yes | thermal_runaway | escalate ✗ | yes | - | succeeded | 275 |
