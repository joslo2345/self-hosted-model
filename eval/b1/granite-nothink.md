# Eval `test` · granite-nothink

Commit `a419152` · model `candidate` · prompt `8c3be535ecec` · judge `off` · 2026-10-02T22:44:24+00:00

| Metric | Value |
| --- | --- |
| Runs with a valid diagnosis | 20/20 |
| **Root-cause accuracy** | **20/20 (100%)** |
| Root-cause accuracy, BMC logs missing | 11/11 (100%) |
| Action allowed by the runbook | 17/20 (85%) |
| Unsafe actions (hardware action on a decoy) | - |
| Missed actions (real fault left in service) | 3/20 (15%) |
| Cites the runbook for the true type | 17/20 (85%) |
| Citation support (judge) | - |
| Latency p50 / p95 | 117.4 s / 151.7 s |
| Tokens per case | 43,804 |
| Cost per case | $0.0 |
| Tool errors / tool calls recovered from text | 0 / 0 |

| Type | Cases | Root cause | Action |
| --- | --- | --- | --- |
| ecc_degradation | 4 | 4 | 4 |
| gpu_off_bus | 4 | 4 | 4 |
| nvlink_degradation | 3 | 3 | 3 |
| pcie_degradation | 3 | 3 | 3 |
| power_fault | 3 | 3 | 0 |
| thermal_runaway | 3 | 3 | 3 |

| Case | Truth | BMC missing | Agent | Action | Runbook | Support | Status | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a6test/f001-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 105 |
| a6test/f022-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 103 |
| a6test/f006-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 98 |
| a6test/f014-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 152 |
| a6test/f008-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 137 |
| a6test/f018-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 82 |
| a6test/f009-nvlink_degradation | nvlink_degradation |  | nvlink_degradation | drain_node | yes | - | succeeded | 87 |
| a6test/f013-power_fault | power_fault |  | power_fault | none ✗ | no | - | succeeded | 103 |
| a6test/f024-pcie_degradation | pcie_degradation |  | pcie_degradation | drain_node | yes | - | succeeded | 138 |
| a6test/f000-power_fault | power_fault | yes | power_fault | monitor ✗ | no | - | succeeded | 118 |
| a6test/f020-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 111 |
| a6test/f021-power_fault | power_fault |  | power_fault | monitor ✗ | no | - | succeeded | 116 |
| a6test/f012-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 138 |
| a6test/f017-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 110 |
| a6test/f007-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 150 |
| a6test/f015-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 155 |
| a6test/f003-gpu_off_bus | gpu_off_bus | yes | gpu_off_bus | drain_node | yes | - | succeeded | 133 |
| a6test/f016-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 120 |
| a6test/f011-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 79 |
| a6test/f005-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 124 |
