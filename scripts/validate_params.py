from __future__ import annotations
import argparse,json
from common import walk_leaves
MODULE_FIELDS=["model","pmax","vmpp","impp","voc","isc","voc_temp_coeff","isc_temp_coeff","dimensions","cell_type","bifacial","first_year_degradation","annual_degradation"]
INVERTER_FIELDS=["model","rated_power","max_input_voltage","start_voltage","mppt_voltage_range","max_input_current","max_short_circuit_current","mppt_count","max_string_inputs","china_efficiency"]
LAYOUT_FIELDS=["module_count","module_model","drawing_annotation","density","confidence","source_layer"]
def validate_params(obj,schema_path=None):
    errors=[]
    if not isinstance(obj,dict): return [{"field":"$","message":"根必须为对象"}]
    for section,fields in (("module",MODULE_FIELDS),("inverter",INVERTER_FIELDS)):
        data=obj.get(section)
        if data is not None:
            if not isinstance(data,dict): errors.append({"field":section,"message":"必须为对象"}); continue
            for f in fields:
                if f not in data: errors.append({"field":f"{section}.{f}","message":"必需字段缺失"})
                elif not isinstance(data[f],dict): errors.append({"field":f"{section}.{f}","message":"必须为四要素叶子对象"})
    layout=obj.get("layout")
    if layout is not None:
        if not isinstance(layout,dict): errors.append({"field":"layout","message":"必须为对象"}); layout={}
        for f in LAYOUT_FIELDS:
            if f not in layout: errors.append({"field":f"layout.{f}","message":"必需字段缺失"})
    if isinstance(layout,dict) and layout:
        if not isinstance(layout.get("module_count"),int) or layout["module_count"]<=0: errors.append({"field":"layout.module_count","message":"必须为正整数"})
        if not isinstance(layout.get("module_model"),str): errors.append({"field":"layout.module_model","message":"必须为字符串"})
        if not isinstance(layout.get("density"),(int,float)): errors.append({"field":"layout.density","message":"必须为数字或 null；不做阈值判定"})
        if layout.get("confidence") not in ("extracted","derived","assumed"): errors.append({"field":"layout.confidence","message":"置信度枚举错误"})
        if layout.get("source_layer") is not None and not isinstance(layout.get("source_layer"),str): errors.append({"field":"layout.source_layer","message":"必须是字符串或 null"})
        if layout.get("drawing_annotation") is not None and not isinstance(layout.get("drawing_annotation"),str): errors.append({"field":"layout.drawing_annotation","message":"必须是字符串或 null"})
    errors.extend(walk_leaves(obj))
    if schema_path:
        try:
            import jsonschema
            schema=json.loads(open(schema_path,encoding="utf-8").read())
            errors.extend({"field":".".join(map(str,e.absolute_path)),"message":e.message} for e in jsonschema.Draft202012Validator(schema).iter_errors(obj))
        except ImportError: pass
    return errors
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input_json"); ap.add_argument("schema_path",nargs="?"); a=ap.parse_args()
    obj=json.load(open(a.input_json,encoding="utf-8")); errors=validate_params(obj,a.schema_path)
    print(json.dumps(errors,ensure_ascii=False,indent=2)); raise SystemExit(1 if errors else 0)
if __name__=="__main__": main()

