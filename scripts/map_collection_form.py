from __future__ import annotations
import argparse
from common import read_form,check_version,write_json,ExtractError
SUMMARY_KEYS=("schema_version","generated_at","project","grid","equipment","tariff","load_monthly","cost","equipment_files")
def map_collection_form(form_path,out_path):
    obj=read_form(form_path); check_version(obj)
    if not isinstance(obj,dict): raise ExtractError("INPUT_ERROR","收资表根必须为 JSON 对象")
    # The exported object is the second-page summary schema. Whitelist its published sections;
    # retain source/confidence verbatim and ignore unrelated first-page/raw controls.
    mapped={key:obj[key] for key in SUMMARY_KEYS if key in obj}
    write_json(out_path,mapped)
    return mapped
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("form_path"); ap.add_argument("out_path"); a=ap.parse_args()
    try:
        obj=map_collection_form(a.form_path,a.out_path); import json; print(json.dumps({"status":"ok","schema_version":obj["schema_version"]},ensure_ascii=False))
    except ExtractError as e: import json; print(json.dumps({"status":"failed","errors":[e.as_dict()]},ensure_ascii=False)); raise SystemExit(2)
if __name__=="__main__": main()
