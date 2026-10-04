# Eval `test` · qwen4-nothink

Commit `a419152` · model `candidate` · prompt `8c3be535ecec` · judge `off` · 2026-10-03T06:52:46+00:00

| Metric | Value |
| --- | --- |
| Runs with a valid diagnosis | 18/20 |
| **Root-cause accuracy** | **17/20 (85%)** |
| Root-cause accuracy, BMC logs missing | 11/11 (100%) |
| Action allowed by the runbook | 14/20 (70%) |
| Unsafe actions (hardware action on a decoy) | - |
| Missed actions (real fault left in service) | 0/20 (0%) |
| Cites the runbook for the true type | 15/20 (75%) |
| Citation support (judge) | - |
| Latency p50 / p95 | 167.8 s / 277.6 s |
| Tokens per case | 110,566 |
| Cost per case | $0.0 |
| Tool errors / tool calls recovered from text | 2 / 0 |

| Type | Cases | Root cause | Action |
| --- | --- | --- | --- |
| ecc_degradation | 4 | 4 | 4 |
| gpu_off_bus | 4 | 2 | 1 |
| nvlink_degradation | 3 | 3 | 3 |
| pcie_degradation | 3 | 3 | 2 |
| power_fault | 3 | 2 | 1 |
| thermal_runaway | 3 | 3 | 3 |

| Case | Truth | BMC missing | Agent | Action | Runbook | Support | Status | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a6test/f001-pcie_degradation | pcie_degradation | yes | pcie_degradation | escalate ✗ | yes | - | succeeded | 265 |
| a6test/f022-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 188 |
| a6test/f006-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 133 |
| a6test/f014-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | replace_part ✗ | yes | - | succeeded | 233 |
| a6test/f008-gpu_off_bus | gpu_off_bus |  | - ✗ | - ✗ | no | - | error | 134 |
| a6test/f018-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 167 |
| a6test/f009-nvlink_degradation | nvlink_degradation |  | nvlink_degradation | drain_node | yes | - | succeeded | 146 |
| a6test/f013-power_fault | power_fault |  | power_fault | reset_gpu ✗ | no | - | succeeded | 275 |
| a6test/f024-pcie_degradation | pcie_degradation |  | pcie_degradation | replace_part | yes | - | succeeded | 237 |
| a6test/f000-power_fault | power_fault | yes | power_fault | replace_part | no | - | succeeded | 278 |
| a6test/f020-ecc_degradation | ecc_degradation | yes | ecc_degradation | replace_part | yes | - | succeeded | 155 |
| a6test/f021-power_fault | power_fault |  | - ✗ | - ✗ | no | - | error | 151 |
| a6test/f012-pcie_degradation | pcie_degradation | yes | pcie_degradation | replace_part | no | - | succeeded | 169 |
| a6test/f017-ecc_degradation | ecc_degradation |  | ecc_degradation | reset_gpu | yes | - | succeeded | 117 |
| a6test/f007-gpu_off_bus | gpu_off_bus |  | pcie_degradation ✗ | replace_part ✗ | yes | - | succeeded | 204 |
| a6test/f015-ecc_degradation | ecc_degradation |  | ecc_degradation | reset_gpu | yes | - | succeeded | 250 |
| a6test/f003-gpu_off_bus | gpu_off_bus | yes | gpu_off_bus | drain_node | yes | - | succeeded | 166 |
| a6test/f016-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 148 |
| a6test/f011-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 145 |
| a6test/f005-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 294 |
