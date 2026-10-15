from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any

class ExtractError(Exception):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message); self.code=code; self.details=details
    def as_dict(self): return {"code":self.code,"message":str(self),**self.details}

def load_json(path: str|Path):
    try: return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception as e: raise ExtractError("INPUT_ERROR", f"无法读取有效 JSON：{e}", file=str(path))

def write_json(path: str|Path, obj: Any):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=False)+"\n",encoding="utf-8")

def read_form(path: str|Path):
    p=Path(path)
    if p.suffix.lower()==".json": return load_json(p)
    if p.suffix.lower() not in (".html",".htm"): raise ExtractError("INPUT_ERROR", "收资表须为 JSON 或 HTML", file=str(p))
    html=p.read_text(encoding="utf-8-sig")
    # Static files cannot expose browser localStorage. Accept an explicit embedded export only.
    patterns=[r'<script[^>]+id=["\']pv_collect_form["\'][^>]*>(.*?)</script>', r'window\.pv_collect_form\s*=\s*(\{.*?\})\s*;']
    for pat in patterns:
        m=re.search(pat,html,re.I|re.S)
        if m:
            try: return json.loads(m.group(1))
            except Exception as e: raise ExtractError("INPUT_ERROR",f"HTML 内嵌 pv_collect_form 无法解析：{e}",file=str(p))
    raise ExtractError("INPUT_ERROR", "静态 HTML 本身不含已保存的浏览器 localStorage。请从表单第二页导出 JSON 后提供；不会读取第一页控件重建汇总数据。",file=str(p),supported="pv-collect-v1.x")

def check_version(obj):
    version=obj.get("schema_version") if isinstance(obj,dict) else None
    if not isinstance(version,str) or not re.fullmatch(r"pv-collect-v1\.\d+",version):
        raise ExtractError("E1004",f"收资表 schema_version 不兼容：{version!r}；支持 pv-collect-v1.x。",actual=version,supported="pv-collect-v1.x")

def leaf(value, unit, source="datasheet", confidence="extracted"):
    return {"value":value,"unit":unit,"source":source,"confidence":confidence}

def require_leaf(value, field, errors):
    if not isinstance(value,dict) or not all(k in value for k in ("value","unit","source","confidence")):
        errors.append({"field":field,"message":"缺少四要素 value/unit/source/confidence"}); return
    if not isinstance(value["unit"],str) or not isinstance(value["source"],str) or not value["source"] or isinstance(value["value"],bool) or not isinstance(value["value"],(int,float,str,type(None))) or value["confidence"] not in ("extracted","derived","assumed"):
        errors.append({"field":field,"message":"四要素类型或 confidence 枚举不合法"})

def walk_leaves(obj,path="$",errors=None):
    errors=[] if errors is None else errors
    if isinstance(obj,dict):
        if any(k in obj for k in ("value","unit","source","confidence")): require_leaf(obj,path,errors)
        else:
            for k,v in obj.items(): walk_leaves(v,f"{path}.{k}",errors)
    elif isinstance(obj,list):
        for i,v in enumerate(obj): walk_leaves(v,f"{path}[{i}]",errors)
    return errors



