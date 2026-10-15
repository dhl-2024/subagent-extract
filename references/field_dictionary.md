# 字段字典

所有参数叶子为 `{ "value": ..., "unit": "...", "source": "...", "confidence": "..." }`。数值字段使用 JSON number，不把单位拼入字符串；文本值使用 string。confidence 取 `extracted`、`derived`、`assumed`；无单位文本使用空字符串单位。收资表已有的来源和置信度原样保留。

## 组件（module）

| 字段 | 单位 | 规则 |
|---|---|---|
| model | `""` | 以 module_power 精确匹配的唯一型号 |
| pmax | Wp | 命中功率档 |
| vmpp / impp | V / A | 双面组件优先使用目标档 BNPI；无 BNPI 时 Vmpp 保持 STC、Impp × 1.10 |
| voc / isc | V / A | 双面组件优先使用目标档 BNPI；无 BNPI 时 Voc 保持 STC、Isc × 1.10 |
| voc_temp_coeff / isc_temp_coeff | %/℃ | 保留正负号 |
| dimensions | mm | 字符串“长 × 宽 × 厚”；不抽重量 |
| cell_type | `""` | P 型或 N 型；规格书明确使用 BC（背接触）技术时按 Skill 规则归类为 N 型，来源注明“BC 技术归类规则” |
| bifacial | `""` | 是/否 |
| first_year_degradation / annual_degradation | % | 规格书值优先；缺值按 P 型 2%/0.55%、N 型 1%/0.4% 并标记 default/assumed |

不抽 β_Pmax、NOCT、系统电压、双面因子数值。若规格书衰减表描述的是“保留率”（如 99%）而非“衰减率”，先正确换算为 1% 并在来源注明推导；不得将两种口径混淆。

双面组件若规格书列出目标档完整 BNPI 参数，五个电参数均取 BNPI，并标记 `datasheet/extracted`；原始 STC 与 BNPI 值均保留在 `extract_meta`。规格书没有 BNPI 参数时，对目标档 STC 的 pmax、impp、isc 乘以 1.10，vmpp、voc 不变；派生值标记 `derived/derived` 并在元数据中记录规则。BNPI 表存在但必需值不完整时报 E1003。仅对 `bifacial` 为“是”的组件应用。

## 逆变器（inverter）

| 字段 | 单位 | 规则 |
|---|---|---|
| model | `""` | 以 inverter_power 精确匹配唯一型号 |
| rated_power | kW | 命中档 |
| max_input_voltage / start_voltage | V | 最大输入电压按命中型号；规格书未给启动电压时，使用 MPPT 电压范围下限作为启动电压，标记为 `derived/derived` |
| mppt_voltage_range | V | 下限和上限结构化表达 |
| max_input_current / max_short_circuit_current | A | 总值，不逐路拆分 |
| mppt_count | 个 | 区分 MPPT 数量 |
| max_string_inputs | 路 | 最大输入组串路数 |
| china_efficiency | % | 中国效率，不用最大效率 |

字段确实合并标示且语义无法区分时，不要臆造拆分值；列出规格书原文并停止校验。

## 排布

`layout.json` 至少包含 `module_count`（number）、`module_model`（string）、`drawing_annotation`（string|null）、`density`（number）、`confidence`、`source_layer`（string|null）。建议包含 `recognition_path`（`L0_annotation`、`L1_dxf_block`、`L2_pdf_vector`、`L3_visual`）。密度是展示信息，无阈值判定。

## 四要素示例

```json
{"value": 630, "unit": "Wp", "source": "datasheet", "confidence": "extracted"}
```

