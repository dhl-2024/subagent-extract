from __future__ import annotations
import argparse,json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from common import load_json,write_json,ExtractError
from map_collection_form import map_collection_form
from extract_spec import extract_spec
from count_modules import count_modules
from validate_params import validate_params

def run_extract(collection_form,module_spec_pdf=None,inverter_spec_pdf=None,layout_drawing=None,out_dir=None,native_reviews=None):
    if not collection_form:
        return {"status":"failed","params_json_path":None,"layout_json_path":None,"errors":[{"code":"INPUT_ERROR","message":"缺少必需收资表 collection_form"}],"warnings":[],"user_message":"本次无法开始：缺少收资表 JSON 或 HTML。请提供收资表导出的 JSON，或保存有数据的表单。"}
    out=Path(out_dir or (Path(collection_form).resolve().parent/"extract_output")); out.mkdir(parents=True,exist_ok=True)
    errors=[]; warnings=[]; incomplete=[]; params_path=out/"params.json"; layout_path=out/"layout.json"
    try:
        params=map_collection_form(collection_form,params_path)
        reviews=native_reviews or {}; equipment=params.get("equipment",{})
        if not module_spec_pdf: incomplete.append("module")
        if not inverter_spec_pdf: incomplete.append("inverter")
        if not layout_drawing: incomplete.append("layout")
        if module_spec_pdf:
            target=equipment.get("module_power",{}).get("value")
            if target is None: raise ExtractError("INPUT_ERROR","收资表缺少 equipment.module_power，无法匹配组件规格书")
            module_result=extract_spec(module_spec_pdf,target,"module",reviews.get("module"))
            params["module"]=module_result["fields"]
            if module_result.get("extract_meta"): params.setdefault("extract_meta",{}).update(module_result["extract_meta"])
            warnings.extend(module_result.get("warnings",[]))
        if inverter_spec_pdf:
            target=equipment.get("inverter_power",{}).get("value")
            if target is None: raise ExtractError("INPUT_ERROR","收资表缺少 equipment.inverter_power，无法匹配逆变器规格书")
            params["inverter"]=extract_spec(inverter_spec_pdf,target,"inverter",reviews.get("inverter")).get("fields")
        if layout_drawing:
            lr=count_modules(layout_drawing,reviews.get("layout")); params["layout"]=lr["layout"]; warnings.extend(lr["warnings"]); write_json(layout_path,lr["layout"])
        warnings.extend({"code":"W0001","branch":b,"message":f"{b} 分支因缺少输入未执行"} for b in incomplete)
        params["extract_meta"]={**params.get("extract_meta",{}),"incomplete_branches":incomplete,"skill_version":"1.0","extracted_at":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),"recognition_path":params.get("layout",{}).get("recognition_path"),"errors":errors,"warnings":warnings}
        invalid=validate_params(params)
        if invalid: raise ExtractError("SCHEMA_VALIDATION","合并后参数校验失败",validation_errors=invalid)
        write_json(params_path,params)
        return {"status":"ok","params_json_path":str(params_path),"layout_json_path":str(layout_path) if layout_drawing else None,"errors":errors,"warnings":warnings,"user_message":"参数抽取与校验完成。"}
    except ExtractError as e:
        errors.append(e.as_dict())
        for p in (params_path,layout_path):
            if p.exists(): p.unlink()
        return {"status":"failed","params_json_path":None,"layout_json_path":None,"errors":errors,"warnings":warnings,"user_message":f"{e}。请核对输入或补充可读文件后重试。"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--collection-form",required=True); ap.add_argument("--module-spec-pdf"); ap.add_argument("--inverter-spec-pdf"); ap.add_argument("--layout-drawing"); ap.add_argument("--out-dir"); ap.add_argument("--native-reviews"); a=ap.parse_args()
    reviews=load_json(a.native_reviews) if a.native_reviews else {}
    result=run_extract(a.collection_form,a.module_spec_pdf,a.inverter_spec_pdf,a.layout_drawing,a.out_dir,reviews)
    print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(0 if result["status"]=="ok" else 2)
if __name__=="__main__": main()


