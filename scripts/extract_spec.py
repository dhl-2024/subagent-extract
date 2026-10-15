from __future__ import annotations
import argparse,json,re
from pathlib import Path
from common import load_json,leaf,ExtractError
MODULE_REQUIRED={"model":"","pmax":"Wp","vmpp":"V","impp":"A","voc":"V","isc":"A","voc_temp_coeff":"%/℃","isc_temp_coeff":"%/℃","dimensions":"mm","cell_type":"","bifacial":"","first_year_degradation":"%","annual_degradation":"%"}
INVERTER_REQUIRED={"model":"","rated_power":"kW","max_input_voltage":"V","start_voltage":"V","mppt_voltage_range":"V","max_input_current":"A","max_short_circuit_current":"A","mppt_count":"个","max_string_inputs":"路","china_efficiency":"%"}
def pdf_diagnostics(pdf_path):
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages=[]
            for i,p in enumerate(pdf.pages,1):
                txt=p.extract_text() or ""
                suspicious=len(re.findall(r"\(cid:\d+\)|\ufffd",txt)); cjk=len(re.findall(r"[\u3400-\u9fff]",txt))
                pages.append({"page":i,"chars":len(txt),"cjk":cjk,"suspicious":suspicious,"text_preview":txt[:1200]})
        return pages
    except Exception as e: return [{"page":None,"error":str(e)}]
def _mppt_lower_bound(value):
    if isinstance(value,dict):
        if value.get("value") is not None:
            value=value["value"]
        else:
            for key in ("min","lower","minimum","lower_bound"):
                if value.get(key) is not None:
                    value=value[key]; break
    if isinstance(value,(list,tuple)) and value:
        value=value[0]
    match=re.search(r"\d+(?:\.\d+)?",str(value))
    if not match: return None
    number=float(match.group())
    return int(number) if number.is_integer() else number

