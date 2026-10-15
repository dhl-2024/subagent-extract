# 验收用例（自动化 tests/test_tools.py）

| ID | 验收点 | 覆盖方式 |
|---|---|---|
| A | 630 W 精确命中及字段值 | `test_A_and_C_exact_module_bins` |
| B | 580 W 不得近似替代，列全档位 | `test_B_no_nearest_power_fallback` |
| C | 600–630 W 七档逐档精确匹配 | `test_A_and_C_exact_module_bins` |
| D | 逆变器目标档位无匹配 E2001 | `test_D_inverter_unmatched` |
| E | L0 “共 128 块”优先 | `test_E_L0_annotation` |
| F | L2 native 识别、source_layer null、密度不拦截 | `test_F_native_L2_density_never_blocks` |
| G | 标注/识别冲突取 L0 并 W3002 | `test_G_annotation_conflict_warning_only` |
| H | 缺 Voc 报 E1003 | `test_H_missing_Voc_fails` |
| I | v0.9 报 E1004 | `test_I_incompatible_schema` |
| J | 同输入映射输出确定 | `test_J_deterministic_mapping` |
| K | 四要素校验 | `test_K_four_elements_and_missing_detection` |

附加用例覆盖重复功率 E1002、不支持格式 E4001、全部计数链路失败 E3001。规格书表格语义/OCR 仍由 native 提供经页面复核的 `review_json`，Tool 不把乱码文本误当可信参数。
