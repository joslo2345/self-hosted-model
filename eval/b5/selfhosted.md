# Eval `test` · selfhosted

Commit `a419152` · model `qwen3.5-9b` · prompt `8c3be535ecec` · judge `off` · 2026-10-04T00:52:34+00:00

| Metric | Value |
| --- | --- |
| Runs with a valid diagnosis | 23/25 |
| **Root-cause accuracy** | **23/25 (92%)** |
| Root-cause accuracy, BMC logs missing | 12/14 (86%) |
| Action allowed by the runbook | 20/25 (80%) |
| Unsafe actions (hardware action on a decoy) | 0/3 (0%) |
| Missed actions (real fault left in service) | 1/22 (4%) |
| Cites the runbook for the true type | 20/25 (80%) |
| Citation support (judge) | - |
| Latency p50 / p95 | 157.8 s / 389.5 s |
| Tokens per case | 47,547 |
| Cost per case | $0.0 |
| Tool errors / tool calls recovered from text | 0 / 0 |

| Type | Cases | Root cause | Action |
| --- | --- | --- | --- |
| ecc_degradation | 4 | 4 | 4 |
| gpu_off_bus | 4 | 4 | 2 |
| noisy_neighbor | 3 | 2 | 2 |
| nvlink_degradation | 3 | 3 | 3 |
| pcie_degradation | 3 | 3 | 3 |
| power_fault | 4 | 4 | 3 |
| thermal_runaway | 4 | 3 | 3 |

| Case | Truth | BMC missing | Agent | Action | Runbook | Support | Status | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a6test/f001-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 123 |
| a6test/f022-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 117 |
| a6test/f006-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 150 |
| a6test/f014-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | replace_part ✗ | yes | - | succeeded | 100 |
| a6test/f008-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | drain_node | yes | - | succeeded | 215 |
| a6test/f018-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 223 |
| a6test/f009-nvlink_degradation | nvlink_degradation |  | nvlink_degradation | drain_node | yes | - | succeeded | 185 |
| a6test/f013-power_fault | power_fault |  | power_fault | monitor ✗ | no | - | succeeded | 158 |
| a6test/f024-pcie_degradation | pcie_degradation |  | pcie_degradation | drain_node | yes | - | succeeded | 141 |
| a6test/f000-power_fault | power_fault | yes | power_fault | replace_part | yes | - | succeeded | 148 |
| a6test/f020-ecc_degradation | ecc_degradation | yes | ecc_degradation | drain_node | yes | - | succeeded | 177 |
| a6test/f021-power_fault | power_fault |  | power_fault | replace_part | no | - | succeeded | 82 |
| a6test/f012-pcie_degradation | pcie_degradation | yes | pcie_degradation | drain_node | yes | - | succeeded | 139 |
| a6test/f017-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 162 |
| a6test/f007-gpu_off_bus | gpu_off_bus |  | gpu_off_bus | replace_part ✗ | yes | - | succeeded | 149 |
| a6test/f015-ecc_degradation | ecc_degradation |  | ecc_degradation | drain_node | yes | - | succeeded | 147 |
| a6test/f003-gpu_off_bus | gpu_off_bus | yes | gpu_off_bus | drain_node | yes | - | succeeded | 129 |
| a6test/f016-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 184 |
| a6test/f011-nvlink_degradation | nvlink_degradation | yes | nvlink_degradation | drain_node | yes | - | succeeded | 188 |
| a6test/f005-thermal_runaway | thermal_runaway | yes | thermal_runaway | drain_node | yes | - | succeeded | 328 |
| a6test/f002-power_fault | power_fault | yes | power_fault | replace_part | no | - | succeeded | 117 |
| a6test/f019-thermal_runaway | thermal_runaway | yes | - ✗ | - ✗ | no | - | invalid_output | 526 |
| a6testnn/f007-noisy_neighbor | noisy_neighbor | yes | - ✗ | - ✗ | no | - | error | 389 |
| a6testnn/f004-noisy_neighbor | noisy_neighbor |  | noisy_neighbor | none | yes | - | succeeded | 237 |
| a6testnn/f002-noisy_neighbor | noisy_neighbor |  | noisy_neighbor | none | yes | - | succeeded | 219 |