def extract_spec(pdf_path,target_power,kind,review_json=None):
    if kind not in ("module","inverter"): raise ValueError("kind must be module or inverter")
    if not Path(pdf_path).is_file(): raise ExtractError("E1003","规格书文件不存在或不可读",file=str(pdf_path))
    code="E1001" if kind=="module" else "E2001"; multi="E1002" if kind=="module" else "E2002"
    diag=pdf_diagnostics(pdf_path)
    if not review_json:
        raise ExtractError("E1003","PDF 已执行文本层质量检查，但型号列、功率档及参数表语义须由 native 对照原页确认；未提供复核后的结构化识别结果，不能猜测继续。",file=str(pdf_path),pages=diag,action="渲染相关页并 OCR；native 核对表头、行列、正负号和单位后提供 review_json")
    review=review_json if isinstance(review_json,dict) else load_json(review_json)
    series=review.get("series",[]); power_key="pmax" if kind=="module" else "rated_power"
    hits=[r for r in series if isinstance(r.get(power_key),(int,float)) and float(r[power_key])==float(target_power)]
    available=sorted({r.get(power_key) for r in series if isinstance(r.get(power_key),(int,float))})
    if not hits: raise ExtractError(code,f"目标功率 {target_power} 无精确档位；规格书可用档位：{available}",file=str(pdf_path),target=target_power,available=available)
    if len(hits)>1: raise ExtractError(multi,f"目标功率 {target_power} 对应多个型号：{[r.get('model') for r in hits]}",file=str(pdf_path),target=target_power,matched=[r.get("model") for r in hits])
    row=hits[0]; required=MODULE_REQUIRED if kind=="module" else INVERTER_REQUIRED
    values=dict(row.get("fields",{})); values["model"]=row.get("model"); values["pmax" if kind=="module" else "rated_power"]=row[power_key]
    if kind=="module" and isinstance(values.get("dimensions"),list): values["dimensions"]=" × ".join(str(x) for x in values["dimensions"])
    if kind=="module" and isinstance(values.get("bifacial"),bool): values["bifacial"]="是" if values["bifacial"] else "否"
    if kind=="module" and not values.get("cell_type") and row.get("cell_technology"):
        technology=str(row["cell_technology"]).upper()
        if "BC" in technology:
            values["cell_type"]="N型"
            row.setdefault("derived_sources",{})["cell_type"]="BC 技术归类规则"
    warnings=[]
    if kind=="inverter" and values.get("start_voltage") is None:
        lower_bound=_mppt_lower_bound(values.get("mppt_voltage_range"))
        if lower_bound is not None:
            values["start_voltage"]=leaf(lower_bound,"V","derived","derived")
    if kind=="module":
        cell=str(values.get("cell_type",""))
        if ("first_year_degradation" not in values or values["first_year_degradation"] is None or "annual_degradation" not in values or values["annual_degradation"] is None):
            if "N" in cell.upper(): defaults=(1.0,0.4)
            elif "P" in cell.upper(): defaults=(2.0,0.55)
            else: defaults=None
            if defaults:
                if values.get("first_year_degradation") is None: values["first_year_degradation"]=leaf(defaults[0],"%","default","assumed")
                if values.get("annual_degradation") is None: values["annual_degradation"]=leaf(defaults[1],"%","default","assumed")
                warnings.append({"code":"W1001","message":"规格书未给完整衰减率，已按组件类型采用需求默认值","cell_type":cell})
    missing=[k for k in required if k not in values or values[k] is None]
    if missing: raise ExtractError("E1003",f"参数表缺少/无法确认必需字段：{sorted(set(missing))}",file=str(pdf_path),missing=sorted(set(missing)),pages=diag)
    result={}
    for k,u in required.items():
        v=values[k]
        if isinstance(v,dict) and all(x in v for x in ("value","unit","source","confidence")): result[k]=v
        elif kind=="module" and k=="cell_type" and row.get("derived_sources",{}).get("cell_type")=="BC 技术归类规则": result[k]=leaf(v,u,"derived","derived")
        else: result[k]=leaf(v,u,"datasheet","extracted")
    extract_meta={}
    if kind=="module" and values.get("bifacial")=="是":
        stc={k:result[k]["value"] for k in ("pmax","vmpp","impp","voc","isc")}
        bnpi=row.get("bnpi_fields") or values.get("bnpi_fields")
        bnpi_present=bool(row.get("bnpi_present",bnpi is not None))
        bnpi_target=row.get("bnpi_target_power")
        bnpi_complete=isinstance(bnpi,dict) and all(k in bnpi and bnpi[k] is not None for k in ("pmax","vmpp","impp","voc","isc"))
        if bnpi_present and bnpi_target is None:
            raise ExtractError("E1003","BNPI 复核结果未声明其对应的 STC 功率档，无法排除列错配",file=str(pdf_path),target=target_power,field="bnpi_target_power")
        if bnpi_present and float(bnpi_target)!=float(target_power):
            raise ExtractError("E1003","BNPI 参数对应的 STC 功率档与目标档不一致",file=str(pdf_path),target=target_power,bnpi_target_power=bnpi_target)
        if bnpi_present and not bnpi_complete:
            raise ExtractError("E1003","规格书含 BNPI 参数，但目标档 BNPI 必需字段不完整",file=str(pdf_path),target=target_power,missing=[k for k in ("pmax","vmpp","impp","voc","isc") if not isinstance(bnpi,dict) or bnpi.get(k) is None])
        if bnpi_complete:
            for key,unit in (("pmax","Wp"),("vmpp","V"),("impp","A"),("voc","V"),("isc","A")):
                result[key]=leaf(bnpi[key],unit,"datasheet","extracted")
            extract_meta={"module_parameter_basis":"BNPI","stc_values":stc,"bnpi_values":{k:result[k]["value"] for k in ("pmax","vmpp","impp","voc","isc")}}
        else:
            result["pmax"]=leaf(stc["pmax"]*1.10,"Wp","derived","derived")
            result["impp"]=leaf(stc["impp"]*1.10,"A","derived","derived")
            result["isc"]=leaf(stc["isc"]*1.10,"A","derived","derived")
            extract_meta={"module_parameter_basis":"stc_plus_user_10_percent","stc_values":stc,"bifacial_gain":{"factor":1.10,"rule":"user_defined","affected_fields":["pmax","impp","isc"],"unchanged_fields":["vmpp","voc"]}}
    return {"kind":kind,"fields":result,"extract_meta":extract_meta,"available_powers":available,"source_file":Path(pdf_path).name,"pdf_diagnostics":diag,"warnings":warnings}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("pdf_path"); ap.add_argument("target_power",type=float); ap.add_argument("kind",choices=["module","inverter"]); ap.add_argument("--review-json"); a=ap.parse_args()
    try: print(json.dumps(extract_spec(a.pdf_path,a.target_power,a.kind,a.review_json),ensure_ascii=False,indent=2))
    except ExtractError as e: print(json.dumps({"status":"failed","errors":[e.as_dict()]},ensure_ascii=False)); raise SystemExit(2)
if __name__=="__main__": main()

